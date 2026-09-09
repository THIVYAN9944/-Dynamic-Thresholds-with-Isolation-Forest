import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Baseline vs Prototype", page_icon="⚖️", layout="wide")
st.title("Baseline vs Prototype Comparison")

st.markdown("""
### Legacy Workflow (Baseline)
- User experiences an issue.
- User eventually submits a complaint manually.
- The complaint is logged.
- An engineer investigates hours or days later.
- Intermittent issues disappear before investigation, leading to "Could not reproduce".

### Prototype Workflow (CampusPulse)
- System continuously monitors probes and telemetry.
- Detects threshold breaches instantly.
- Creates an incident and logs metrics before, during, and after.
- Recommends root cause automatically.
- Engineer has historical evidence of intermittent faults.
""")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Baseline Metrics (Simulated)")
    st.metric("Average Detection Time", "Hours / Days")
    st.metric("Intermittent Fault Capture Rate", "< 10%")
    st.metric("Localisation Accuracy", "Low (User reliant)")

with col2:
    st.subheader("Prototype Metrics (CampusPulse)")
    st.metric("Average Detection Time", "< 5 Seconds")
    st.metric("Intermittent Fault Capture Rate", "> 95%")
    st.metric("Localisation Accuracy", "High (Telemetry based)")
