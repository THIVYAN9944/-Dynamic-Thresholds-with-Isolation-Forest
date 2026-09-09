import streamlit as st

st.set_page_config(
    page_title="CampusPulse",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("CampusPulse")
st.subheader("End-to-End Network Experience Recorder and Intermittent Degradation Localisation System")

st.markdown("""
Welcome to CampusPulse! 

Use the sidebar to navigate through the different modules of the prototype:
- **Home Dashboard:** High-level overview of campus network health.
- **Live Experience Monitoring:** Real-time metrics streaming.
- **Incident Timeline:** History of network degradations.
- **Campus Localisation:** Identify the most affected locations.
- **User Reports:** Submit and view manual problem reports.
- **Failure Simulator:** Inject synthetic failures to test the system.
- **Baseline vs Prototype:** Compare the automated system with manual logging.
- **Migration & Legacy:** Import historical CSV logs.
- **Rollback Demonstration:** Toggle between legacy and prototype modes.
- **Evaluation Report:** System performance metrics and error analysis.
""")

# Initialize session state for rollback feature
if 'mode' not in st.session_state:
    st.session_state.mode = 'prototype'
