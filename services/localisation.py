from collections import defaultdict

def locate_affected_area(metrics_data, user_reports):
    """
    metrics_data: list of dictionaries containing location_id and metrics.
    user_reports: list of dictionaries with location_id and severity.
    """
    location_scores = defaultdict(float)
    
    # Weight metrics severity
    for data in metrics_data:
        loc_id = data.get("location_id")
        if data.get("latency_ms", 0) > 150:
            location_scores[loc_id] += 2.0
        if data.get("packet_loss_percent", 0) > 5.0:
            location_scores[loc_id] += 3.0
        if data.get("wifi_rssi", 0) < -80:
            location_scores[loc_id] += 2.0
        if data.get("app_response_time_ms", 0) > 500:
            location_scores[loc_id] += 1.0
            
    # Weight user reports
    for report in user_reports:
        loc_id = report.get("location_id")
        if report.get("severity") == "High":
            location_scores[loc_id] += 5.0
        elif report.get("severity") == "Medium":
            location_scores[loc_id] += 3.0
        else:
            location_scores[loc_id] += 1.0
            
    if not location_scores:
        return None
        
    most_affected = max(location_scores, key=location_scores.get)
    return most_affected
