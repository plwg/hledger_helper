from __future__ import annotations

import importlib.metadata
import shutil
from typing import TYPE_CHECKING

import pytest

import hhelper
from hhelper.helpers import fetch_price as fetch_price_module
from hhelper.ui.display import ask_yes_no
from tests.conftest import FakeTerminal

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("reply", "default", "expected"),
    [
        ("", True, True),
        ("", False, False),
        ("Y", False, True),
        ("yes", False, True),
        ("n", True, False),
        ("Q", True, False),
        ("quit", True, False),
    ],
)
def test_ask_yes_no(term, answers, reply: str, default: bool, expected: bool) -> None:
    answers(reply)

    assert ask_yes_no(term, "? ", default=default) is expected


def test_ask_yes_no_asks_again_on_invalid_input(term, answers) -> None:
    answers("maybe", "y")

    assert ask_yes_no(term, "? ", default=False) is True


class MainRunner:
    # Runs hh with a config in a temporary home, choosing the given menu entries
    def __init__(self, home: Path, monkeypatch: pytest.MonkeyPatch, answers) -> None:
        self.journal_dir = home / "finance"
        self.journal_dir.mkdir()
        config_dir = home / ".config" / "hhelper"
        config_dir.mkdir(parents=True)
        self.config = config_dir / "config.toml"
        self.config.write_text(
            "[paths]\n"
            f'directory = "{self.journal_dir}"\n'
            'ledger_file = "my.ledger"\n'
            'price_file = "prices.txt"\n'
            'header_file = "my.ledger.header"\n'
            'recurring_tx_file = "recur.journal"\n'
            "[commodities]\n"
            "commodity_pairs = []\n"
        )
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setattr(hhelper, "Terminal", FakeTerminal)
        self.monkeypatch = monkeypatch
        self.answers = answers

    def __call__(self, *selections: str) -> None:
        choices = iter([*selections, "Exit"])
        self.monkeypatch.setattr(hhelper, "menu", lambda options, term: next(choices))
        self.answers()
        with pytest.raises(SystemExit):
            hhelper.main([])


@pytest.fixture
def run_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answers) -> MainRunner:
    return MainRunner(tmp_path, monkeypatch, answers)


@pytest.mark.parametrize(
    "selection",
    [
        "Mark Transactions as Cleared",
        "Clean Up Journal",
        "Generate Recurring Transactions",
    ],
)
def test_missing_ledger_is_reported(
    run_main, capsys: pytest.CaptureFixture, selection: str
) -> None:
    run_main(selection)

    assert f"File not found: {run_main.journal_dir / 'my.ledger'}" in (
        capsys.readouterr().out
    )


