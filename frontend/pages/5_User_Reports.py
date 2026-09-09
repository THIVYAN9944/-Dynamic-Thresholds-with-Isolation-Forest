import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="User Reports", page_icon="📝", layout="wide")
st.title("Submit a User Report")

try:
    locations = requests.get(f"{API_URL}/locations").json()
except:
    st.error("Failed to fetch locations.")
    st.stop()

if not locations:
    st.info("No locations available.")
    st.stop()

loc_options = {loc['name']: loc['id'] for loc in locations}

with st.form("user_report_form"):
    location_name = st.selectbox("Location", list(loc_options.keys()))
    issue_type = st.selectbox("Issue Type", ["Internet Slow", "No Wi-Fi", "Application Timeout", "Connection Dropping", "Other"])
    severity = st.select_slider("Severity", options=["Low", "Medium", "High"])
    description = st.text_area("Description")
    
    submitted = st.form_submit_button("Submit Report")
    
    if submitted:
        report_data = {
            "location_id": loc_options[location_name],
            "issue_type": issue_type,
            "severity": severity,
            "description": description
        }
        res = requests.post(f"{API_URL}/report", json=report_data)
        if res.status_code == 200:
            st.success("Report submitted successfully!")
        else:
            st.error("Failed to submit report.")
