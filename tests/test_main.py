from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import hhelper
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


def test_hh_config_and_similar_cannot_be_combined() -> None:
    with pytest.raises(SystemExit):
        hhelper.main(["--config", "--similar"])
