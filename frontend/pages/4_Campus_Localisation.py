import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Campus Localisation", page_icon="🗺️", layout="wide")
st.title("Campus Localisation Map")

try:
    locations = requests.get(f"{API_URL}/locations").json()
    incidents = requests.get(f"{API_URL}/incidents").json()
except:
    st.error("Failed to fetch data")
    st.stop()

if not locations:
    st.info("No locations defined.")
    st.stop()

df_locs = pd.DataFrame(locations)
df_incs = pd.DataFrame(incidents)

# Count active incidents per location
active_counts = {}
for loc in locations:
    active_counts[loc['id']] = 0

if not df_incs.empty:
    active_incs = df_incs[df_incs['status'] == 'Active']
    for _, row in active_incs.iterrows():
        active_counts[row['location_id']] += 1

df_locs['active_incidents'] = df_locs['id'].map(active_counts)

# Create a map
fig = px.scatter_mapbox(
    df_locs, 
    lat="latitude", 
    lon="longitude", 
    hover_name="name", 
    hover_data=["active_incidents"],
    color="active_incidents",
    color_continuous_scale=px.colors.sequential.Reds,
    size="active_incidents",
    size_max=20,
    zoom=16,
    height=600
)

fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

st.plotly_chart(fig, use_container_width=True)

# Highlight most affected
if df_locs['active_incidents'].sum() > 0:
    most_affected = df_locs.loc[df_locs['active_incidents'].idxmax()]
    st.error(f"🚨 **Most Affected Location:** {most_affected['name']} with {most_affected['active_incidents']} active incidents.")
else:
    st.success("✅ All locations are currently healthy.")
