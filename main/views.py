from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.http import HttpResponse, JsonResponse
from django import template
from django.contrib import messages

from main.td.client import TDClient
from main.td.config import *
from main.td.orders import Order, OrderLeg
from main.td.enums import ORDER_SESSION, DURATION, ORDER_INSTRUCTIONS, ORDER_ASSET_TYPE

from twilio.twiml.messaging_response import Message, MessagingResponse
from twilio.rest import Client
from django.views.decorators.csrf import csrf_exempt

from .models import TradeOptions

from datetime import datetime

TDSession = TDClient(
    account_number=ACCOUNT_NUMBER,
    account_password=PASSWORD,
    consumer_id=CLIENT_ID,
    redirect_uri=REDIRECT_URI,
)
TDSession.login()
print("TD login success!")

months = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]


@login_required(login_url="/login/")
def index(request):
    try:
        trade_option = TradeOptions.objects.all()[0]
        if not trade_option:
            messages.error(request, "Trade option not defined")
            return render(request, "index.html")

        params = {
            "num_options": trade_option.num_options,
            "amt_options": trade_option.amt_options,
            "amt_shares": trade_option.amt_shares,
        }
    except:
        params = {}
        messages.error(request, "Trade option not defined")
    return render(request, "index.html", context=params)


@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        print(request.path)
        load_template = request.path.split("/")[-1]
        html_template = loader.get_template(load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template("error-404.html")
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template("error-500.html")
        return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def save_setting(request):

    if request.method == "POST":

        try:
            trade_option = TradeOptions.objects.all()[0]
        except:
            trade_option = None
            pass

        num_options = request.POST.get("num_options")
        amt_options = request.POST.get("amt_options")
        amt_shares = request.POST.get("amt_shares")
        print(num_options)
        print(amt_options)
        print(amt_shares)

        if trade_option:
            if num_options:
                trade_option.num_options = int(num_options)
            if amt_shares:
                trade_option.amt_shares = float(amt_shares)
            if amt_options:
                trade_option.amt_options = float(amt_options)
            trade_option.save()

            messages.info(request, "Your settings successfully saved!")
            return redirect("/")
        else:

            new_option = TradeOptions(
                num_options=num_options, amt_options=amt_options, amt_shares=amt_shares
            )

            new_option.save()

            messages.info(request, "Your settings successfully saved!")

            return redirect("/")

    else:
        return redirect("/")


def placeOrder(order_dict):
    try:
        trade_option = TradeOptions.objects.all()[0]
        num_options = int(trade_option.num_options)
        amt_options = float(trade_option.amt_options)
        amt_shares = float(trade_option.amt_shares)
        print("Setting load ok!")
    except Exception as e:
        print(e)
        num_options = 1
        amt_options = 200
        amt_shares = 200
    print("number of options: ", num_options)
    print("amount of options: ", amt_options)
    print("amount of shares: ", amt_shares)

    symbol = order_dict["symbol"]
    side = order_dict["side"]
    assetType = order_dict["assetType"]
    if assetType == "OPTION" and side == "BUY":
        side = "BUY_TO_OPEN"
    if assetType == "OPTION" and side == "SELL":
        side = "SELL_TO_CLOSE"

    account_details = TDSession.get_accounts(
        account=ACCOUNT_NUMBER, fields=["positions", "orders"]
    )
    balance = account_details["securitiesAccount"]["projectedBalances"][
        "availableFunds"
    ]
    print("Ballance: ", balance)
    quote = TDSession.get_quotes(instruments=[symbol])
    try:
        multiplier = int(float(quote[symbol]["multiplier"]))
    except:
        multiplier = 1
    if multiplier < 1:
        multiplier = 1

    askPrice = quote[symbol]["askPrice"] / multiplier
    bidPrice = quote[symbol]["bidPrice"] / multiplier

    if "BUY" in side:
        smsPrice = order_dict["price"]
        priceDiff = int((askPrice - smsPrice) / smsPrice * 100)
        if priceDiff > 5:
            return {
                "state": False,
                "err": f"Buy price or 5% higher buy price not available. Current price: {askPrice} Balance: {balance}",
            }

        print("askPrice:", askPrice)
        print("smsPrice:", smsPrice)

        if assetType == "OPTION":
            amount = amt_options
            size = int(amount / askPrice)
            if size == 0:
                size = num_options
        else:
            amount = amt_shares
            size = int(amount / askPrice)
            if size == 0:
                return {
                    "state": False,
                    "err": f"Current price is greater than the amount of shares to buy. Current price: {askPrice} Balance: {balance}",
                }
        print(size, askPrice)
        if size * askPrice > balance:
            return {
                "state": False,
                "err": f"${balance} balance insufficient for ${round(size * askPrice, 2)} trade!",
            }

        trade_amount = round(size * askPrice, 2)

    if "SELL" in side:
        if assetType != "Monkey":
            try:
                positions = account_details["securitiesAccount"]["positions"]
                size = 0
                for position in positions:
                    if position["instrument"]["symbol"] == symbol:
                        size = size + position["longQuantity"]
            except Exception as e:
                print(e)
                return {
                    "state": False,
                    "err": f"Trade position not found. Balance: ${balance}",
                }

        if size == 0:
            return {
                "state": False,
                "err": f"Trade position not found. Balance: ${balance}",
            }

        trade_amount = round(size * bidPrice, 2)

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
                "instrument": {"symbol": symbol, "assetType": assetType},
            }
        ],
    }

    print(newOrder)
    try:
        order_result = TDSession.place_order(account=ACCOUNT_NUMBER, order=newOrder)
        account_details = TDSession.get_accounts(
            account=ACCOUNT_NUMBER, fields=["positions", "orders"]
        )
        new_balance = account_details["securitiesAccount"]["projectedBalances"][
            "availableFunds"
        ]

        if order_result["orderStatus"] == "success":
            return {
                "state": True,
                "order": order_result["order"],
                "success": f"${new_balance} balance after ${trade_amount} trade.",
            }
        else:
            return {
                "state": False,
                "err": f"Unknown. Balance: ${new_balance} Trade amount: ${trade_amount}",
            }
        print("KO")
    except Exception as e:
        return {
            "state": False,
            "err": e + f" Balance: ${balance} Trade amount: ${trade_amount}",
        }


