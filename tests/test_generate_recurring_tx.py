from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from hhelper.helpers import generate_recurring_tx as recurring_module
from hhelper.helpers.generate_recurring_tx import generate_recurring_tx
from hhelper.helpers.return_status import STATUS
from tests.conftest import requires_hledger

if TYPE_CHECKING:
    from pathlib import Path

RULE = "~ monthly from 2024-01-01\n    expenses:rent  100 USD\n    assets:bank\n"


@pytest.fixture
def recurring(tmp_path: Path) -> Path:
    path = tmp_path / "recur.journal"
    path.write_text(RULE)
    return path


def is_valid(path: Path) -> bool:
    return (
        subprocess.run(
            ["hledger", "check", "-f", str(path)], capture_output=True
        ).returncode
        == 0
    )


@requires_hledger
@pytest.mark.parametrize(
    "existing",
    ["", "2024-01-01 a\n    x  1 USD\n    y\n", "2024-01-01 a\n    x  1 USD\n    y"],
    ids=["empty", "final newline", "no final newline"],
)
def test_appends_generated_transactions(
    tmp_path: Path, recurring: Path, term, answers, existing: str
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text(existing)
    answers("2024-02", "y", "q")

    assert generate_recurring_tx(ledger, recurring, term) == STATUS.NOWAIT
    assert ledger.read_text().count("expenses:rent") == 1
    assert is_valid(ledger)


@requires_hledger
def test_default_answer_does_not_append(
    tmp_path: Path, recurring: Path, term, answers
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("")
    answers("2024-02", "", "q")

    generate_recurring_tx(ledger, recurring, term)

    assert ledger.read_text() == ""


@requires_hledger
def test_warnings_do_not_discard_the_preview(
    tmp_path: Path,
    recurring: Path,
    term,
    answers,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    real_run = subprocess.run

    def run_with_warning(*args, **kwargs):
        result = real_run(*args, **kwargs)
        result.stderr = "hledger: warning: something minor\n"
        return result

    monkeypatch.setattr(recurring_module.subprocess, "run", run_with_warning)
    ledger = tmp_path / "my.ledger"
    ledger.write_text("")
    answers("2024-02", "y", "q")

    generate_recurring_tx(ledger, recurring, term)

    assert ledger.read_text().count("expenses:rent") == 1
    assert "something minor" in capsys.readouterr().out


@requires_hledger
def test_invalid_period_asks_again(
    tmp_path: Path, recurring: Path, term, answers
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("")
    answers("not a period", "q")

    assert generate_recurring_tx(ledger, recurring, term) == STATUS.NOWAIT
    assert ledger.read_text() == ""
