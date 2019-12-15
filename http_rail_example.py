import requests
import json
from datetime import date, datetime

base_url = "https://www.rail.co.il/apiinfo/api/Plan/GetRoutes"


def get_stations(use_cache=True):
    if not use_cache:
        response = requests.get(base_url)
        if response.status_code != 200:
            raise ValueError("Error - Return Code: {}".format(response.status_code))
        data = json.loads(response.content)['Data']['CustomPropertys']
    else:
        with open("stations.json", encoding="utf-8") as stations:
            data = json.load(stations)['Data']['CustomPropertys']
    eng_ids, heb_ids = {}, {}
    for item in data:
        heb_ids[item['Heb'][0]] = item['Id']
        eng_ids[item['Eng'][0]] = item['Id']
    return eng_ids, heb_ids


eng_station_id, heb_station_id = get_stations()
eng_id_station = {v: k for k, v in eng_station_id.items()}
heb_id_station = {v: k for k, v in heb_station_id.items()}

start_station = 'Haifa-Hof HaKarmel (Razi`el)'
end_station = 'Caesarea-Pardes Hana'

# now = datetime.now()
now = datetime(year=2019, month=12, day=16, hour=8, minute=0, second=0)

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
    for i, route in enumerate(routes):
        response += "Route {}:\n".format(i+1)
        for train in route['Train']:
            train_id = int(train['Trainno'])
            response += "Train id {} from {} to {}: ".format(train_id,
                                                               eng_id_station[train['OrignStation']],
                                                               eng_id_station[train['DestinationStation']],)
            try:
                dif_type, dif_min = train_positions[train_id]['DifType'], train_positions[train_id]['DifMin']
                if dif_type == 0 and dif_type == "":
                    dif_type = "ON TIME"
                if dif_type == "DELAY":
                    dif_type = "DELAYED"

                if dif_type == "ON TIME":
                    response += dif_type
                else:
                    response += dif_type + " by {} minutes\n".format(dif_min)
            except KeyError:
                response += "No itinerary data for Train id {}, try again later\n".format(train_id)
                continue
        # if str(route['Train'][0]['DepartureTime']) == f'{todayParsed} {departureParsed}':
        #     trainNum = rout['Train'][0]['Trainno']
    # assert 'trainNum' in locals(), "could not find the train number"
    # for pos in TrainPositions:
    #     if str(trainNum) == str(pos['TrainNumber']):
    #         delay = pos['DifMin']
    # assert 'delay' in locals(), ("There no available data for this train yet, please try again later\n"
    #                              "(data is usually available 1 hour before departure)")
    # print(f'Train num: {trainNum} from: {fStation} to: {tStation} will be delayed by {delay} minutes\n'
    #       f'Leave by {int(departure) - 10 + delay} by foot \nor by '
    #       f'{int(departure) + delay - 5} if you have a cool scooter ')
    print(response)
except () as e:
    print(e)