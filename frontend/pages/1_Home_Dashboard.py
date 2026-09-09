import streamlit as st
import requests
import plotly.graph_objects as go

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Home Dashboard", page_icon="📊", layout="wide")

st.title("Home Dashboard")

try:
    dashboard_data = requests.get(f"{API_URL}/dashboard").json()
except Exception as e:
    st.error(f"Failed to connect to backend: {e}")
    st.stop()

# Metric Cards
col1, col2, col3, col4 = st.columns(4)

col1.metric("Campus Health Score", f"{dashboard_data.get('score', 0)}/100")
col2.metric("Active Incidents", dashboard_data.get('active_incidents', 0))
col3.metric("Avg Latency", f"{dashboard_data.get('avg_latency', 0)} ms")
col4.metric("User Reports", dashboard_data.get('user_reports', 0))

st.markdown("---")

col5, col6, col7 = st.columns(3)
col5.metric("Avg Packet Loss", f"{dashboard_data.get('avg_packet_loss', 0)} %")
col6.metric("Avg Wi-Fi Quality", f"{dashboard_data.get('avg_wifi_quality', 0)} %")
col7.metric("Avg App Response", f"{dashboard_data.get('app_response_time', 0)} ms")

st.markdown("---")
st.subheader("Experience Score Gauge")

score = dashboard_data.get('score', 0)
fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = score,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "Overall Network Experience"},
    gauge = {
        'axis': {'range': [None, 100]},
        'bar': {'color': "darkblue"},
        'steps' : [
            {'range': [0, 50], 'color': "red"},
            {'range': [50, 80], 'color': "yellow"},
            {'range': [80, 100], 'color': "green"}],
        'threshold' : {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': score}
    }
))
st.plotly_chart(fig, use_container_width=True)
