from datetime import datetime, timedelta
import requests
import json
from fuzzywuzzy import process, fuzz
from config import *
import telegram
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread
import time


# Bot utils
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
    if code == 'מתעכבת':
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


def get_route(update, context, timestamp):
    depart_station = context.user_data['depart_station']
    dest_station = context.user_data['dest_station']
    res = get_routes(depart_station, dest_station, timestamp)
    update.message.reply_text(res, parse_mode=telegram.ParseMode.MARKDOWN)


def past_route_keyboard(update, context):
    conv_end_reply_keyboard = [['סיימתי', 'חיפוש חדש', 'צור תזכורת']]
    update.message.reply_text("איך עוד אפשר לעזור?", reply_markup=telegram.ReplyKeyboardMarkup(conv_end_reply_keyboard,
                                                                                               resize_keyboard=True,
                                                                                               one_time_keyboard=True))


def notify(context):
    recv_context = context.job.context
    chat_id = recv_context.user_data['chat_id']
    context.bot.send_message(chat_id=chat_id, text="תזכורת מסלולים:")
    depart_station = recv_context.user_data['depart_station']
    dest_station = recv_context.user_data['dest_station']
    res = get_routes(depart_station, dest_station, datetime.now())
    context.bot.send_message(chat_id=chat_id, text=res, parse_mode=telegram.ParseMode.MARKDOWN)


# Server / HTTP Utils
def server():
    logger.info("TCP server started")
    httpd = TCPServer(("", 8080), WakeupHandler)
    httpd.serve_forever()


class WakeupHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/wakeup':
            logger.info("Wake up url invoked")
            self.send_response(200, message="I'm still alive")
            self.end_headers()


def wakeup_worker(wake_url, rep=30):
    logger.info("Wake up worker invoked")
    while True:
        res = requests.get(wake_url, verify=False)
        if res.status_code != 200:
            logger.warn("Wake up method encountered a bad response: {}".format(res))
        time.sleep(rep)


def wakeup_warpper(app_url):
    # Wakeup Server
    server_thread = Thread(target=server)
    server_thread.daemon = True
    server_thread.start()

    # Wakeup worker
    wakeup_thread = Thread(target=wakeup_worker, args=(app_url + 'wakeup', WAKEUP_PERIOD))
    wakeup_thread.daemon = True
    wakeup_thread.start()
