import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Live Monitoring", page_icon="📈", layout="wide")

st.title("Live Experience Monitoring")

try:
    probe_data = requests.get(f"{API_URL}/metrics/probe?limit=200").json()
    wifi_data = requests.get(f"{API_URL}/metrics/wifi?limit=200").json()
    app_data = requests.get(f"{API_URL}/metrics/application?limit=200").json()
except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

if not probe_data:
    st.info("No data available yet. Please start the background simulation.")
    st.stop()

df_probe = pd.DataFrame(probe_data)
df_probe['timestamp'] = pd.to_datetime(df_probe['timestamp'])

df_wifi = pd.DataFrame(wifi_data)
df_wifi['timestamp'] = pd.to_datetime(df_wifi['timestamp'])

df_app = pd.DataFrame(app_data)
df_app['timestamp'] = pd.to_datetime(df_app['timestamp'])

col1, col2 = st.columns(2)

with col1:
    fig_lat = px.line(df_probe, x="timestamp", y="latency_ms", color="location_id", title="Network Latency (ms)")
    fig_lat.add_hline(y=150, line_dash="dash", line_color="red", annotation_text="Threshold")
    st.plotly_chart(fig_lat, use_container_width=True)
    
    fig_rssi = px.line(df_wifi, x="timestamp", y="wifi_rssi", color="location_id", title="Wi-Fi RSSI (dBm)")
    fig_rssi.add_hline(y=-80, line_dash="dash", line_color="red", annotation_text="Threshold")
    st.plotly_chart(fig_rssi, use_container_width=True)

    fig_users = px.line(df_wifi, x="timestamp", y="connected_users", color="location_id", title="Connected Users")
    st.plotly_chart(fig_users, use_container_width=True)

with col2:
    fig_loss = px.line(df_probe, x="timestamp", y="packet_loss_percent", color="location_id", title="Packet Loss (%)")
    fig_loss.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Threshold")
    st.plotly_chart(fig_loss, use_container_width=True)
    
    fig_qual = px.line(df_wifi, x="timestamp", y="wifi_quality", color="location_id", title="Wi-Fi Quality (%)")
    st.plotly_chart(fig_qual, use_container_width=True)
    
    fig_app = px.line(df_app, x="timestamp", y="app_response_time_ms", color="location_id", title="App Response Time (ms)")
    fig_app.add_hline(y=500, line_dash="dash", line_color="red", annotation_text="Threshold")
    st.plotly_chart(fig_app, use_container_width=True)
