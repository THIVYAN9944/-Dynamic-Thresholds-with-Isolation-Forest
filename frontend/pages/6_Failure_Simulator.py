import streamlit as st
import requests
import sys
import os

# Add parent directory to path to import simulation
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from simulation import simulator

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Failure Simulator", page_icon="⚡", layout="wide")
st.title("Network Failure Simulator")

st.markdown("""
Use these controls to inject synthetic degradation into the live network data.
These failures will be detected by the backend and generate incidents automatically.
""")

try:
    locations = requests.get(f"{API_URL}/locations").json()
except:
    st.error("Failed to fetch locations.")
    st.stop()

if not locations:
    st.info("No locations available.")
    st.stop()

loc_options = {loc['name']: loc['id'] for loc in locations}
selected_loc = st.selectbox("Target Location for Failure", list(loc_options.keys()))
loc_id = loc_options[selected_loc]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Case 1: High Latency")
    st.markdown("Simulates a network bottleneck or failing switch.")
    if st.button("Inject High Latency"):
        simulator.inject_high_latency(loc_id)
        st.success(f"High latency injected at {selected_loc}!")
        
    st.subheader("Case 3: Weak Wi-Fi Signal")
    st.markdown("Simulates AP failure or severe interference.")
    if st.button("Inject Weak Wi-Fi"):
        simulator.inject_weak_wifi(loc_id)
        st.success(f"Weak Wi-Fi injected at {selected_loc}!")

with col2:
    st.subheader("Case 2: Packet Loss")
    st.markdown("Simulates faulty cabling or overloaded uplinks.")
    if st.button("Inject Packet Loss"):
        simulator.inject_packet_loss(loc_id)
        st.success(f"Packet loss injected at {selected_loc}!")
        
    st.subheader("Case 4: Application Slowdown")
    st.markdown("Simulates application server issues while the network is healthy.")
    if st.button("Inject Application Slowdown"):
        simulator.inject_app_slowdown(loc_id)
        st.success(f"Application slowdown injected at {selected_loc}!")
