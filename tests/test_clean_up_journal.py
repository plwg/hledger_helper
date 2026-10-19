from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from hhelper.helpers.clean_up_journal import clean_up_journal
from hhelper.helpers.return_status import STATUS
from tests.conftest import requires_hledger

if TYPE_CHECKING:
    from pathlib import Path

TRANSACTIONS = """\
2024-01-02 later
    expenses:food  2.5 USD
    assets:bank

2024-01-01 earlier
    expenses:rent  100 USD
    assets:bank
"""


def hledger_print(path: Path) -> str:
    return subprocess.run(
        ["hledger", "print", "-x", "-f", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    ledger = tmp_path / "my.ledger"
    header = tmp_path / "my.ledger.header"
    ledger.write_text("account assets:bank\n\n" + TRANSACTIONS)
    header.write_text("account assets:bank\n")
    return ledger, header


@requires_hledger
def test_sorts_and_keeps_the_header(files, term, answers) -> None:
    ledger, header = files
    before = hledger_print(ledger)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT

    text = ledger.read_text()
    assert text.startswith("account assets:bank\n")
    assert text.index("earlier") < text.index("later")
    assert hledger_print(ledger) == before


@requires_hledger
def test_declining_changes_nothing(files, term, answers) -> None:
    ledger, header = files
    original = ledger.read_text()
    answers("n")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.NOWAIT
    assert ledger.read_text() == original


@requires_hledger
def test_unreadable_ledger_is_left_unchanged(files, term, answers) -> None:
    ledger, header = files
    unbalanced = "2024-01-01 a\n    x  1 USD\n    y  2 USD\n"
    ledger.write_text(unbalanced)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT
    assert ledger.read_text() == unbalanced


@requires_hledger
def test_included_transactions_are_not_duplicated(
    files, term, answers, capsys: pytest.CaptureFixture
) -> None:
    ledger, header = files
    (ledger.parent / "other.journal").write_text(
        "2024-01-10 included\n    expenses:x  5 USD\n    assets:bank\n"
    )
    header.write_text("include other.journal\n")
    original = "include other.journal\n\n" + TRANSACTIONS
    ledger.write_text(original)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT
    assert ledger.read_text() == original
    assert "would read differently" in capsys.readouterr().out


@pytest.mark.parametrize("header_exists", [False, None])
def test_missing_header_is_explained(
    files, term, answers, capsys: pytest.CaptureFixture, header_exists
) -> None:
    ledger, header = files
    original = ledger.read_text()
    header.unlink()
    answers("y")

    header_arg = None if header_exists is None else header
    assert clean_up_journal(ledger, header_arg, ledger, term) == STATUS.WAIT
    assert ledger.read_text() == original
    assert "header file" in capsys.readouterr().out
