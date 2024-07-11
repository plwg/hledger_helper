#!./.venv/bin/python
import yfinance as yf
import datetime
from pathlib import Path

path = Path('~/finance/fetched_prices.txt').expanduser()

daily_price = []

def fetch_hist_price(name):
    price_history = yf.download(name, start= datetime.datetime(2021,9,1), end = datetime.datetime(2025,1,1),interval='1d')
    return price_history

def parse_hledger_format(price_history, commodity1, commodity2):

    for index, row in price_history.iterrows():
        daily_price.append(f"P {index.date()} {commodity1} {commodity2}{round(row['Close'],2)}\n")

def write_price():
    with open(path,'w') as file_object:
        for price in daily_price:
            file_object.write(price)

parse_hledger_format(fetch_hist_price("ETH-USD"), "ETH", "USD ")
parse_hledger_format(fetch_hist_price("USDCNY=x"), "USD", "CNY ")
parse_hledger_format(fetch_hist_price("USDSGD=x"), "USD", "S$")
write_price()

print(f'Prices successfully written to {path}')
