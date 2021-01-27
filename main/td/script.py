from td.client import TDClient
import json
from pprint import pprint
from time import sleep
opn = {}
cls = {}
i = 0
# create a new session
while(True) : 
    TDSession = TDClient(account_number = 'mitchking777',
                        account_password = 'Iplayguitar01@',
                        consumer_id = 'X1SGTF29ZIPFEABYL9DGLM7UDL4H1FGH',
                        redirect_uri = 'http://localhost/test'
                        )

    # login to the session
    TDSession.login()

    #data = TDSession.get_quotes(instruments='MSFT')
    data = TDSession.get_quotes(instruments=['AMZN','SQ', 'MSFT', 'SA', 'AN'])


    for key,value in data.items() :

        if key in opn:
            opn[key].append(value["openPrice"])
            cls[key].append(value["closePrice"])
        else:
            opn[key] = []
            opn[key].append(value["openPrice"])
            cls[key] = []
            cls[key].append(value["closePrice"])
    i = i + 1
    print(i)
    if i < 30:
        sleep(1)
    else:
        break
#print(opn)
#print(cls)
diff = {}
for val in range(30):
    for key in opn.keys():
        if key in diff:
            diff[key].append(opn[key][val] - cls[key][val])
        else:
            diff[key] = []
            diff[key].append(opn[key][val] - cls[key][val])
green = {}
red = {}
for key in diff.keys():
    for val in diff[key]:
        if key in green:
            if val < 0:
                green[key].append(abs(val))
        else:
            if val < 0:
                green[key] = []
                green[key].append(abs(val))
        if key in red:
            if val > 0:
                red[key].append(abs(val))
        else:
            if val > 0:
                red[key] = []
                red[key].append(abs(val))
for key in green.keys():
    print("green", key, sum(green[key]))
for key in red.keys():
    print("red", key, sum(red[key]))
