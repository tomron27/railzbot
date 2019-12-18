# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import json
import requests
from utils import get_stations, get_time_diff, get_combined_station_id_dict
from config import BASE_URL, ROUTE_LIMIT


def get_routes(start_station, end_station, timestamp):

    station_id_dict = get_combined_station_id_dict()
    start_station_id = station_id_dict[start_station]
    end_station_id = station_id_dict[end_station]
    _, _, eng_id_station, heb_id_station = get_stations()

    # timestamp = datetime(year=2019, month=12, day=16, hour=8, minute=0, second=0)

    url = BASE_URL + "?" \
          "OId={}&TId={}&Date={}&Hour={}&isGoing=true&c=1572448829822".format(
        start_station_id,
        end_station_id,
        timestamp.strftime("%Y%m%d"),
        timestamp.strftime("%H%M")
    )

    response = requests.get(url)
    if response.status_code != 200:
        return "Error - Return Code: {}".format(response.status_code)

    data = json.loads(response.content)['Data']
    if data['Error'] is not None:
        return "Received server error: {}".format(data['Error'])

    start_index = data['StartIndex']
    routes = data['Routes'][start_index:]
    train_positions = {x['TrainNumber']: x for x in data['TrainPositions']}
    congestion = {x['TrainNumber']: x for x in data['Omasim']}

    response = ""
    try:
        if len(routes) == 0:
            response = "אין רכבות זמינות. אנא נסה/י מאוחר יותר.\n"
        for i, route in enumerate(routes[:ROUTE_LIMIT]):
            response += "*מסלול {}*:\n".format(i+1)
            for j, train in enumerate(route['Train']):
                if j > 0:
                    response += "_החלפה_\n"
                train_id = int(train['Trainno'])
                response += "רכבת מס': {} (מ{} אל {})\n".format(train_id,
                                                                heb_id_station[train['OrignStation']],
                                                                heb_id_station[train['DestinationStation']])
                depart_time = datetime.strptime(train['DepartureTime'], '%d/%m/%Y %H:%M:%S')
                arrival_time = datetime.strptime(train['ArrivalTime'], '%d/%m/%Y %H:%M:%S')
                duration = (arrival_time-depart_time).seconds // 60
                time_span = "*{} {}->{} (משך {} דקות)*\n".format(depart_time.strftime('%d/%m/%y'),
                                              depart_time.strftime('%H:%M'),
                                              arrival_time.strftime('%H:%M'),
                                                           duration)

                cong_data = congestion[train_id]['Stations']
                station_cong_data = {x['StationNumber']: x for x in cong_data}
                platform = station_cong_data[int(train['OrignStation'])]['Platform']
                station_cong = station_cong_data[int(train['OrignStation'])]['OmesPercent']
                response += "רציף {}, מדד עומס {:.2f}\n".format(platform, station_cong)
                response += time_span
                status = "סטטוס: "
                try:
                    dif_type, dif_min = train_positions[train_id]['DifType'], train_positions[train_id]['DifMin']
                    if dif_min == 0 and dif_type == "":
                        dif_type = "בזמן"
                    if dif_type == "DELAY":
                        dif_type = "מתעכבת"
                    if dif_type == "AHEAD":
                        dif_type = "מקדימה"
                    if dif_type == "בזמן":
                        status += dif_type + "."
                    else:
                        if depart_time < timestamp - timedelta(minutes=dif_min):  #TODO - can be ahead as well..
                            alt_time = get_time_diff(dif_type, dif_min, train['ArrivalTime'])
                            status += dif_type + " כ-{} דקות (תגיע ב {}).".format(dif_min, alt_time)
                        else:
                            alt_time = get_time_diff(dif_type, dif_min, train['DepartureTime'])
                            status += dif_type + " כ-{} דקות (תצא ב {}).".format(dif_min, alt_time)
                        status = "*" + status + "*"
                except KeyError:
                    status += "אין סטטוס איחורים.".format(train_id)
                finally:
                    response += status + "\n"
        return response
    except Exception as e:
        return str(e)
