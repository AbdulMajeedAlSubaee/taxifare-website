import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

import openrouteservice
from openrouteservice import convert

st.set_page_config(page_title="NYC Taxi Fare Predictor", page_icon="🚖", layout="wide")

'''
# 🚖 TaxiFareModel - Interactive Predictor
'''

st.markdown('''
Welcome! This app predicts NYC taxi fares based on your trip details.
Simply click on the map to select your **pickup** and **dropoff** locations!
''')

# Initialize session state for locations
if 'pickup_coords' not in st.session_state:
    st.session_state.pickup_coords = None
if 'dropoff_coords' not in st.session_state:
    st.session_state.dropoff_coords = None
if 'selection_mode' not in st.session_state:
    st.session_state.selection_mode = 'pickup'
if 'last_click' not in st.session_state:
    st.session_state.last_click = None

'''
## 📍 Step 1: Select Pickup and Dropoff Locations on the Map
'''

# Instructions
col1, col2 = st.columns(2)
with col1:
    st.info("🟢 **Green marker** = Pickup location")
with col2:
    st.info("🔴 **Red marker** = Dropoff location")

# Selection mode toggle
mode = st.radio(
    "Click on the map to set:",
    ["🟢 Pickup Location", "🔴 Dropoff Location"],
    horizontal=True
)

st.session_state.selection_mode = 'pickup' if '🟢' in mode else 'dropoff'

# Create the map centered on NYC
nyc_center = [40.7589, -73.9851]  # Times Square
m = folium.Map(
    location=nyc_center,
    zoom_start=12,
    tiles="OpenStreetMap"
)

# Add markers for selected locations
if st.session_state.pickup_coords:
    folium.Marker(
        st.session_state.pickup_coords,
        popup="Pickup",
        tooltip="Pickup Location",
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)

if st.session_state.dropoff_coords:
    folium.Marker(
        st.session_state.dropoff_coords,
        popup="Dropoff",
        tooltip="Dropoff Location",
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)

# Draw route if both locations are selected
if st.session_state.pickup_coords and st.session_state.dropoff_coords:
    try:
        client = openrouteservice.Client(key="eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjhlOWNhMzIyZWU5ZTQ0YTI5ODUxNmUyN2E5NDAyMjhmIiwiaCI6Im11cm11cjY0In0=")
        coords = (
            (st.session_state.pickup_coords[1], st.session_state.pickup_coords[0]),
            (st.session_state.dropoff_coords[1], st.session_state.dropoff_coords[0])
        )

        # Get route geometry from ORS
        route = client.directions(coords, profile='driving-car', format='geojson')

        # Extract coordinates and draw polyline
        folium.GeoJson(
            route,
            name='Driving Route',
            style_function=lambda x: {'color': 'blue', 'weight': 4, 'opacity': 0.8}
        ).add_to(m)

    except Exception as e:
        st.warning(f"⚠️ Route drawing failed: {e}")

# Display the map and capture clicks with return_on_hover=False to reduce reruns
map_data = st_folium(
    m,
    width=None,
    height=500,
    returned_objects=["last_clicked"],
    return_on_hover=False
)

# Handle map clicks with deduplication
if map_data and map_data.get('last_clicked'):
    clicked_lat = map_data['last_clicked']['lat']
    clicked_lng = map_data['last_clicked']['lng']

    # Create a unique identifier for this click
    current_click = f"{clicked_lat}_{clicked_lng}_{st.session_state.selection_mode}"

    # Only process if this is a new click
    if current_click != st.session_state.last_click:
        st.session_state.last_click = current_click

        if st.session_state.selection_mode == 'pickup':
            st.session_state.pickup_coords = [clicked_lat, clicked_lng]
        else:
            st.session_state.dropoff_coords = [clicked_lat, clicked_lng]

# Display selected coordinates
st.markdown("### 📊 Selected Coordinates:")
coord_col1, coord_col2 = st.columns(2)

with coord_col1:
    if st.session_state.pickup_coords:
        st.success(f"**🟢 Pickup:**  \n Lat: {st.session_state.pickup_coords[0]:.6f}  \n Lon: {st.session_state.pickup_coords[1]:.6f}")
    else:
        st.warning("Click on the map to set pickup location")

with coord_col2:
    if st.session_state.dropoff_coords:
        st.success(f"**🔴 Dropoff:**  \n Lat: {st.session_state.dropoff_coords[0]:.6f}  \n Lon: {st.session_state.dropoff_coords[1]:.6f}")
    else:
        st.warning("Click on the map to set dropoff location")

# Reset button
if st.button("🔄 Reset Locations"):
    st.session_state.pickup_coords = None
    st.session_state.dropoff_coords = None
    st.session_state.last_click = None
    st.rerun()

'''
## 🕐 Step 2: Enter Trip Details
'''

col1, col2, col3 = st.columns(3)

with col1:
    date = st.date_input('📅 Date', value=datetime.now())
with col2:
    time = st.time_input('🕐 Time', value=datetime.now().time())
with col3:
    passenger_count = st.number_input('👥 Passengers', min_value=1, max_value=8, value=1, step=1)

'''
## 🔮 Step 3: Get Fare Prediction
'''

# Only allow prediction if both locations are selected
if st.session_state.pickup_coords and st.session_state.dropoff_coords:

    if st.button('💵 Predict Fare', type='primary', use_container_width=True):

        params = {
            'pickup_datetime': f"{date} {time}",
            'pickup_longitude': st.session_state.pickup_coords[1],  # lon
            'pickup_latitude': st.session_state.pickup_coords[0],   # lat
            'dropoff_longitude': st.session_state.dropoff_coords[1],  # lon
            'dropoff_latitude': st.session_state.dropoff_coords[0],   # lat
            'passenger_count': int(passenger_count)
        }

        url = 'https://taxifare.lewagon.ai/predict'

        with st.spinner('🚕 Calculating your fare...'):
            try:
                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    prediction = response.json().get('fare')

                    if prediction:
                        st.balloons()

                        # Display prediction in a nice format
                        st.success(f"## 💰 Estimated Fare: ${np.round(prediction, 2)}")

                        # Show trip details
                        with st.expander("📋 Trip Details"):
                            st.write(f"**Date & Time:** {date} {time}")
                            st.write(f"**Passengers:** {passenger_count}")
                            st.write(f"**Pickup:** ({st.session_state.pickup_coords[0]:.4f}, {st.session_state.pickup_coords[1]:.4f})")
                            st.write(f"**Dropoff:** ({st.session_state.dropoff_coords[0]:.4f}, {st.session_state.dropoff_coords[1]:.4f})")
                    else:
                        st.error("❌ No prediction received from API")

                else:
                    st.warning(f"⚠️ API Error: Status {response.status_code}")
                    st.write("Response:", response.text)

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
else:
    st.info("👆 Please select both pickup and dropoff locations on the map above to enable prediction")
