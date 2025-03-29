import requests 
import json 

symbol = 'BTC'

def ask_bid(symbol):

    url = "https://api.hyperliquid.xyz/info"
    headers = {'Content-Type': 'application/json'}

    data = {
        'type': 'l2Book', 
        'coin': symbol, 
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    print(f'symbol: {symbol}... ')
    l2_data = l2_data['levels']

    bid = float(l2_data[0][0]['px'])
    ask = float(l2_data[1][0]['px'])

    return ask, bid, l2_data

def get_current_price(coin):
    """ fetch the current price for a given symbol"""
    ask, bid, _ = ask_bid(symbol)
    return (ask + bid) / 2


