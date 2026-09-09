import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Incident Timeline", page_icon="🚨", layout="wide")
st.title("Incident Timeline")

try:
    incidents = requests.get(f"{API_URL}/incidents").json()
    locations = requests.get(f"{API_URL}/locations").json()
except:
    st.error("Failed to fetch data")
    st.stop()

loc_map = {loc['id']: loc['name'] for loc in locations}

if not incidents:
    st.success("No incidents recorded yet!")
else:
    for inc in incidents:
        loc_name = loc_map.get(inc['location_id'], "Unknown")
        status_color = "🔴" if inc['status'] == "Active" else "🟢"
        
        with st.expander(f"{status_color} {inc['incident_type']} at {loc_name} ({inc['start_time'][:19]})"):
            st.write(f"**Status:** {inc['status']}")
            st.write(f"**Severity:** {inc['severity']}")
            st.write(f"**Start Time:** {inc['start_time']}")
            if inc['end_time']:
                st.write(f"**End Time:** {inc['end_time']}")
                st.write(f"**Duration:** {inc['duration_seconds']} seconds")
            
            st.write(f"**Cause Explanation:** {inc['cause_explanation']}")
            st.info(f"**Recommendation:** {inc['recommendation']}")
            
            st.json({
                "Metrics During Incident": inc['metrics_during'],
                "Metrics After Recovery": inc.get('metrics_after', 'N/A')
            })
