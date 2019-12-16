import requests
import json
from datetime import datetime, timedelta

base_url = "https://www.rail.co.il/apiinfo/api/Plan/GetRoutes"
route_limit = 5

def get_stations(use_cache=True):
    if not use_cache:
        response = requests.get(base_url)
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
    if code == 'AHEAD':
        new_timestamp = timestamp - timedelta(minutes=delta)
    elif code == 'DELAYED':
        new_timestamp = timestamp + timedelta(minutes=delta)
    else:
        new_timestamp = timestamp
    res = "arrive at {}".format(new_timestamp.strftime('%H:%M'))
    return res


eng_station_id, heb_station_id, eng_id_station, heb_id_station = get_stations()


start_station = 'Haifa-Hof HaKarmel (Razi`el)'
end_station = 'Caesarea-Pardes Hana'

now = datetime.now()
# now = datetime(year=2019, month=12, day=16, hour=8, minute=0, second=0)

url = base_url + "?" \
      "OId={}&TId={}&Date={}&Hour={}&isGoing=true&c=1572448829822".format(
    eng_station_id[start_station],
    eng_station_id[end_station],
    now.strftime("%Y%m%d"),
    now.strftime("%H%M")
)

response = requests.get(url)
if response.status_code != 200:
    raise ValueError("Error - Return Code: {}".format(response.status_code))

data = json.loads(response.content)['Data']
if data['Error'] is not None:
    raise ValueError("Received server error: {}".format(data['Error']))

routes = data['Routes']
train_positions = {x['TrainNumber']: x for x in data['TrainPositions']}

response = ""
try:
    if len(routes) == 0:
        response = "No available routes. Try again later.\n"
    for i, route in enumerate(routes[:route_limit]):
        response += "Route {}:\n".format(i+1)
        for train in route['Train']:
            train_id = int(train['Trainno'])
            depart_time = datetime.strptime(train['DepartureTime'], '%d/%m/%Y %H:%M:%S')
            arrival_time = datetime.strptime(train['ArrivalTime'], '%d/%m/%Y %H:%M:%S')
            time_span = "{} {}->{}".format(depart_time.strftime('%d/%m/%y'),
                                          depart_time.strftime('%H:%M'),
                                          arrival_time.strftime('%H:%M'))
            response += " Train id: {} (from {} to {}), {}\n   Status: ".format(train_id,
                                                               eng_id_station[train['OrignStation']],
                                                               eng_id_station[train['DestinationStation']],
                                                                                             time_span)
            try:
                dif_type, dif_min = train_positions[train_id]['DifType'], train_positions[train_id]['DifMin']
                if dif_min == 0 and dif_type == "":
                    dif_type = "ON TIME"
                if dif_type == "DELAY":
                    dif_type = "DELAYED"
                if dif_type == "ON TIME":
                    response += dif_type
                else:
                    alt_time = get_time_diff(dif_type, dif_min, train['ArrivalTime'])
                    response += dif_type + " by {} minutes ({})".format(dif_min, alt_time)
            except KeyError:
                response += "No itinerary data for {}, please try again later.".format(train_id)
            finally:
                response += "\n"
    print(response)
except () as e:
    print(e)
