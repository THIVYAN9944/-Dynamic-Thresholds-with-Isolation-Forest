import streamlit as st
import pandas as pd
import requests

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Migration Workflow", page_icon="🔄", layout="wide")
st.title("Migration and Legacy Workflow")

st.markdown("""
This module allows you to import legacy manual engineer logs (CSV format) into the new CampusPulse system.
""")

uploaded_file = st.file_uploader("Upload Legacy CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("Preview of Legacy Data:")
    st.dataframe(df.head())
    
    expected_columns = ["timestamp", "location_name", "reported_issue", "severity", "engineer_notes", "status", "resolution_time_hrs"]
    if all(col in df.columns for col in expected_columns):
        st.success("Column validation passed!")
        
        if st.button("Migrate to Database"):
            # Fetch locations to map
            try:
                locations = requests.get(f"{API_URL}/locations").json()
                loc_map = {loc['name']: loc['id'] for loc in locations}
            except:
                st.error("Failed to fetch locations from backend.")
                st.stop()
                
            success_count = 0
            for _, row in df.iterrows():
                loc_id = loc_map.get(row['location_name'])
                if loc_id:
                    report_data = {
                        "location_id": loc_id,
                        "issue_type": row['reported_issue'],
                        "severity": row['severity'],
                        "description": str(row['engineer_notes'])
                    }
                    res = requests.post(f"{API_URL}/report", json=report_data)
                    if res.status_code == 200:
                        success_count += 1
            
            st.success(f"Migration completed! Successfully imported {success_count} legacy records into User Reports.")
    else:
        st.error(f"Invalid CSV format. Expected columns: {', '.join(expected_columns)}")
