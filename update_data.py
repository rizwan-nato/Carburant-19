import os
import requests
from zipfile import ZipFile
import time
import pandas as pd
from lxml import objectify
import numpy as np
import pickle
from tqdm import tqdm


def update_data_instant():

    URL_Instant = "https://donnees.roulez-eco.fr/opendata/instantane"


    BASE_CWD = os.getcwd()
    PATH_DATA = BASE_CWD + "/data"
    PATH_TEMP = BASE_CWD + "/temp"

    if not os.path.exists(PATH_DATA):
        os.makedirs(PATH_DATA)
    if not os.path.exists(PATH_TEMP):
        os.makedirs(PATH_TEMP)


    if os.path.exists(os.path.join(PATH_DATA, "instant.csv")):
        last_update = os.path.getctime(os.path.join(PATH_DATA, "instant.csv"))
        if time.time() - last_update < 600:
            print("Not updating instant")
            return



    with requests.get(URL_Instant) as r:
        with open(os.path.join(PATH_TEMP, "file.zip"), "wb") as file:
            file.write(r.content)

        with ZipFile(os.path.join(PATH_TEMP, "file.zip")) as zipObj:
            for f in zipObj.infolist():
                name, date_time = f.filename, f.date_time
                name = os.path.join(PATH_TEMP, name)
                with open(name, 'wb') as outFile:
                    outFile.write(zipObj.open(f).read())
                date_time = time.mktime(date_time + (0, 0, -1))
                os.utime(name, (date_time, date_time))

    xml_data = objectify.parse(name)  # Parse XML data
    pvd_list = xml_data.getroot()  # Root element
    record = []

    for pdv in pvd_list.getchildren():
        new_row = {}
        attrib_pdv = pdv.attrib
        new_row["id"] = attrib_pdv["id"]
        try:
            new_row["latitude"] = float(attrib_pdv["latitude"])/100000
            new_row["longitude"] = float(attrib_pdv["longitude"])/100000
        except:
            print(attrib_pdv)
            continue
        new_row["cp"] = attrib_pdv["cp"]
        new_row["pop"] = attrib_pdv["pop"]
        new_row["adresse"] = pdv.adresse.text
        new_row["ville"] = pdv.ville.text
        if hasattr(pdv, 'prix'):
            for prix in pdv.prix:
                attrib_prix = prix.attrib
                nom = attrib_prix["nom"]
                new_row[f"maj_{nom}"] = pd.to_datetime(attrib_prix["maj"])
                new_row[f"prix_{nom}"] = attrib_prix["valeur"]
        record.append(new_row)

    df_instant = pd.DataFrame.from_records(record)
    df_instant.to_csv(os.path.join(PATH_DATA, "instant.csv"))

    print("Data updated")
    return

def update_data_anual():
    URL_Year = "https://donnees.roulez-eco.fr/opendata/annee"

    BASE_CWD = os.getcwd()
    PATH_DATA = BASE_CWD + "/data"
    PATH_TEMP = BASE_CWD + "/temp"

 
    if not os.path.exists(PATH_DATA):
        os.makedirs(PATH_DATA)
    if not os.path.exists(PATH_TEMP):
        os.makedirs(PATH_TEMP)


    with requests.get(URL_Year) as r:
        with open(os.path.join(PATH_TEMP, "file.zip"), "wb") as file:
            file.write(r.content)

        with ZipFile(os.path.join(PATH_TEMP, "file.zip")) as zipObj:
            for f in zipObj.infolist():
                name, date_time = f.filename, f.date_time
                date_time = time.mktime(date_time + (0, 0, -1))
                name = os.path.join(PATH_TEMP, name)
                if os.path.exists(name):
                    last_update = os.path.getmtime(name)
                    if last_update == date_time:
                        print("Not updating annual file")
                        return
                with open(name, 'wb') as outFile:
                    outFile.write(zipObj.open(f).read())
                os.utime(name, (date_time, date_time))



    E10 = {}
    E85 = {}
    GPLc = {}
    Gazole = {}
    SP95 = {}
    SP98 = {}

    Name_to_dict = {"E10": E10, "E85": E85, "GPLc": GPLc, "Gazole": Gazole, "SP95": SP95, "SP98": SP98}

    xml_data = objectify.parse(name)  # Parse XML data
    pvd_list = xml_data.getroot()  # Root element
    for pdv in tqdm(pvd_list.getchildren()):
        attrib_pdv = pdv.attrib
        id_station = attrib_pdv["id"]
        if hasattr(pdv, 'prix'):
            for prix in pdv.prix:
                attrib_prix = prix.attrib
                if attrib_prix != {}:
                    nom = attrib_prix["nom"]
                    maj = attrib_prix["maj"]
                    price = attrib_prix["valeur"]
                    if id_station in Name_to_dict[nom]:
                        Time, Prices = Name_to_dict[nom][id_station]
                        Time.append(np.datetime64(maj))
                        Prices.append(float(price))
                    else:
                        Time = [pd.to_datetime(maj)]
                        Prices = [price]
                    Name_to_dict[nom][id_station] = Time, Prices
    for name in Name_to_dict:
        for id in Name_to_dict[name]:
            T,P = Name_to_dict[name][id]
            T = np.array(T, dtype="datetime64")
            P = np.array(P, dtype="float64")
            argsort = np.argsort(T)
            T = T[argsort]
            P = P[argsort]
            Name_to_dict[name][id] = T,P
    for name in Name_to_dict:
        with open(os.path.join(PATH_DATA, name), 'wb') as fp:
            pickle.dump(Name_to_dict[name], fp)
    print("Data updated")
    return


if __name__ == "__main__":
    update_data_instant()
    update_data_anual()