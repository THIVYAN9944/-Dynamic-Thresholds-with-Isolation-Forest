"""
CampusPulse Anomaly Detection Service.

Provides two tiers of performance degradation analysis:
1. Static Heuristic Threshold Engine: Rule-based boundary evaluation.
2. Dynamic ML Isolation Forest Engine: Unsupervised multidimensional anomaly detection
   with per-location model persistence, historical median imputation, and periodic retraining.
"""

import os
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

logger = logging.getLogger("campuspulse.detection")

# Static degradation threshold definitions (Baseline)
THRESHOLDS = {
    "latency_ms": 150.0,            # Round-trip latency > 150ms denotes degraded performance
    "packet_loss_percent": 5.0,     # Packet loss > 5% causes perceptible degradation
    "wifi_rssi": -80.0,             # Wi-Fi RSSI < -80 dBm implies weak physical RF coverage
    "app_response_time_ms": 500.0   # HTTP TTFB > 500ms denotes slow server/upstream response
}

# Directory for persisting serialized Isolation Forest models per campus location
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# In-memory LRU-style cache for loaded scikit-learn estimators
MODEL_CACHE: Dict[Any, IsolationForest] = {}
# Request counters for triggering automated model retraining to adapt to concept drift
MODEL_LAST_TRAINED: Dict[Any, int] = {}
RETRAIN_INTERVAL = 100  # Retrain the model every 100 telemetry samples per location


def calculate_experience_score(
    latency: float = 20.0,
    packet_loss: float = 0.0,
    wifi_quality: float = 100.0,
    app_response: float = 100.0
) -> float:
    """
    Computes an empirical Composite Experience Score (0 to 100).

    Formula Details:
    - Base score: 100
    - Latency penalty: -1 point per 10ms above baseline (50ms)
    - Packet loss penalty: -5 points per 1% packet loss
    - Wi-Fi quality penalty: -0.5 points per 1% below optimal (100)
    - App response penalty: -1 point per 100ms above baseline (200ms)

    Args:
        latency (float): ICMP RTT in milliseconds.
        packet_loss (float): Packet drop percentage (0-100).
        wifi_quality (float): Wi-Fi link score (0-100).
        app_response (float): HTTP response time in milliseconds.

    Returns:
        float: Bounded experience score between 0.0 (unusable) and 100.0 (optimal).
    """
    # Safe fallback for None or non-numeric inputs
    latency = float(latency) if latency is not None else 20.0
    packet_loss = float(packet_loss) if packet_loss is not None else 0.0
    wifi_quality = float(wifi_quality) if wifi_quality is not None else 100.0
    app_response = float(app_response) if app_response is not None else 100.0

    score = 100.0

    # 1. Latency penalty: -1 point for every 10ms above 50ms
    if latency > 50.0:
        score -= (latency - 50.0) / 10.0

    # 2. Packet loss penalty: -5 points per 1% lost
    score -= packet_loss * 5.0

    # 3. Wi-Fi Quality penalty: -0.5 points per unit below 100%
    if wifi_quality < 100.0:
        score -= (100.0 - wifi_quality) * 0.5

    # 4. Application response penalty: -1 point per 100ms above 200ms
    if app_response > 200.0:
        score -= (app_response - 200.0) / 100.0

    # Enforce strict boundary: [0.0, 100.0]
    return float(max(0.0, min(100.0, round(score, 2))))


def detect_anomaly(
    latency: Optional[float] = None,
    packet_loss: Optional[float] = None,
    wifi_rssi: Optional[float] = None,
    app_response: Optional[float] = None
) -> Tuple[str, List[str]]:
    """
    Evaluates telemetry against static heuristic thresholds.
    
    Acts as the baseline detection engine and Tier-2 fallback when historical
    data is insufficient or ML inference experiences a failure.

    Args:
        latency: Round-trip time in milliseconds.
        packet_loss: Packet drop percentage (0-100).
        wifi_rssi: Received signal strength in dBm.
        app_response: HTTP response time in milliseconds.

    Returns:
        Tuple[str, List[str]]: Tuple containing:
            - status: "Healthy" or "Degraded"
            - anomalies: List of identified failure labels.
    """
    anomalies: List[str] = []

    if latency is not None and latency > THRESHOLDS["latency_ms"]:
        anomalies.append("High Latency")
    if packet_loss is not None and packet_loss > THRESHOLDS["packet_loss_percent"]:
        anomalies.append("Packet Loss")
    if wifi_rssi is not None and wifi_rssi < THRESHOLDS["wifi_rssi"]:
        anomalies.append("Weak Wi-Fi")
    if app_response is not None and app_response > THRESHOLDS["app_response_time_ms"]:
        anomalies.append("Application Slowdown")

    if anomalies:
        return "Degraded", anomalies
    return "Healthy", []


