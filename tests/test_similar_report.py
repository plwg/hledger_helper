from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import shutil
import subprocess

import pytest

import hhelper
from hhelper.helpers.similar_report import (
    HledgerError,
    account_counts,
    accounts_under,
    how_to,
    description_counts,
    similar_accounts,
    similar_report,
)
from tests.conftest import requires_hledger

if TYPE_CHECKING:
    from pathlib import Path

LEDGER = """\
account assets:bank
account expenses:food
account expenses:unused

include years/*.journal

2024-01-01 Whole Foods
    expenses:food  10 USD
    assets:bank

2024-01-06 Whole Foods
    expenses:food  10 USD
    assets:bank

2024-01-02 whole foods
    Expenses:Food  5 USD
    assets:bank

2024-01-03 Whole Food
    expenses:grocerys  1 USD
    assets:bank

2024-01-04 Rent
    expenses:rent  2 USD
    assets:bank

2024-01-05 Tent
    expenses:camping  2 USD
    assets:bank
"""

INCLUDED = """\
2023-05-01 Starbuck
    expenses:coffee  3 USD
    assets:bank

2023-05-02 Starbucks
    expenses:coffee  3 USD
    assets:bank

2023-05-03 Starbucks
    expenses:groceries  3 USD
    assets:bank
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    (tmp_path / "years").mkdir()
    (tmp_path / "years" / "2023.journal").write_text(INCLUDED)
    path = tmp_path / "my.ledger"
    path.write_text(LEDGER)
    return path


def test_similar_accounts_compares_siblings_only() -> None:
    names = {
        "Expenses:Food",
        "expenses:food",
        "expenses:grocerys",
        "expenses:groceries",
        "assets:bank",
        "liabilities:bank",
    }

    assert similar_accounts(names) == [
        ("Expenses", "expenses"),
        ("expenses:groceries", "expenses:grocerys"),
    ]


def test_accounts_under_lists_used_subaccounts() -> None:
    counts = Counter(
        {"Expenses:Food": 2, "Expenses:Food:coffee": 1, "Expenses:Rent": 0, "x": 1}
    )

    assert (
        accounts_under(counts, "Expenses") == "; in Expenses:Food, Expenses:Food:coffee"
    )
    assert (
        accounts_under(counts, "Expenses", limit=1) == "; in Expenses:Food and 1 more"
    )
    assert accounts_under(counts, "x") == ""


@requires_hledger
def test_counts_include_included_files(ledger: Path) -> None:
    descriptions = description_counts(ledger)
    accounts = account_counts(ledger)

    assert descriptions["Starbucks"] == 2
    assert descriptions["Whole Foods"] == 2
    assert accounts["expenses:coffee"] == 2
    assert accounts["expenses:unused"] == 0


@requires_hledger
def test_report_lists_variants_and_leaves_files_alone(ledger: Path) -> None:
    before = sorted(p.name for p in ledger.parent.rglob("*"))

    report = similar_report(ledger)

    assert "    'Whole Food'  (1)  similar" in report
    assert "    'whole foods'  (1)  written differently" in report
    assert "    'Starbuck'  (1)  similar" in report
    assert "    expenses:grocerys  (1)  similar" in report
    assert "    Expenses  (1)  written differently; in Expenses:Food" in report
    assert "'Tent'" not in report
    assert sorted(p.name for p in ledger.parent.rglob("*")) == before


@requires_hledger
def test_unreadable_journal_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("2024-01-01 a\n    x  1 USD\n    y  1 USD\n")

    with pytest.raises(HledgerError):
        similar_report(ledger)


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ledger: Path) -> Path:
    config_dir = tmp_path / "home" / ".config" / "hhelper"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        "[paths]\n"
        f'directory = "{ledger.parent}"\n'
        'ledger_file = "my.ledger"\n'
        'price_file = "prices.txt"\n'
        'header_file = "my.ledger.header"\n'
        'recurring_tx_file = "recur.journal"\n'
        "[commodities]\n"
        "commodity_pairs = []\n"
    )
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return config_dir


@requires_hledger
@pytest.mark.usefixtures("config_home")
def test_hh_similar_prints_the_report(capsys: pytest.CaptureFixture) -> None:
    hhelper.main(["--similar"])

    assert "Descriptions: 2 groups of possible variants" in capsys.readouterr().out


@pytest.mark.usefixtures("config_home")
def test_hh_similar_with_a_missing_ledger(ledger: Path) -> None:
    ledger.unlink()

    with pytest.raises(SystemExit, match="File not found"):
        hhelper.main(["--similar"])


@requires_hledger
@pytest.mark.skipif(
    subprocess.run(["sed", "--version"], capture_output=True).returncode != 0,
    reason="needs GNU sed",
)
def test_the_suggested_sed_commands_work(ledger: Path) -> None:
    # Run the commands exactly as the report prints them
    files = [str(ledger), str(ledger.parent / "years" / "2023.journal")]
    lines = how_to(ledger, files)
    account = next(line for line in lines if "account:" in line).split(":", 1)[1]
    description = next(line for line in lines if "description:" in line).split(":", 1)[
        1
    ]

    for command in (
        account.replace("OLD", "expenses:grocerys").replace(
            "NEW", "expenses:groceries"
        ),
        account.replace("OLD", "Expenses").replace("NEW", "expenses"),
        description.replace("OLD", "whole foods").replace("NEW", "Whole Foods"),
    ):
        subprocess.run(command, shell=True, check=True)

    report = similar_report(ledger)
    assert "grocerys" not in report
    assert "Expenses" not in report
    assert "'whole foods'" not in report
    assert (
        subprocess.run(
            [shutil.which("hledger") or "hledger", "check", "-f", str(ledger)]
        ).returncode
        == 0
    )
