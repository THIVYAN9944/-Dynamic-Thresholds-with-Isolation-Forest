import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import os
import joblib
import time
THRESHOLDS = {
    "latency_ms": 150,
    "packet_loss_percent": 5.0,
    "wifi_rssi": -80,
    "app_response_time_ms": 500
}

def calculate_experience_score(latency, packet_loss, wifi_quality, app_response):
    score = 100
    
    # Latency penalty: -1 point per 10ms over 50ms
    if latency > 50:
        score -= (latency - 50) / 10
        
    # Packet loss penalty: -5 points per 1%
    score -= packet_loss * 5
    
    # Wi-Fi Quality penalty: -0.5 points per 1% below 100
    if wifi_quality < 100:
        score -= (100 - wifi_quality) * 0.5
        
    # App response penalty: -1 point per 100ms over 200ms
    if app_response > 200:
        score -= (app_response - 200) / 100
        
    return max(0, min(100, score))

def detect_anomaly(latency=None, packet_loss=None, wifi_rssi=None, app_response=None):
    anomalies = []
    
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

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_CACHE = {}
MODEL_LAST_TRAINED = {}
RETRAIN_INTERVAL = 100 # Retrain every 100 requests (or we could use time)

def detect_anomaly_ml(current_metrics, historical_data, location_id="default", contamination=0.05):
    """
    Detect anomalies using Isolation Forest.
    current_metrics: dict containing latency_ms, packet_loss_percent, wifi_rssi, app_response_time_ms
    historical_data: list of dicts with the same keys
    location_id: Identifier for the location to persist/load specific model
    contamination: Tunable contamination parameter for Isolation Forest
    """
    if not historical_data or len(historical_data) < 20:
        return detect_anomaly(
            latency=current_metrics.get("latency_ms"),
            packet_loss=current_metrics.get("packet_loss_percent"),
            wifi_rssi=current_metrics.get("wifi_rssi"),
            app_response=current_metrics.get("app_response_time_ms")
        )

    # Prepare data for ML
    df = pd.DataFrame(historical_data)
    features = ["latency_ms", "packet_loss_percent", "wifi_rssi", "app_response_time_ms"]
    
    # Ensure all features exist in dataframe
    for f in features:
        if f not in df.columns:
            df[f] = np.nan
            
    # Handle sparse/missing telemetry streams using median imputation instead of 0
    # 0 can be a valid value (e.g., latency, packet loss) but very skewed for wifi_rssi
    df = df[features]
    medians = df.median()
    # If all values are NaN, provide sensible defaults
    defaults = pd.Series({
        "latency_ms": 20.0,
        "packet_loss_percent": 0.0,
        "wifi_rssi": -60.0,
        "app_response_time_ms": 100.0
    })
    medians = medians.fillna(defaults)
    df = df.fillna(medians)
    
    model_path = os.path.join(MODEL_DIR, f"iforest_{location_id}.pkl")
    
    # Load model if exists in cache or disk
    if location_id not in MODEL_CACHE:
        if os.path.exists(model_path):
            MODEL_CACHE[location_id] = joblib.load(model_path)
            MODEL_LAST_TRAINED[location_id] = 0 # force tracking
        else:
            MODEL_CACHE[location_id] = None
            MODEL_LAST_TRAINED[location_id] = 0

    # Retrain if no model or periodic retraining needed
    MODEL_LAST_TRAINED[location_id] = MODEL_LAST_TRAINED.get(location_id, 0) + 1
    if MODEL_CACHE[location_id] is None or MODEL_LAST_TRAINED[location_id] > RETRAIN_INTERVAL:
        model = IsolationForest(contamination=contamination, random_state=42)
        model.fit(df)
        MODEL_CACHE[location_id] = model
        MODEL_LAST_TRAINED[location_id] = 0
        joblib.dump(model, model_path)
    
    model = MODEL_CACHE[location_id]
    
    # Prepare current point, handling missing data with the historical medians
    current_series = pd.Series(current_metrics)
    current_df = pd.DataFrame([current_series], columns=features)
    current_df = current_df.fillna(medians)
    
    prediction = model.predict(current_df)[0]
    
    if prediction == -1:
        anomalies = []
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
