import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, roc_curve, auc
from services.detection import detect_anomaly, detect_anomaly_ml
import random

def generate_dataset(num_normal=1000, num_anomalous=100):
    data = []
    labels = []
    
    # Generate normal data
    for _ in range(num_normal):
        # Using distributions from data_generator.py
        metrics = {
            "latency_ms": random.uniform(10, 45),
            "packet_loss_percent": random.uniform(0, 1.5),
            "wifi_rssi": random.uniform(-75, -50),
            "app_response_time_ms": random.uniform(50, 150)
        }
        data.append(metrics)
        labels.append(0)
        
    # Generate anomalous data
    for _ in range(num_anomalous):
        anomaly_type = random.choice(["latency", "packet_loss", "wifi", "app"])
        
        metrics = {
            "latency_ms": random.uniform(10, 45),
            "packet_loss_percent": random.uniform(0, 1.5),
            "wifi_rssi": random.uniform(-75, -50),
            "app_response_time_ms": random.uniform(50, 150)
        }
        
        if anomaly_type == "latency":
            metrics["latency_ms"] = random.uniform(200, 500)
        elif anomaly_type == "packet_loss":
            metrics["packet_loss_percent"] = random.uniform(10, 25)
        elif anomaly_type == "wifi":
            metrics["wifi_rssi"] = random.uniform(-95, -85)
        elif anomaly_type == "app":
            metrics["app_response_time_ms"] = random.uniform(800, 2000)
            
        data.append(metrics)
        labels.append(1)
        
    # Shuffle
    combined = list(zip(data, labels))
    random.shuffle(combined)
    data, labels = zip(*combined)
    
    return list(data), list(labels)

def run_benchmark():
    print("Generating synthetic dataset for benchmarking...")
    data, labels = generate_dataset(num_normal=2000, num_anomalous=200)
    print(f"Dataset generated: {len(data)} total samples ({sum(labels)} anomalies)")
    
    # Static Threshold Evaluation
    print("\n--- Evaluating Static Thresholds ---")
    static_preds = []
    for d in data:
        status, _ = detect_anomaly(
            latency=d["latency_ms"],
            packet_loss=d["packet_loss_percent"],
            wifi_rssi=d["wifi_rssi"],
            app_response=d["app_response_time_ms"]
        )
        static_preds.append(1 if status == "Degraded" else 0)
        
    s_precision = precision_score(labels, static_preds)
    s_recall = recall_score(labels, static_preds)
    s_f1 = f1_score(labels, static_preds)
    s_roc = roc_auc_score(labels, static_preds)
    
    print(f"Precision: {s_precision:.4f}")
    print(f"Recall:    {s_recall:.4f}")
    print(f"F1 Score:  {s_f1:.4f}")
    print(f"ROC AUC:   {s_roc:.4f}")
    
    # ML Dynamic Threshold Evaluation
    print("\n--- Evaluating Dynamic Thresholds (Isolation Forest) ---")
    ml_preds = []
    historical_data = []
    
    # We simulate a streaming environment
    for i, d in enumerate(data):
        # We pass historical_data up to this point, or last N points
        hist = historical_data[-500:] if len(historical_data) > 0 else []
        status, _ = detect_anomaly_ml(d, hist, location_id="bench_loc", contamination=0.1)
        ml_preds.append(1 if status == "Degraded" else 0)
        historical_data.append(d)
        
    m_precision = precision_score(labels, ml_preds)
    m_recall = recall_score(labels, ml_preds)
    m_f1 = f1_score(labels, ml_preds)
    m_roc = roc_auc_score(labels, ml_preds)
    
    print(f"Precision: {m_precision:.4f}")
    print(f"Recall:    {m_recall:.4f}")
    print(f"F1 Score:  {m_f1:.4f}")
    print(f"ROC AUC:   {m_roc:.4f}")
    
    # False positive reduction
    s_fp = sum(1 for p, l in zip(static_preds, labels) if p == 1 and l == 0)
    m_fp = sum(1 for p, l in zip(ml_preds, labels) if p == 1 and l == 0)
    
    print("\n--- Alert Fatigue Metrics ---")
    print(f"Static False Positives: {s_fp}")
    print(f"Dynamic False Positives: {m_fp}")
    if s_fp > 0:
        reduction = (s_fp - m_fp) / s_fp * 100
        print(f"False Positive Reduction: {reduction:.2f}%")
        
if __name__ == "__main__":
    run_benchmark()
