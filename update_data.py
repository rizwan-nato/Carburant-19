import os
import requests
from zipfile import ZipFile
import time


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