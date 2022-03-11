import streamlit as st
import pandas as pd
import numpy as np
from update_data import update_data

import geopy.distance
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from streamlit_folium import folium_static
import folium
import branca


def get_close_station(lat, lon, row, distance):
    coord1 = (lat,lon)
    coord2 = (row["latitude"], row["longitude"])
    if geopy.distance.geodesic(coord1, coord2).km < distance:
        return True
    else: return False


@st.experimental_memo
def load_data():
    df = pd.read_csv("test.csv")
    return df

df = load_data()


genre = st.sidebar.radio(
     "Quel carburant voulez vous?",
     ('SP95', 'SP95-E10', 'Gazoil', 'SP98'))

rue = st.sidebar.text_input("Adresse", "35 Avenue de Stalingrad, Fresnes")

geolocator = Nominatim(user_agent="GTA Lookup")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
location = geolocator.geocode(f"{rue}, France")
R = st.sidebar.number_input('Distance de recherche', value=5)

lat = location.latitude
lon = location.longitude

station_to_plot = df.apply(lambda row: get_close_station(lat, lon, row, R), axis=1)

m = folium.Map(location=[lat, lon], zoom_start=13)
folium.Marker([lat, lon]).add_to(m)
min_prix = np.inf
max_prix = -np.inf
for index, row in df[station_to_plot].iterrows():
    prix = row['prix_E10']
    if prix < min_prix:
        min_prix = prix
    if prix > max_prix:
        max_prix = prix

colorscale = branca.colormap.StepColormap(colors=["green", "orange", "red", "darkred"], vmin=min_prix, vmax=max_prix)
color_dict = {"#008000ff": "green", "#ffa500ff": "orange", "#ff0000ff": "red", "#8b0000ff": "darkred"}

for index, row in df[station_to_plot].iterrows():
    if not pd.isna(row['prix_E10']):
        lat_row = row["latitude"]
        lon_row = row["longitude"]
        folium.Marker(
            location=[lat_row, lon_row],
            popup=f"{row['prix_E10']}€ \n{row['maj_E10']}",
            icon=folium.Icon(color=color_dict[colorscale(row['prix_E10'])])
        ).add_to(m)
folium_static(m)

st.dataframe(df[station_to_plot][["adresse", "ville", "prix_E10", "maj_E10"]])