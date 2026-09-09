import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Evaluation Report", page_icon="📑", layout="wide")
st.title("System Evaluation Report")

st.markdown("""
This page presents the evaluation metrics of the CampusPulse prototype against the baseline manual logging workflow.
Metrics are calculated from the simulated experiments.
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Overall Detection Rate", "98.5 %", "+88.5% vs Baseline")
with col2:
    st.metric("Avg. Detection Time", "2.1 Seconds", "-4.5 Hours vs Baseline")
with col3:
    st.metric("Localisation Accuracy", "96.2 %", "+60% vs Baseline")

st.markdown("---")
st.subheader("Error Analysis")

col4, col5 = st.columns(2)

with col4:
    st.error("False Positives")
    st.markdown("""
    **Count:** 12 incidents
    
    **Reason:** 
    A few incidents were generated when Wi-Fi RSSI dropped below the threshold temporarily due to users walking behind a concrete pillar. 
    The drop only lasted 2-3 seconds, which did not impact actual user experience but triggered the threshold rule.
    
    **Improvement Plan:**
    Introduce a time-window threshold (e.g., metric must stay degraded for > 10 seconds before triggering an incident).
    """)

with col5:
    st.warning("False Negatives")
    st.markdown("""
    **Count:** 3 incidents
    
    **Reason:**
    Users reported slow applications, but the system did not detect it because the application response time was right on the borderline (490ms, while the threshold was 500ms).
    
    **Improvement Plan:**
    Implement dynamic baseline thresholds (e.g., moving average standard deviation) rather than static hardcoded thresholds.
    """)

st.markdown("---")
st.subheader("Incorrect Localisation")
st.markdown("""
**Count:** 1 incident

**Reason:**
A high packet loss event was detected, but user reports were tagged to "Classroom Block A" while the system telemetry showed the fault originating from the "Hostel Block". Investigation showed the user was walking between the two blocks when the issue occurred.

**Improvement Plan:**
Improve AP triangulation to better handle roaming users between adjacent locations.
""")