def process_messages(message0):
    message = message0.upper()
    secType = ""
    if "SHARE" in message or "SELL" in message:
        secType = "EQUITY"
    if "CALL" in message or "PUT" in message:
        secType = "OPTION"
    if not secType:
        return {
            "canTrade": False,
            "err": "The asset type is unknown.",
            "symbol": message.split(" ")[1],
        }

    ticker = message.split(" ")[1]
    side = message.split(" ")[0]
    if side == "CLOSE":
        side = "SELL"

    if secType == "OPTION":
        expiry = message.split(" ")[2]
        expiry1 = (
            expiry.replace(expiry[:3], str(months.index(expiry[:3]) + 1).zfill(2))
            + str(datetime.now().year)[-2:]
        )
        strike0 = float(message.split(" ")[3].replace("$", ""))
        if strike0 == int(strike0):
            strike = str(int(strike0))
        else:
            strike = str(strike0)
        putCall = message.split(" ")[4]

        prefix = putCall[0] + strike
        symbol = ticker + "_" + expiry1 + prefix

        option_chain_args = {
            "symbol": ticker,
            "contractType": putCall,
            "strike": strike0
            # "expMonth": expiry[:3]
        }
        try:
            option_chains = TDSession.get_options_chain(
                args_dictionary=option_chain_args
            )
            symbols = [
                list(item.values())[0][0]["symbol"]
                for item in list(option_chains["callExpDateMap"].values())
            ]
        except:
            return {
                "canTrade": False,
                "err": "The symbol is unknown.",
                "symbol": ticker,
            }
        if symbol not in symbols:
            for item in symbols:
                if item > symbol:
                    symbol = item
                    break
            if item == symbols[-1] and item != symbol:
                return {
                    "canTrade": False,
                    "err": "The symbol is unknown.",
                    "symbol": ticker,
                }

    if secType == "EQUITY":
        symbol = ticker

    if side == "BUY":
        price = float(
            message.split("@")[1]
            .strip(" .,")
            .split(" ")[0]
            .strip(" .,")
            .replace("$", "")
        )
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
        "roi": roi,
    }

    return {"canTrade": True, "order": order_dict, "symbol": symbol}


@csrf_exempt
def get_bot_triggers(request):

    print("OK")

    if request.method == "POST":
        num = request.POST.get("From")
        message = request.POST.get("Body")

        result = process_messages(message)
        print(result)

        resp = MessagingResponse()
        client = Client(twilio_sid, twilio_auth)
        _from = twilio_number
        _tos = [item.strip(",. ") for item in broadcast_numbers.split(",")]

        symbol = result["symbol"]
        if not result["canTrade"]:
            err_msg = result["err"]
            msg = f"\n\nHello,\nTrade [{symbol}] failed.\n Details: {err_msg}\n Your sms: {message}"
            resp.message(msg)
            for _to in _tos:
                client.messages.create(to=_to, from_=_from, body=msg)
            return HttpResponse("Message delivered")

        order_result = placeOrder(result["order"])
        if not order_result["state"]:
            err_msg = order_result["err"]
            msg = f"\n\nHello,\nTrade [{symbol}] failed.\n Details: {err_msg}\n Your sms: {message}"
            resp.message(msg)
            for _to in _tos:
                client.messages.create(to=_to, from_=_from, body=msg)
            return HttpResponse("Message delivered")

        msg = f"\n\nHello,\nTrade [{symbol}] executed.\n Details: {order_result['success']}\n Your sms: {message}\n Your order details: \n{order_result['order']}"
        resp.message(msg)
        for _to in _tos:
            client.messages.create(to=_to, from_=_from, body=msg)
        return HttpResponse("Message delivered")

    if request.method == "GET":
        return redirect("/")
