#!./.venv/bin/python
import re
from datetime import datetime as dt
from datetime import timedelta as timedelta
from pathlib import Path

import yfinance as yf


def fetch_hist_price(name, start_date):
    price_history = yf.download(name, start=start_date, interval="1d")
    return price_history


def parse_hledger_format(price_history, commodity1, commodity2):
    prices = []

    for index, row in price_history.iterrows():
        prices.append(
            f"P {index.date()} {commodity1} {commodity2}{round(row['Close'],2)}\n"
        )

    return prices


def main():
    path = Path("~/finance/fetched_prices.txt").expanduser()

    with open(path, "r") as file_object:
        lines = file_object.readlines()

    date_pat = re.compile(r"\d\d\d\d-\d\d-\d\d")

    latest_date = max(date_pat.search(line).group(0) for line in lines)

    latest_date = dt.strptime(latest_date, "%Y-%m-%d")
    start_date = latest_date - timedelta(days=30)
    start_date_str = str(start_date)[:10]

    daily_price = []

    daily_price.extend(
        parse_hledger_format(fetch_hist_price("ETH-USD", start_date), "ETH", "USD ")
    )
    daily_price.extend(
        parse_hledger_format(fetch_hist_price("USDCNY=x", start_date), "USD", "CNY ")
    )
    daily_price.extend(
        parse_hledger_format(fetch_hist_price("USDSGD=x", start_date), "USD", "S$")
    )

    latest_date = max(date_pat.search(line).group(0) for line in daily_price)

    print(f"Fetched {len(daily_price)} postings from {start_date_str} to {latest_date}")

    for line in lines:
        if date_pat.search(line).group(0) < start_date_str:
            daily_price.append(line)

    daily_price.sort()

    with open(path, "w") as file_object:
        file_object.writelines(daily_price)

    print(f"Prices successfully written to {path}")


if __name__ == "__main__":
    main()
