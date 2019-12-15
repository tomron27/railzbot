import requests
import json
from datetime import date

stations = {'hashalom': '4600',
            'sapir': '3310',
            'hedera': '3100',
            'herzlia': '3500',
            'hof_hakarmel': '2300',
            'pardes_hana': '2820',
            'binyamina': '2800',
            'bat_galim': '2200'
            }

fStation = 'hof_hakarmel'
tStation = 'pardes_hana'

departure = '1754'
departureParsed = '17:54:00'

today = date.today().strftime('%Y%m%d')
todayParsed = date.today().strftime('%d/%m/%Y')
url = f'https://www.rail.co.il/apiinfo/api/Plan/GetRoutes?' \
    f'OId={stations[fStation]}&TId={stations[tStation]}&Date={today}&Hour={departure}&isGoing=true&c=1572448829822'
response = requests.get(url)
Routes = json.loads(response.content)['Data']['Routes']
TrainPositions = json.loads(response.content)['Data']['TrainPositions']
try:
    for rout in Routes:
        if str(rout['Train'][0]['DepartureTime']) == f'{todayParsed} {departureParsed}':
            trainNum = rout['Train'][0]['Trainno']
    assert 'trainNum' in locals(), "could not find the train number"
    for pos in TrainPositions:
        if str(trainNum) == str(pos['TrainNumber']):
            delay = pos['DifMin']
    assert 'delay' in locals(), ("There no available data for this train yet, please try again later\n"
                                 "(data is usually available 1 hour before departure)")
    print(f'Train num: {trainNum} from: {fStation} to: {tStation} will be delayed by {delay} minutes\n'
          f'Leave by {int(departure) - 10 + delay} by foot \nor by '
          f'{int(departure) + delay - 5} if you have a cool scooter ')
except () as e:
    print(e)