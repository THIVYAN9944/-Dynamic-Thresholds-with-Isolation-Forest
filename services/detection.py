import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

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

def detect_anomaly_ml(current_metrics, historical_data):
    """
    Detect anomalies using Isolation Forest.
    current_metrics: dict containing latency_ms, packet_loss_percent, wifi_rssi, app_response_time_ms
    historical_data: list of dicts with the same keys
    """
    # If we don't have enough data (e.g. less than 20 points), fallback to static thresholds
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
            df[f] = 0.0
            
    df = df[features].fillna(0)
    
    # Train Isolation Forest
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(df)
    
    # Prepare current point
    current_df = pd.DataFrame([current_metrics], columns=features).fillna(0)
    
    prediction = model.predict(current_df)[0]
    
    if prediction == -1:
        # It's an anomaly, figure out why by comparing to 90th/10th percentile
        anomalies = []
        
        if current_metrics.get("latency_ms", 0) > df["latency_ms"].quantile(0.90):
            anomalies.append("High Latency")
            
        if current_metrics.get("packet_loss_percent", 0) > df["packet_loss_percent"].quantile(0.90):
            anomalies.append("Packet Loss")
            
        if current_metrics.get("wifi_rssi", 0) < df["wifi_rssi"].quantile(0.10):
            anomalies.append("Weak Wi-Fi")
            
        if current_metrics.get("app_response_time_ms", 0) > df["app_response_time_ms"].quantile(0.90):
            anomalies.append("Application Slowdown")
            
        if not anomalies:
            anomalies.append("Unusual Network Behavior")
            
        return "Degraded", anomalies

    return "Healthy", []
