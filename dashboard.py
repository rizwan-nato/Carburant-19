import streamlit as st
import pandas as pd
import numpy as np
import os
from update_data import update_data_instant, update_data_anual

import geopy.distance
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from streamlit_folium import folium_static
import folium
import branca
from time import time
import streamlit_analytics.streamlit_analytics as streamlit_analytics
import pickle
import altair as alt

with streamlit_analytics.track():


    update_data_instant()
    update_data_anual()

    st.title("Compratareur de station")

    BASE_CWD = os.getcwd()
    PATH_DATA = BASE_CWD + "/data"

    def get_close_station(lat, lon, row, distance):
        coord1 = (lat,lon)
        coord2 = (row["latitude"], row["longitude"])
        if geopy.distance.geodesic(coord1, coord2).km < distance:
            return True
        else: return False


    @st.experimental_memo
    def load_data():
        df_instant = pd.read_csv(os.path.join(PATH_DATA, "instant.csv"), index_col="id")
        return df_instant

    df_instant = load_data()


    carburant = st.sidebar.radio(
        "Quel carburant voulez vous?",
        ('SP95-E10', 'Gazole', 'SP98'))

    if carburant == "SP95-E10":
        suffixe = "E10"
    else:
        suffixe = carburant
    
    df_instant[f"maj_{suffixe}"] = pd.to_datetime(df_instant[f"maj_{suffixe}"])
    with open(os.path.join(PATH_DATA, suffixe), 'rb') as fp:
        data_year = pickle.load(fp)

    rue = st.sidebar.text_input("Adresse", "Antony")

    geolocator = Nominatim(user_agent="GTA Lookup")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location = geolocator.geocode(f"{rue}, France")
    R = st.sidebar.number_input('Distance de recherche', value=5)

    lat = location.latitude
    lon = location.longitude

    station_to_plot = df_instant.apply(lambda row: get_close_station(lat, lon, row, R), axis=1)

    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], popup=rue).add_to(m)
    min_prix = np.inf
    max_prix = -np.inf
    for index, row in df_instant[station_to_plot].iterrows():
        prix = row[f"prix_{suffixe}"]
        if prix < min_prix:
            min_prix = prix
        if prix > max_prix:
            max_prix = prix

    colorscale = branca.colormap.StepColormap(colors=["green", "orange", "red", "darkred"], vmin=min_prix, vmax=max_prix)
    color_dict = {"#008000ff": "green", "#ffa500ff": "orange", "#ff0000ff": "red", "#8b0000ff": "darkred"}

    for index, row in df_instant[station_to_plot].iterrows():
        if not pd.isna(row[f'prix_{suffixe}']):
            lat_row = row["latitude"]
            lon_row = row["longitude"]
            folium.Marker(
                location=[lat_row, lon_row],
                popup=f"{row[f'prix_{suffixe}']}€ \n{row[f'maj_{suffixe}']}",
                icon=folium.Icon(color=color_dict[colorscale(row[f"prix_{suffixe}"])])
            ).add_to(m)
    folium_static(m)


    colms = st.columns((2, 1, 1, 1, 1))
    fields = ["Adresse", 'Ville', f'Prix {carburant}', 'Dernière mise à jour']
    for col, field_name in zip(colms, fields):
        # header
        col.write(field_name)

    for x, iterrow in enumerate(df_instant[station_to_plot].sort_values(f"prix_{suffixe}", ascending=True).iterrows()):
        index, row = iterrow
        if not pd.isna(row[f'prix_{suffixe}']):
            col1, col2, col3, col4, col5 = st.columns((2, 1, 1, 1, 1))
            col1.write(row["adresse"])
            col2.write(row["ville"])
            col3.write(row[f"prix_{suffixe}"])
            col4.write(row[f"maj_{suffixe}"])

            button_type = "Voir l'historique"
            button_phold = col5.empty()  # create a placeholder
            do_action = button_phold.button(button_type, key=x)
            if do_action:
                st.write(f"Historique de prix de la station")
                T,P = data_year[str(index)]
                T = pd.DataFrame(T, columns=["Date"])
                P = pd.DataFrame(P, columns=[f"Prix"])
                chart_data = pd.concat([T,P], axis=1)
                c = alt.Chart(chart_data).mark_line().encode(
                    x='Date', 
                    y=alt.Y("Prix", scale=alt.Scale(zero=False))
                )

                st.altair_chart(c.interactive(), use_container_width=True)
                pass

