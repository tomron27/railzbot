from datetime import datetime, timedelta
import requests
import json
from fuzzywuzzy import process, fuzz
from config import *


def get_stations(use_cache=True):
    if not use_cache:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            raise ValueError("Error - Return Code: {}".format(response.status_code))
        data = json.loads(response.content)['Data']['CustomPropertys']
    else:
        with open("stations.json", encoding="utf-8") as stations:
            data = json.load(stations)['Data']['CustomPropertys']
    eng_station_id, heb_station_id = {}, {}
    for item in data:
        heb_station_id[item['Heb'][0]] = item['Id']
        eng_station_id[item['Eng'][0]] = item['Id']

    eng_id_station = {v: k for k, v in eng_station_id.items()}
    heb_id_station = {v: k for k, v in heb_station_id.items()}
    return eng_station_id, heb_station_id, eng_id_station, heb_id_station


def get_time_diff(code, delta, str_time):
    timestamp = datetime.strptime(str_time, '%d/%m/%Y %H:%M:%S')
    if code == 'מקדימה':
        new_timestamp = timestamp - timedelta(minutes=delta)
    elif code == 'מתעכבת':
        new_timestamp = timestamp + timedelta(minutes=delta)
    else:
        new_timestamp = timestamp
    return new_timestamp.strftime('%H:%M')


def get_combined_station_id_dict():
    eng_station_id, heb_station_id, _, _ = get_stations()
    return {k: v for (k, v) in list(eng_station_id.items()) + list(heb_station_id.items())}


def get_fuzzy_station_name(query):
    eng_station_id, heb_station_id, _, _ = get_stations()
    stations = list(eng_station_id.keys()) + list(heb_station_id.keys())
    res = process.extractOne(query, stations, scorer=fuzz.UWRatio)
    return res
