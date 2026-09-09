import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import detection, recommendation

def test_anomaly_detection_healthy():
    status, anomalies = detection.detect_anomaly(latency=20, packet_loss=1.0, wifi_rssi=-60, app_response=100)
    assert status == "Healthy"
    assert len(anomalies) == 0

def test_anomaly_detection_high_latency():
    status, anomalies = detection.detect_anomaly(latency=200, packet_loss=1.0, wifi_rssi=-60, app_response=100)
    assert status == "Degraded"
    assert "High Latency" in anomalies

def test_anomaly_detection_packet_loss():
    status, anomalies = detection.detect_anomaly(latency=20, packet_loss=10.0, wifi_rssi=-60, app_response=100)
    assert status == "Degraded"
    assert "Packet Loss" in anomalies

def test_anomaly_detection_weak_wifi():
    status, anomalies = detection.detect_anomaly(latency=20, packet_loss=1.0, wifi_rssi=-90, app_response=100)
    assert status == "Degraded"
    assert "Weak Wi-Fi" in anomalies

def test_anomaly_detection_app_slowdown():
    status, anomalies = detection.detect_anomaly(latency=20, packet_loss=1.0, wifi_rssi=-60, app_response=800)
    assert status == "Degraded"
    assert "Application Slowdown" in anomalies

def test_recommendation_weak_wifi_overload():
    rec = recommendation.generate_recommendation(["Weak Wi-Fi"], {"connected_users": 60})
    assert "handling too many devices" in rec

def test_recommendation_app_slowdown_only():
    rec = recommendation.generate_recommendation(["Application Slowdown"], {})
    assert "network appears healthy, but the application is responding slowly" in rec

def test_experience_score():
    score = detection.calculate_experience_score(latency=50, packet_loss=0, wifi_quality=100, app_response=200)
    assert score == 100
    
    score_degraded = detection.calculate_experience_score(latency=150, packet_loss=5, wifi_quality=80, app_response=500)
    assert score_degraded < 100

def test_anomaly_detection_ml_fallback():
    # Less than 20 points should use fallback (static)
    current = {"latency_ms": 200, "packet_loss_percent": 1.0, "wifi_rssi": -60, "app_response_time_ms": 100}
    status, anomalies = detection.detect_anomaly_ml(current, [])
    assert status == "Degraded"
    assert "High Latency" in anomalies

import random

def test_anomaly_detection_ml_outlier():
    # Generate 50 healthy points with slight variance
    random.seed(42)
    historical = [{"latency_ms": 20 + random.randint(-2, 2), 
                   "packet_loss_percent": 1.0, 
                   "wifi_rssi": -60 + random.randint(-5, 5), 
                   "app_response_time_ms": 100 + random.randint(-10, 10)} for _ in range(50)]
    
    # Inject a couple of anomalies into the historical data so Isolation Forest learns the bounds
    historical.append({"latency_ms": 250, "packet_loss_percent": 1.0, "wifi_rssi": -60, "app_response_time_ms": 100})
    historical.append({"latency_ms": 20, "packet_loss_percent": 15.0, "wifi_rssi": -60, "app_response_time_ms": 100})
    
    # Normal point should be healthy
    current_normal = {"latency_ms": 22, "packet_loss_percent": 1.1, "wifi_rssi": -61, "app_response_time_ms": 105}
    status, anomalies = detection.detect_anomaly_ml(current_normal, historical)
    assert status == "Healthy"
    assert len(anomalies) == 0

    # Anomalous point should be detected
    current_anomaly = {"latency_ms": 300, "packet_loss_percent": 1.0, "wifi_rssi": -60, "app_response_time_ms": 100}
    status, anomalies = detection.detect_anomaly_ml(current_anomaly, historical)
    assert status == "Degraded"
    assert "High Latency" in anomalies