def detect_anomaly_ml(
    current_metrics: Dict[str, Any],
    historical_data: List[Dict[str, Any]],
    location_id: Any = "default",
    contamination: float = 0.05
) -> Tuple[str, List[str]]:
    """
    Evaluates current telemetry using an Isolation Forest dynamic threshold model.

    Error Boundaries & Resiliency Architecture:
    1. Sample Size Boundary: If historical observations are fewer than 20 points,
       the function seamlessly falls back to the static heuristic detection engine.
    2. Missing Data Boundary: Historical medians are computed across sparse streams.
       Any missing features (NaN/None) are imputed with historical medians to prevent
       matrix degradation. If all historical values are missing, sensible defaults are used.
    3. Model Persistence & Corruption Boundary: Serialized models on disk are verified.
       If joblib deserialization throws an exception (e.g. file truncated/corrupted),
       the corrupt file is discarded and a new model is freshly trained.
    4. Runtime Inference Exception Boundary: If any unexpected numerical or matrix exception
       occurs during feature extraction or fitting, it catches the exception and falls back
       to static heuristic detection.

    Args:
        current_metrics: Dictionary containing latency_ms, packet_loss_percent,
                         wifi_rssi, and app_response_time_ms.
        historical_data: List of telemetry dictionaries from recent historical window.
        location_id: Identifier to persist/load endpoint-specific models.
        contamination: Expected proportion of outliers in the dataset (default: 0.05).

    Returns:
        Tuple[str, List[str]]: Status ("Healthy" or "Degraded") and list of anomaly labels.
    """
    features = ["latency_ms", "packet_loss_percent", "wifi_rssi", "app_response_time_ms"]

    # Tier-1 Error Boundary: Insufficient sample count fallback
    if not historical_data or len(historical_data) < 20:
        return detect_anomaly(
            latency=current_metrics.get("latency_ms"),
            packet_loss=current_metrics.get("packet_loss_percent"),
            wifi_rssi=current_metrics.get("wifi_rssi"),
            app_response=current_metrics.get("app_response_time_ms")
        )

    try:
        # Construct and clean historical DataFrame
        df = pd.DataFrame(historical_data)
        for f in features:
            if f not in df.columns:
                df[f] = np.nan

        df = df[features].copy()

        # Sensible defaults in the event an entire historical feature is null
        defaults = pd.Series({
            "latency_ms": 20.0,
            "packet_loss_percent": 0.0,
            "wifi_rssi": -60.0,
            "app_response_time_ms": 100.0
        })
        medians = df.median().fillna(defaults)
        df = df.fillna(medians)

        model_path = os.path.join(MODEL_DIR, f"iforest_{location_id}.pkl")

        # Tier-2 Error Boundary: Safe model deserialization
        if location_id not in MODEL_CACHE or MODEL_CACHE[location_id] is None:
            if os.path.exists(model_path):
                try:
                    MODEL_CACHE[location_id] = joblib.load(model_path)
                    MODEL_LAST_TRAINED[location_id] = 0
                except Exception as exc:
                    logger.warning("Corrupted model file detected for location %s: %s. Re-training model.", location_id, exc)
                    MODEL_CACHE[location_id] = None
                    MODEL_LAST_TRAINED[location_id] = 0
                    try:
                        os.remove(model_path)
                    except OSError:
                        pass
            else:
                MODEL_CACHE[location_id] = None
                MODEL_LAST_TRAINED[location_id] = 0

        # Retraining cycle: Periodic adaptation to dynamic campus baselines
        MODEL_LAST_TRAINED[location_id] = MODEL_LAST_TRAINED.get(location_id, 0) + 1
        if MODEL_CACHE[location_id] is None or MODEL_LAST_TRAINED[location_id] > RETRAIN_INTERVAL:
            model = IsolationForest(contamination=contamination, random_state=42)
            model.fit(df)
            MODEL_CACHE[location_id] = model
            MODEL_LAST_TRAINED[location_id] = 0
            try:
                joblib.dump(model, model_path)
            except Exception as dump_err:
                logger.warning("Failed to persist model to %s: %s", model_path, dump_err)

        model = MODEL_CACHE[location_id]

        # Prepare current evaluation record with median imputation for missing values
        current_series = pd.Series(current_metrics)
        current_df = pd.DataFrame([current_series], columns=features)
        current_df = current_df.fillna(medians)

        # Execute Isolation Forest prediction (-1 = anomaly, 1 = normal)
        prediction = model.predict(current_df)[0]

        if prediction == -1:
            anomalies: List[str] = []
            # Granular attribution based on distribution quantiles
            if current_df.iloc[0]["latency_ms"] > df["latency_ms"].quantile(0.90):
                anomalies.append("High Latency")
            if current_df.iloc[0]["packet_loss_percent"] > df["packet_loss_percent"].quantile(0.90):
                anomalies.append("Packet Loss")
            if current_df.iloc[0]["wifi_rssi"] < df["wifi_rssi"].quantile(0.10):
                anomalies.append("Weak Wi-Fi")
            if current_df.iloc[0]["app_response_time_ms"] > df["app_response_time_ms"].quantile(0.90):
                anomalies.append("Application Slowdown")

            if not anomalies:
                anomalies.append("Unusual Network Behavior")

            return "Degraded", anomalies

        return "Healthy", []

    except Exception as runtime_err:
        # Tier-3 Error Boundary: Fall back to static rules upon unexpected exception
        logger.error("Exception during ML anomaly evaluation: %s. Reverting to static rules.", runtime_err)
        return detect_anomaly(
            latency=current_metrics.get("latency_ms"),
            packet_loss=current_metrics.get("packet_loss_percent"),
            wifi_rssi=current_metrics.get("wifi_rssi"),
            app_response=current_metrics.get("app_response_time_ms")
        )