def test_missing_price_file_is_not_an_error(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    run_main("Fetch Prices")

    assert "does not exist yet" in capsys.readouterr().out


def test_config_without_header_file_still_starts(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    run_main.config.write_text(
        run_main.config.read_text().replace('header_file = "my.ledger.header"\n', "")
    )
    (run_main.journal_dir / "my.ledger").write_text("")

    run_main("Clean Up Journal")

    assert "header_file is not set" in capsys.readouterr().out


def test_missing_config_is_explained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    hhelper.main([])

    assert "config file is not found" in capsys.readouterr().out


def test_hh_config_prints_the_location_and_content(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    hhelper.main(["--config"])

    out = capsys.readouterr().out
    assert out.startswith(f"Config file: {run_main.config}\n\n")
    assert out.endswith(run_main.config.read_text())


def test_hh_config_prints_a_config_that_does_not_parse(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    run_main.config.write_text("[paths\nbroken = \n")

    hhelper.main(["--config"])

    assert capsys.readouterr().out.endswith("[paths\nbroken = \n")


def test_hh_config_without_a_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(SystemExit, match="does not exist yet"):
        hhelper.main(["--config"])

    expected = tmp_path / ".config" / "hhelper" / "config.toml"
    assert f"Config file: {expected}" in capsys.readouterr().out


@pytest.mark.parametrize(
    "flags",
    [
        ["--config", "--similar"],
        ["--clean-up", "--fetch-prices"],
        ["--similar", "--clean-up"],
    ],
)
def test_command_line_actions_cannot_be_combined(flags: list[str]) -> None:
    with pytest.raises(SystemExit):
        hhelper.main(flags)


@pytest.mark.skipif(shutil.which("hledger") is None, reason="hledger is not installed")
def test_hh_clean_up_cleans_without_asking(run_main) -> None:
    (run_main.journal_dir / "my.ledger.header").write_text("account assets:bank\n")
    ledger = run_main.journal_dir / "my.ledger"
    ledger.write_text(
        "2024-01-02 b\n    expenses:x  2 USD\n    assets:bank\n\n"
        "2024-01-01 a\n    expenses:x  1 USD\n    assets:bank\n"
    )
    # Any prompt would raise EOFError
    run_main.answers()

    hhelper.main(["--clean-up"])

    text = ledger.read_text()
    assert text.startswith("include ")
    assert text.index("2024-01-01") < text.index("2024-01-02")
    assert any((run_main.journal_dir / ".hhelper" / "backups").iterdir())


def test_hh_clean_up_exits_non_zero_when_nothing_is_written(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    run_main.answers()

    with pytest.raises(SystemExit) as exit_info:
        hhelper.main(["--clean-up"])

    assert exit_info.value.code == 1
    assert "File not found" in capsys.readouterr().out


def test_hh_fetch_prices_writes_without_asking(
    run_main, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pandas as pd

    run_main.config.write_text(
        run_main.config.read_text().replace(
            "commodity_pairs = []",
            "commodity_pairs = [{ symbol = 'ETH-USD', base_currency = 'ETH',"
            " quote_currency = 'USD', is_append_space = true }]",
        )
    )
    prices = run_main.journal_dir / "prices.txt"
    prices.write_text("P 2024-03-01 ETH USD 3000.0\n")
    monkeypatch.setattr(
        fetch_price_module,
        "fetch_hist_price",
        lambda symbol, start_date: pd.DataFrame(
            {"Close": [3050.0]}, index=pd.to_datetime(["2024-03-02"])
        ),
    )
    run_main.answers()

    hhelper.main(["--fetch-prices"])

    assert prices.read_text() == "P 2024-03-02 ETH USD 3050.0\n"


def test_hh_fetch_prices_exits_non_zero_when_nothing_is_fetched(
    run_main, capsys: pytest.CaptureFixture
) -> None:
    run_main.answers()

    with pytest.raises(SystemExit) as exit_info:
        hhelper.main(["--fetch-prices"])

    assert exit_info.value.code == 1
    assert "No prices fetched" in capsys.readouterr().out


def test_hh_version_prints_the_installed_version(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exit_info:
        hhelper.main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"hh {importlib.metadata.version('hhelper')}\n"


@pytest.mark.skipif(shutil.which("hledger") is None, reason="hledger is not installed")
def test_clean_up_includes_the_header_as_written_in_the_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answers
) -> None:
    finance = tmp_path / "finance"
    finance.mkdir()
    (finance / "my.ledger.header").write_text("account assets:bank\n")
    ledger = finance / "my.ledger"
    ledger.write_text("2024-01-01 a\n    expenses:x  1 USD\n    assets:bank\n")
    config_dir = tmp_path / ".config" / "hhelper"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        "[paths]\n"
        'directory = "~/finance/"\n'
        'ledger_file = "my.ledger"\n'
        'price_file = "prices.txt"\n'
        'header_file = "my.ledger.header"\n'
        'recurring_tx_file = "recur.journal"\n'
        "[commodities]\n"
        "commodity_pairs = []\n"
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(hhelper, "Terminal", FakeTerminal)
    choices = iter(["Clean Up Journal", "Exit"])
    monkeypatch.setattr(hhelper, "menu", lambda options, term: next(choices))
    answers("y")

    with pytest.raises(SystemExit):
        hhelper.main([])

    assert ledger.read_text().startswith("include ~/finance/my.ledger.header\n")
