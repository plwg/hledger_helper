import re
from collections import namedtuple
from datetime import datetime as dt
from datetime import timedelta

import yfinance as yf

from .return_status import STATUS


def fetch_hist_price(name, start_date):
    # Return price history
    return yf.download(
        name, start=start_date, interval="1d", progress=False, multi_level_index=False
    )


def parse_hledger_format(price_history, commodity1, commodity2, append_space):
    prices = []

    for index, row in price_history.iterrows():
        prices.append(
            f"P {index.date()} {commodity1} {commodity2}{' ' if append_space else ''}{round(row['Close'], 2)}\n"
        )

    return prices


def fetch_price(price_file_path, commodity_pairs, term):
    with price_file_path.open() as file_object:
        lines = file_object.readlines()

    date_pat = re.compile(r"\d\d\d\d-\d\d-\d\d")

    latest_date = max(date_pat.search(line).group(0) for line in lines)

    latest_date = dt.strptime(latest_date, "%Y-%m-%d")
    start_date = latest_date - timedelta(days=30)
    start_date_str = str(start_date)[:10]

    daily_price = []

    CommodityPair = namedtuple("CommodityPair", commodity_pairs[0])

    commodity_pairs = [CommodityPair(**cp) for cp in commodity_pairs]

    for pair in commodity_pairs:
        daily_price.extend(
            parse_hledger_format(
                fetch_hist_price(pair.symbol, start_date),
                pair.base_currency,
                pair.quote_currency,
                pair.is_append_space,
            )
        )

    latest_date = max(date_pat.search(line).group(0) for line in daily_price)

    print(term.clear + term.home)
    print("".join(daily_price))
    print(f"Fetched {len(daily_price)} postings from {start_date_str} to {latest_date}")

    descision = input(term.green("Write to file? (Y/n/q): ")).lower()

    if descision in {"", "y", "yes"}:
        pass

    elif descision in {"n", "no", "q", "quit"}:
        return STATUS.NOWAIT

    else:
        raise ValueError

    daily_price.extend(
        line for line in lines if date_pat.search(line).group(0) < start_date_str
    )
    daily_price.sort()

    with price_file_path.open("w") as file_object:
        file_object.writelines(daily_price)

    print(f"Prices successfully written to {price_file_path}")

    return STATUS.WAIT
