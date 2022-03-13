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
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

with streamlit_analytics.track():


    update_data_instant()
    update_data_anual()

    st.title("Comparateur de station")
  
    st.write("Où sont les stations essence les moins chères autour de vous ? Voici une carte mise à jour quotidiennement. Choisissez le type de carburant recherché, l'adresse ainsi la distance de recherche dans les filtres.")
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
        ('SP95-E10', 'Gazole', 'SP98','GPLc', 'E85'))

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
    if location is None:
        location = geolocator.geocode(f"Paris, France")
        rue = 'Paris'
        st.sidebar.write("Erreur: Adresse non trouvée")
    R = st.sidebar.number_input('Distance de recherche (Km)', value=5)
    loc_button = Button(label="Me localiser", button_type="primary")
    loc_button.js_on_event(
        "button_click",
        CustomJS(
            code="""
        navigator.geolocation.getCurrentPosition(
            (loc) => {
                document.dispatchEvent(new CustomEvent("GET_LOCATION", {detail: {lat: loc.coords.latitude, lon: loc.coords.longitude}}))
            }
        )
        """
        ),
    )
    
    result = streamlit_bokeh_events(
    loc_button,
    events="GET_LOCATION",
    key="get_location",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0,)

    if result:
        if "GET_LOCATION" in result:
            loc = result.get("GET_LOCATION")
            lat = loc.get("lat")
            lon = loc.get("lon")
    else:
        lat = location.latitude
        lon = location.longitude

    station_to_plot = df_instant.apply(lambda row: get_close_station(lat, lon, row, R), axis=1)

    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], tooltip=rue).add_to(m)
    min_prix = np.inf
    max_prix = -np.inf
    for index, row in df_instant[station_to_plot].iterrows():
        prix = row[f"prix_{suffixe}"]
        if prix < min_prix:
            min_prix = prix
        if prix > max_prix:
            max_prix = prix

    colorscale = branca.colormap.StepColormap(colors=["green", "orange", "red", "darkred"], vmin=min_prix, vmax=max_prix)
    colorscale.add_to(m)
    color_dict = {"#008000ff": "green", "#ffa500ff": "orange", "#ff0000ff": "red", "#8b0000ff": "darkred"}

    for index, row in df_instant[station_to_plot].iterrows():
        if not pd.isna(row[f'prix_{suffixe}']):
            lat_row = row["latitude"]
            lon_row = row["longitude"]
            adresse = row["adresse"]
            ville = row["ville"]
            T,P = data_year[str(index)]
            T = pd.DataFrame(T, columns=["Date"])
            P = pd.DataFrame(P, columns=[f"Prix"])
            chart_data = pd.concat([T,P], axis=1)
            c = alt.Chart(chart_data).mark_line().encode(
                x='Date', 
                y=alt.Y("Prix", scale=alt.Scale(zero=False))
            ).properties(
            title="Historique du prix",
            )

            folium.Marker(
                location=[lat_row, lon_row],
                tooltip= f"<b>{row[f'prix_{suffixe}']}€</b><br><br>{adresse}<br><br>{ville}",
                icon=folium.Icon(color=color_dict[colorscale(row[f"prix_{suffixe}"])]),
                popup=folium.Popup(max_width=450).add_child(folium.VegaLite(c))
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

    st.write("Les données sont issus des des données publiques des prix des carburants. Un arrêté ministériel en date du 12 décembre 2006 modifié par un arrêté en date du 7 avril 2009 rend obligatoire la déclaration des prix pratiqués pour tout gérant de point de vente de carburants ayant vendu au moins 500 mètres cube des carburants SP95, gazole, E85, GPLC, SP95-E10, SP98. Le non respect de cette obligation est passible d'une amende, le contrôle des prix étant effectué par la DGCCRF.")


