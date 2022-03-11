import os
import requests
from zipfile import ZipFile
import time
import pandas as pd
from lxml import objectify


def update_data():

    URL_Year = "https://donnees.roulez-eco.fr/opendata/annee"
    URL_Instant = "https://donnees.roulez-eco.fr/opendata/instantane"


    BASE_CWD = os.getcwd()
    PATH_DATA = BASE_CWD + "/data"
    PATH_TEMP = BASE_CWD + "/temp"

    if not os.path.exists(PATH_DATA):
        os.makedirs(PATH_DATA)
    if not os.path.exists(PATH_TEMP):
        os.makedirs(PATH_TEMP)


    for URL in [URL_Instant, URL_Year]:
        with requests.get(URL) as r:
            with open(os.path.join(PATH_TEMP, "file.zip"), "wb") as file:
                file.write(r.content)

        with ZipFile(os.path.join(PATH_TEMP, "file.zip")) as zipObj:
            for f in zipObj.infolist():
                name, date_time = f.filename, f.date_time
                name = os.path.join(PATH_DATA, name)
                with open(name, 'wb') as outFile:
                    outFile.write(zipObj.open(f).read())
                date_time = time.mktime(date_time + (0, 0, -1))
                os.utime(name, (date_time, date_time))

    xml_data = objectify.parse('data/PrixCarburants_instantane.xml')  # Parse XML data
    pvd_list = xml_data.getroot()  # Root element
    record = []

    for pdv in pvd_list.getchildren():
        new_row = {}
        attrib_pdv = pdv.attrib
        new_row["id"] = attrib_pdv["id"]
        new_row["latitude"] = float(attrib_pdv["latitude"])/100000
        new_row["longitude"] = float(attrib_pdv["longitude"])/100000
        new_row["cp"] = attrib_pdv["cp"]
        new_row["pop"] = attrib_pdv["pop"]
        new_row["adresse"] = pdv.adresse.text
        new_row["ville"] = pdv.ville.text
        if hasattr(pdv, 'prix'):
            for prix in pdv.prix:
                attrib_prix = prix.attrib
                nom = attrib_prix["nom"]
                new_row[f"maj_{nom}"] = attrib_prix["maj"]
                new_row[f"prix_{nom}"] = attrib_prix["valeur"]
        record.append(new_row)

    df_instant = pd.DataFrame.from_records(record)
    df_instant.to_csv("test.csv")

    print("Data updated")
    return