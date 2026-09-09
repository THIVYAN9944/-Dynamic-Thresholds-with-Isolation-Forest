def generate_recommendation(anomalies: list, metrics: dict) -> str:
    """
    anomalies: List of strings (e.g., ["Weak Wi-Fi", "Application Slowdown"])
    metrics: dictionary of the specific degraded metrics.
    """
    recommendations = []
    
    if "Weak Wi-Fi" in anomalies:
        if metrics.get("connected_users", 0) > 50:
            recommendations.append("The Wi-Fi in this location is handling too many devices at the same time. Consider checking the access point capacity or distributing users across additional access points.")
        else:
            recommendations.append("The Wi-Fi signal strength is very low in this area. This could be due to physical interference or a failing access point. An engineer should check the physical device.")
            
    if "High Latency" in anomalies or "Packet Loss" in anomalies:
        recommendations.append("The network connection is experiencing interruptions and delays. This could be caused by a faulty switch or an overloaded uplink connecting this building to the main network.")
        
    if "Application Slowdown" in anomalies:
        if "High Latency" not in anomalies and "Packet Loss" not in anomalies and "Weak Wi-Fi" not in anomalies:
            recommendations.append("The network appears healthy, but the application is responding slowly. The application server should be checked.")
        else:
            recommendations.append("The application is responding slowly, likely due to the ongoing network issues mentioned above.")
            
    if not recommendations:
        return "System metrics are within normal ranges. No immediate action required."
        
    return " ".join(recommendations)
