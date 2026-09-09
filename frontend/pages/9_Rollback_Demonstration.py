import streamlit as st
import time

st.set_page_config(page_title="Rollback Demonstration", page_icon="🔙", layout="wide")
st.title("System Rollback Demonstration")

st.markdown("""
Use this page to toggle the system mode between **Prototype** (automated) and **Legacy** (manual).
This demonstrates the ability to safely rollback to the baseline system if needed, while preserving collected data.
""")

if 'mode' not in st.session_state:
    st.session_state.mode = 'prototype'

current_mode = st.session_state.mode

st.write(f"### Current System Mode: **{current_mode.upper()}**")

if current_mode == 'prototype':
    st.success("The system is currently running in Automated Prototype mode. Telemetry is being collected and analyzed.")
    if st.button("Trigger Rollback to Legacy Mode"):
        with st.spinner("Initiating rollback... pausing automated telemetry..."):
            time.sleep(2)
            st.session_state.mode = 'legacy'
            st.rerun()
else:
    st.warning("The system is currently running in Legacy mode. Automated telemetry and anomaly detection are PAUSED. Only manual user reports are accepted.")
    if st.button("Restore Prototype Mode"):
        with st.spinner("Restoring prototype... resuming automated telemetry..."):
            time.sleep(2)
            st.session_state.mode = 'prototype'
            st.rerun()

st.markdown("---")
st.subheader("System Logs")
if current_mode == 'prototype':
    st.code("[SYSTEM] Mode set to PROTOTYPE.\n[SYSTEM] Automated probes activated.\n[SYSTEM] Anomaly detection engine running.")
else:
    st.code("[SYSTEM] Mode set to LEGACY.\n[SYSTEM] Automated probes suspended.\n[SYSTEM] Anomaly detection engine paused.\n[SYSTEM] Awaiting manual user reports.")
