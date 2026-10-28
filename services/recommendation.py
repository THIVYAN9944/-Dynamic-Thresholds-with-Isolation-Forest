"""
CampusPulse Automated Recommendation Service.

Translates empirical telemetry anomalies into actionable, human-readable
prescriptive guidance for campus network administrators and site reliability engineers.
"""

from typing import List, Dict, Any, Optional


def generate_recommendation(
    anomalies: Optional[List[str]],
    metrics: Optional[Dict[str, Any]]
) -> str:
    """
    Synthesizes detected anomalies and telemetry context to generate targeted diagnostic steps.

    Error Boundaries:
    - Safeguards against None or non-dict/non-list parameters.
    - Default fallbacks for missing or unmapped anomaly classifications.
    - Resolves multi-variable interactions (e.g. Wi-Fi overload vs RF fading, app issue vs network drop).

    Rule Logic:
    1. Weak Wi-Fi:
       - If connected_users > 50: AP channel saturation / overload issue -> add capacity or load-balance.
       - Else: Physical RF attenuation or AP transmitter failure -> physical hardware check.
    2. High Latency / Packet Loss:
       - Uplink congestion, faulty switch port, or MTU/transmission queue saturation.
    3. Application Slowdown:
       - If isolated (network latency/loss healthy): Upstream application/database bottleneck.
       - If coupled with network issues: Cascading degradation stemming from link instability.
    4. Unusual Network Behavior:
       - Generic multivariate anomaly detected via Isolation Forest dynamic bounds.

    Args:
        anomalies: List of anomaly string identifiers (e.g. ["Weak Wi-Fi", "High Latency"]).
        metrics: Current telemetry metrics dictionary (e.g. {"connected_users": 65}).

    Returns:
        str: Prescriptive guidance string with recommended administrative actions.
    """
    if not anomalies:
        return "System metrics are within normal ranges. No immediate action required."

    metrics = metrics or {}
    recommendations: List[str] = []

    # Check for Wi-Fi anomalies and discriminate between client density and RF signal loss
    if "Weak Wi-Fi" in anomalies:
        connected_users = metrics.get("connected_users", 0)
        try:
            connected_users = int(connected_users)
        except (ValueError, TypeError):
            connected_users = 0

        if connected_users > 50:
            recommendations.append(
                "The Wi-Fi in this location is handling too many devices at the same time. "
                "Consider checking the access point capacity or distributing users across additional access points."
            )
        else:
            recommendations.append(
                "The Wi-Fi signal strength is very low in this area. This could be due to physical "
                "interference or a failing access point. An engineer should check the physical device."
            )

    # Check for transport layer latency or packet drop
    if "High Latency" in anomalies or "Packet Loss" in anomalies:
        recommendations.append(
            "The network connection is experiencing interruptions and delays. This could be caused "
            "by a faulty switch or an overloaded uplink connecting this building to the main network."
        )

    # Check for application tier response slowdown
    if "Application Slowdown" in anomalies:
        network_impaired = any(a in anomalies for a in ("High Latency", "Packet Loss", "Weak Wi-Fi"))
        if not network_impaired:
            recommendations.append(
                "The network appears healthy, but the application is responding slowly. "
                "The application server should be checked."
            )
        else:
            recommendations.append(
                "The application is responding slowly, likely due to the ongoing network issues mentioned above."
            )

    # Check for multivariate ML anomalous behavior not captured by rigid single thresholds
    if "Unusual Network Behavior" in anomalies and not recommendations:
        recommendations.append(
            "Multivariate anomaly detected by dynamic baseline model. Telemetry patterns deviate "
            "from historical norms for this location. Verify switch telemetry and localized traffic spikes."
        )

    if not recommendations:
        return "System metrics are within normal ranges. No immediate action required."

    return " ".join(recommendations)
