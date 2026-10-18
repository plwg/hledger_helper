from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from hhelper.helpers import fetch_price as fetch_price_module
from hhelper.helpers.fetch_price import (
    CommodityPairConfig,
    fetch_price,
    parse_hledger_format,
)
from hhelper.helpers.return_status import STATUS

if TYPE_CHECKING:
    from pathlib import Path

ETH: CommodityPairConfig = {
    "symbol": "ETH-USD",
    "base_currency": "ETH",
    "quote_currency": "USD",
    "is_append_space": True,
}
SGD: CommodityPairConfig = {
    "symbol": "USDSGD=x",
    "base_currency": "USD",
    "quote_currency": "S$",
    "is_append_space": False,
}


def history(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": [close for _, close in rows]},
        index=pd.to_datetime([date for date, _ in rows]),
    )


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch):
    # Replaces Yahoo Finance: maps a symbol to the rows it returns
    data: dict[str, list[tuple[str, float]]] = {}
    monkeypatch.setattr(
        fetch_price_module,
        "fetch_hist_price",
        lambda symbol, start_date: history(data.get(symbol, [])),
    )
    return data


def test_parse_hledger_format_skips_missing_prices() -> None:
    prices = parse_hledger_format(
        history([("2024-03-02", 3100.123), ("2024-03-03", float("nan"))]),
        "ETH",
        "USD",
        append_space=True,
    )

    assert prices == ["P 2024-03-02 ETH USD 3100.12\n"]


def test_parse_hledger_format_without_space() -> None:
    prices = parse_hledger_format(
        history([("2024-03-02", 1.35)]), "USD", "S$", append_space=False
    )

    assert prices == ["P 2024-03-02 USD S$1.35\n"]


def test_replaces_only_recent_prices_of_fetched_pairs(
    tmp_path: Path, term, answers, downloads, capsys: pytest.CaptureFixture
) -> None:
    prices = tmp_path / "prices.txt"
    prices.write_text(
        "; my prices\n"
        "commodity 1,000.00 USD\n"
        "P 2024-01-01 ETH USD 100.0\n"
        "P 2024-03-01 ETH USD 3000.0\n"
        "P 2024-03-01 USD S$1.34\n"
        "P 2024-03-02 GOLD USD 2000.0\n"
    )
    downloads["ETH-USD"] = [("2024-03-02", 3050.0)]
    answers("y")

    assert fetch_price(prices, [ETH, SGD], term) == STATUS.WAIT

    assert prices.read_text() == (
        "; my prices\n"
        "commodity 1,000.00 USD\n"
        "P 2024-01-01 ETH USD 100.0\n"
        "P 2024-03-01 USD S$1.34\n"
        "P 2024-03-02 ETH USD 3050.0\n"
        "P 2024-03-02 GOLD USD 2000.0\n"
    )
    assert "No prices fetched for USDSGD=x" in capsys.readouterr().out


def test_nothing_fetched_leaves_the_file_unchanged(
    tmp_path: Path, term, answers, downloads
) -> None:
    prices = tmp_path / "prices.txt"
    prices.write_text("P 2024-03-01 ETH USD 3000.0\n")
    answers("y")

    assert fetch_price(prices, [ETH], term) == STATUS.WAIT
    assert prices.read_text() == "P 2024-03-01 ETH USD 3000.0\n"


def test_declining_leaves_the_file_unchanged(
    tmp_path: Path, term, answers, downloads
) -> None:
    prices = tmp_path / "prices.txt"
    prices.write_text("P 2024-03-01 ETH USD 3000.0\n")
    downloads["ETH-USD"] = [("2024-03-02", 3050.0)]
    answers("n")

    assert fetch_price(prices, [ETH], term) == STATUS.NOWAIT
    assert prices.read_text() == "P 2024-03-01 ETH USD 3000.0\n"


def test_missing_price_file_is_created(
    tmp_path: Path, term, answers, downloads
) -> None:
    prices = tmp_path / "prices.txt"
    downloads["ETH-USD"] = [("2024-03-02", 3050.0)]
    answers("y")

    fetch_price(prices, [ETH], term)

    assert prices.read_text() == "P 2024-03-02 ETH USD 3050.0\n"


def test_price_file_without_dates_fetches_recent_prices(
    tmp_path: Path, term, answers, monkeypatch: pytest.MonkeyPatch
) -> None:
    prices = tmp_path / "prices.txt"
    prices.write_text("; no prices yet\n")
    start_dates = []

    def fake_fetch(symbol: str, start_date):
        start_dates.append(start_date)
        return history([])

    monkeypatch.setattr(fetch_price_module, "fetch_hist_price", fake_fetch)
    answers("y")

    fetch_price(prices, [ETH], term)

    [start_date] = start_dates
    assert (pd.Timestamp.now() - pd.Timestamp(start_date)).days == 30
