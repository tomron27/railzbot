from datetime import datetime, timedelta
import json
import requests
from utils import get_stations, get_time_diff, get_combined_station_id_dict
from config import BASE_URL, ROUTE_LIMIT


def get_routes(start_station, end_station):

    station_id_dict = get_combined_station_id_dict()
    start_station_id = station_id_dict[start_station]
    end_station_id = station_id_dict[end_station]
    _, _, eng_id_station, heb_id_station = get_stations()

    now = datetime.now()

    # now = datetime(year=2019, month=12, day=16, hour=8, minute=0, second=0)

    url = BASE_URL + "?" \
          "OId={}&TId={}&Date={}&Hour={}&isGoing=true&c=1572448829822".format(
        start_station_id,
        end_station_id,
        now.strftime("%Y%m%d"),
        now.strftime("%H%M")
    )

    response = requests.get(url)
    if response.status_code != 200:
        return "Error - Return Code: {}".format(response.status_code)

    data = json.loads(response.content)['Data']
    if data['Error'] is not None:
        return "Received server error: {}".format(data['Error'])

    routes = data['Routes']
    train_positions = {x['TrainNumber']: x for x in data['TrainPositions']}

    response = ""
    try:
        if len(routes) == 0:
            response = "אין רכבות זמינות. אנא נסה/י מאוחר יותר.\n"
        for i, route in enumerate(routes[:ROUTE_LIMIT]):
            response += "מסלול {}:\n".format(i+1)
            for train in route['Train']:
                train_id = int(train['Trainno'])
                depart_time = datetime.strptime(train['DepartureTime'], '%d/%m/%Y %H:%M:%S')
                arrival_time = datetime.strptime(train['ArrivalTime'], '%d/%m/%Y %H:%M:%S')
                time_span = "{} {}<-{}".format(depart_time.strftime('%d/%m/%y'),
                                              depart_time.strftime('%H:%M'),
                                              arrival_time.strftime('%H:%M'))
                response += "רכבת מס': {} (מ{} אל {}), {}\n".format(train_id,
                                                                   heb_id_station[train['OrignStation']],
                                                                   heb_id_station[train['DestinationStation']],
                                                                                                 time_span)
                response += "סטטוס: "
                try:
                    dif_type, dif_min = train_positions[train_id]['DifType'], train_positions[train_id]['DifMin']
                    if dif_min == 0 and dif_type == "":
                        dif_type = "בזמן"
                    if dif_type == "DELAY":
                        dif_type = "מתעכבת"
                    if dif_type == "AHEAD":
                        dif_type = "מקדימה"
                    if dif_type == "בזמן":
                        response += dif_type
                    else:
                        if depart_time < now:
                            alt_time = get_time_diff(dif_type, dif_min, train['ArrivalTime'])
                            response += dif_type + " כ-{} דקות (תגיע ב {})".format(dif_min, alt_time)
                        else:
                            alt_time = get_time_diff(dif_type, dif_min, train['DepartureTime'])
                            response += dif_type + " כ-{} דקות (תצא ב {})".format(dif_min, alt_time)

                except KeyError:
                    response += "לא נמצאו לוחות זמנים.".format(train_id)
                finally:
                    response += "\n"
        return response
    except Exception as e:
        return str(e)