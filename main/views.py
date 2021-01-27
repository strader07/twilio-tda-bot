
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.http import HttpResponse, JsonResponse
from django import template

from main.td.client import TDClient
from main.td.config import ACCOUNT_NUMBER, PASSWORD, CLIENT_ID, REDIRECT_URI
from main.td.orders import Order, OrderLeg
from main.td.enums import ORDER_SESSION, DURATION, ORDER_INSTRUCTIONS, ORDER_ASSET_TYPE

from twilio.twiml.messaging_response import Message, MessagingResponse
from django.views.decorators.csrf import csrf_exempt

from datetime import datetime

TDSession = TDClient(account_number = ACCOUNT_NUMBER,
                     account_password = PASSWORD,
                     consumer_id = CLIENT_ID,
                     redirect_uri = REDIRECT_URI)
TDSession.login()
print("TD login success!")

months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def index(request):
    return render(request, "index.html")


def pages(request):
    context = {}
    try:
        print(request.path)
        load_template = request.path.split('/')[-1]
        html_template = loader.get_template( load_template )
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template( 'error-404.html' )
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template( 'error-500.html' )
        return HttpResponse(html_template.render(context, request))


def placeOrder(order_dict):
    symbol = order_dict["symbol"]
    side = order_dict["side"]
    assetType = order_dict["assetType"]
    if assetType == "OPTION" and side=="BUY":
        side = "BUY_TO_OPEN"
    if assetType == "OPTION" and side=="SELL":
        side = "SELL_TO_CLOSE"

    account_details = TDSession.get_accounts(account=ACCOUNT_NUMBER, fields=["positions", "orders"])
    if "BUY" in side:
        balance = account_details["securitiesAccount"]["currentBalances"]["cashAvailableForTrading"]
        quote = TDSession.get_quotes(instruments = [symbol])

        askPrice = quote[symbol]["askPrice"]
        smsPrice = order_dict["price"]
        priceDiff = int((askPrice - smsPrice) / smsPrice * 100)
        if priceDiff > 5:
            return {"state":False, "err": "Buy price or 5% higher buy price not available."}

        if balance >= 250:
            size = int(250/askPrice)
        else:
            size = int(balance/askPrice)
        if size != 0:
            return {"state":False, "err": "Insufficient Funds!"}

    if "SELL" in side:
        try:
            positions = account_details["positions"]
            size = 0
            for position in positions:
                if position["instrument"]["symbol"] == symbol:
                    size = size + position["longQuantity"]
        except Exception as e:
            print(e)
            return {"state":False, "err": "Trade can't be found."}

        if size == 0:
            return {"state":False, "err": "Trade can't be found."}

    # Initalize a new Order Object.
    newOrder = {
        "complexOrderStrategyType": "NONE",
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": side,
                "quantity": size,
                "instrument": {
                    "symbol": symbol,
                    "assetType": assetType
                }
            }
        ]
    }

    # order_status = TDSession.place_order(account = ACCOUNT_NUMBER, order = newOrder)
    return {"state":True, "order": newOrder}


def process_messages(message0):
    message = message0.upper()
    secType = ""
    if "SHARE" in message or "SELL" in message:
        secType = "EQUITY"
    if "CALL" in message or "PUT" in message:
        secType = "OPTION"
    if not secType:
        return {"canTrade": False, "err": "The asset type is unknown.", "symbol": message.split(" ")[1]}

    ticker = message.split(" ")[1]
    side = message.split(" ")[0]
    if side == "CLOSE":
        side = "SELL"

    if secType == "OPTION":
        expiry = message.split(" ")[2]
        expiry1 = expiry.replace(expiry[:3], str(months.index(expiry[:3])+1).zfill(2)) + str(datetime.now().year)[-2:]
        strike0 = float(message.split(" ")[3].replace("$", ""))
        if strike0 == int(strike0):
            strike = str(int(strike0))
        else:
            strike = str(strike0)
        putCall = message.split(" ")[4]

        prefix = putCall[0]+strike
        symbol = ticker+"_"+expiry1+prefix

        option_chain_args = {
            "symbol": ticker,
            "contractType": putCall,
            "strike": strike0
            # "expMonth": expiry[:3]
        }
        try:
            option_chains = TDSession.get_options_chain(args_dictionary=option_chain_args)
            symbols = [list(item.values())[0][0]["symbol"] for item in list(option_chains["callExpDateMap"].values())]
        except:
            return {"canTrade": False, "err": "The symbol is unknown.", "symbol": ticker}
        if symbol not in symbols:
            for item in symbols:
                if item > symbol:
                    symbol = item
                    break
        if item == symbols[-1] and item != symbol:
            return {"canTrade": False, "err": "The symbol is unknown.", "symbol": ticker}

    if secType == "EQUITY":
        symbol = ticker

    if side == "BUY":
        price = float(message.split("@")[1].strip(" .,").split(" ")[0].strip(" .,").replace("$", ""))
        roi = 0
    else:
        price = 0
        roi = float([x for x in message.split(" ") if "%" in x][0].replace("%", ""))

    order_dict = {
        "side": side,
        "assetType": secType,
        "price": price,
        "symbol": symbol,
        "underlyingSymbol": ticker,
        "roi": roi
    }

    return {"canTrade": True, "order": order_dict, "symbol": symbol}


@csrf_exempt
def get_bot_triggers(request):

    if request.method == 'POST':
        num = request.POST.get('From')
        message = request.POST.get('Body')

        result = process_messages(message)
        symbol = result["symbol"]
        if not result["canTrade"]:
            resp = MessagingResponse()
            err_msg = result["err"]
            resp.message(f"\nHello {num}, Trade [{symbol}] failed.\n Reason: {err_msg}\n Your sms: {message}")
            return HttpResponse(str(resp))

        order_result = placeOrder(result["order"])
        if not order_result["state"]:
            resp = MessagingResponse()
            err_msg = order_result["err"]
            resp.message(f"\nHello {num}, Trade [{symbol}] failed.\n Reason: {err_msg}\n Your sms: {message}")
            return HttpResponse(str(resp))

        resp = MessagingResponse()
        resp.message(f"\nHello {num}, Trade [{symbol}] executed.\n Your order details: \n")
        return HttpResponse(str(resp))

    if request.method == 'GET':
        return redirect('/')