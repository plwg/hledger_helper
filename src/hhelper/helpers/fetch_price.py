from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypedDict, cast

from hhelper.helpers.return_status import STATUS
from hhelper.helpers.safe_write import safe_write
from hhelper.ui.display import ask_yes_no

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd
    from blessed import Terminal


class CommodityPairConfig(TypedDict):
    # One entry of commodity_pairs in config.toml
    symbol: str
    base_currency: str
    quote_currency: str
    is_append_space: bool


@dataclass
class CommodityPair:
    symbol: str
    base_currency: str
    quote_currency: str
    is_append_space: bool


def fetch_hist_price(name: str, start_date: datetime) -> pd.DataFrame:
    # Imported lazily: yfinance pulls in pandas, which dominates startup time
    import yfinance as yf

    # Return price history
    return yf.download(
        name,
        start=start_date,
        interval="1d",
        progress=False,
        multi_level_index=False,
        auto_adjust=True,
    )


def parse_hledger_format(
    price_history: pd.DataFrame, commodity1: str, commodity2: str, append_space: bool
) -> list[str]:
    prices = []

    for index, row in price_history.iterrows():
        index = cast("pd.Timestamp", index)
        close = cast("float", row["Close"])

        # yfinance can return rows without a price, e.g. for the current day
        if math.isnan(close):
            continue

        prices.append(
            f"P {index.date()} {commodity1} {commodity2}{' ' if append_space else ''}{round(close, 2)}\n"
        )

    return prices


def is_refetched(line: str, date: str, refetched_prefixes: list[str]) -> bool:
    # Matches the lines parse_hledger_format writes: "P DATE BASE QUOTE[ ]AMOUNT"
    head = f"P {date} "
    if not line.startswith(head):
        return False

    rest = line[len(head) :]
    for prefix in refetched_prefixes:
        if rest.startswith(prefix):
            amount_start = rest[len(prefix) : len(prefix) + 1]
            if amount_start.isdigit() or amount_start == "-":
                return True

    return False


def fetch_price(
    price_file_path: Path,
    commodity_pairs: list[CommodityPairConfig],
    term: Terminal,
) -> STATUS:
    with price_file_path.open() as file_object:
        lines = file_object.readlines()

    date_pat = re.compile(r"\d\d\d\d-\d\d-\d\d")

    dates = []
    for line in lines:
        line_date = date_pat.search(line)

        if line_date is not None:
            dates.append(line_date.group(0))
    if dates:
        latest_date = datetime.strptime(max(dates), "%Y-%m-%d")
    else:
        # No prices yet: fetch the last 30 days
        latest_date = datetime.combine(datetime.now().date(), datetime.min.time())

    start_date = latest_date - timedelta(days=30)
    start_date_str = str(start_date)[:10]

    daily_price = []
    # Only pairs that returned prices have their existing prices replaced
    refetched_prefixes = []
    failed_symbols = []

    commodity_pairs_list = [CommodityPair(**cp) for cp in commodity_pairs]

    for pair in commodity_pairs_list:
        prices = parse_hledger_format(
            fetch_hist_price(pair.symbol, start_date),
            pair.base_currency,
            pair.quote_currency,
            pair.is_append_space,
        )

        if prices:
            daily_price.extend(prices)
            refetched_prefixes.append(
                f"{pair.base_currency} {pair.quote_currency}"
                f"{' ' if pair.is_append_space else ''}"
            )
        else:
            failed_symbols.append(pair.symbol)

    dp_dates = []
    for dp in daily_price:
        dp_date = date_pat.search(dp)

        if dp_date is not None:
            dp_dates.append(dp_date.group(0))
    if not dp_dates:
        print(
            f"No prices fetched since {start_date_str}, {price_file_path} is left unchanged"
        )
        return STATUS.WAIT

    latest_dp_date = max(dp_dates)

    print(term.clear + term.home)
    print("".join(daily_price))
    print(
        f"Fetched {len(daily_price)} postings from {start_date_str} to {latest_dp_date}"
    )

    if failed_symbols:
        print(
            term.yellow(
                f"No prices fetched for {', '.join(failed_symbols)};"
                " their existing prices are kept"
            )
        )

    if not ask_yes_no(term, "Write to file? (Y/n/q): ", default=True):
        return STATUS.NOWAIT

    # Lines without a date (comments, directives) are kept at the top, in order
    undated_lines = []

    for line in lines:
        date = date_pat.search(line)

        if date is None:
            if line.strip():
                undated_lines.append(line)

        elif date.group(0) < start_date_str or not is_refetched(
            line, date.group(0), refetched_prefixes
        ):
            daily_price.append(line)

    daily_price.sort()

    safe_write(price_file_path, "".join(undated_lines + daily_price))

    print(f"Prices successfully written to {price_file_path}")

    return STATUS.WAIT
