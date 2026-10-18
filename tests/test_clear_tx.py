from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from hhelper.helpers import clear_tx as clear_tx_module
from hhelper.helpers.clear_tx import (
    clear_tx,
    is_transaction_header,
    is_transaction_header_cleared,
)
from hhelper.helpers.return_status import STATUS
from tests.conftest import requires_hledger

if TYPE_CHECKING:
    from pathlib import Path

JOURNAL = """\
2024-01-01 * already cleared
    expenses:food  1.00 USD
    assets:bank

2024-01-02 groceries
    expenses:food  2.00 USD
    assets:bank

2024-01-03 ! pending rent
    expenses:rent  3.00 USD
    assets:bank

01-04 no year
    expenses:fun  4.00 USD
    assets:bank
"""


@pytest.fixture
def no_hledger_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        clear_tx_module, "check_valid_journal", lambda text, ledger_path: True
    )


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "my.ledger"
    path.write_text(JOURNAL)
    return path


def headers(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line[:1].isdigit()]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("2024-01-31 payee", True),
        ("01-31 payee", True),
        ("2024/01/31 payee", True),
        ("2024.01.31 payee", True),
        ("2024-02-30 not a date", False),
        ("    2024-01-31 indented", False),
        ("; 2024-01-31 comment", False),
    ],
)
def test_is_transaction_header(line: str, expected: bool) -> None:
    assert is_transaction_header(line) is expected


def test_is_transaction_header_cleared() -> None:
    assert is_transaction_header_cleared("2024-01-31 * payee")
    assert not is_transaction_header_cleared("2024-01-31 ! payee")
    assert not is_transaction_header_cleared("2024-01-31 payee")


@pytest.mark.usefixtures("no_hledger_check")
def test_clear_one_and_skip_one(ledger: Path, term, answers) -> None:
    answers("", "y", "n", "q")

    assert clear_tx(ledger, term) == STATUS.NOWAIT
    assert headers(ledger) == [
        "2024-01-01 * already cleared",
        "2024-01-02 * groceries",
        "2024-01-03 ! pending rent",
        "01-04 no year",
    ]


@pytest.mark.usefixtures("no_hledger_check")
def test_clear_all_replaces_pending_marks(ledger: Path, term, answers) -> None:
    answers("", "a")

    assert clear_tx(ledger, term) == STATUS.WAIT
    assert headers(ledger) == [
        "2024-01-01 * already cleared",
        "2024-01-02 * groceries",
        "2024-01-03 * pending rent",
        "01-04 * no year",
    ]


@pytest.mark.usefixtures("no_hledger_check")
def test_regex_query_limits_clear_all(ledger: Path, term, answers) -> None:
    answers("rent", "a", "q")

    clear_tx(ledger, term)

    assert headers(ledger)[1:] == [
        "2024-01-02 groceries",
        "2024-01-03 * pending rent",
        "01-04 no year",
    ]


@pytest.mark.usefixtures("no_hledger_check")
def test_invalid_regex_asks_again(ledger: Path, term, answers) -> None:
    answers("(", "q")

    assert clear_tx(ledger, term) == STATUS.NOWAIT
    assert ledger.read_text() == JOURNAL


@pytest.mark.usefixtures("no_hledger_check")
def test_generated_transaction_comment_is_removed(
    tmp_path: Path, term, answers
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text(
        "2024-01-01 rent\n"
        "    ; generated-transaction: ~ monthly\n"
        "    expenses:rent  1.00 USD\n"
        "    assets:bank\n"
    )
    answers("", "y")

    clear_tx(ledger, term)

    assert ledger.read_text() == (
        "2024-01-01 * rent\n    expenses:rent  1.00 USD\n    assets:bank\n"
    )


@pytest.mark.usefixtures("no_hledger_check")
def test_transaction_without_postings(tmp_path: Path, term, answers) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("2024-01-01 lonely\n; top-level comment\n")
    answers("", "a")

    assert clear_tx(ledger, term) == STATUS.WAIT
    assert headers(ledger) == ["2024-01-01 * lonely"]


@pytest.mark.usefixtures("no_hledger_check")
@pytest.mark.parametrize("date", ["2024/01/05", "2024.01.05", "01/05"])
def test_non_dash_dates_are_refused(
    tmp_path: Path, term, answers, capsys: pytest.CaptureFixture, date: str
) -> None:
    ledger = tmp_path / "my.ledger"
    original = (
        f"2024-01-01 ok\n    a  1 USD\n    b\n\n{date} payee\n    a  1 USD\n    b\n"
    )
    ledger.write_text(original)
    answers("", "a")

    assert clear_tx(ledger, term) == STATUS.WAIT
    assert ledger.read_text() == original
    assert "must use '-'" in capsys.readouterr().out


@pytest.mark.usefixtures("no_hledger_check")
# The screen is cleared twice before the first transaction, then once per clear
@pytest.mark.parametrize(("interrupt_at", "saved"), [(2, 0), (3, 1), (4, 2)])
def test_ctrl_c_during_clear_all_keeps_progress(
    ledger: Path,
    term,
    answers,
    monkeypatch: pytest.MonkeyPatch,
    interrupt_at: int,
    saved: int,
) -> None:
    calls = []
    real_clear_screen = clear_tx_module.clear_screen_move_to_bottom

    def interrupting_clear_screen(term) -> None:
        calls.append(None)
        if len(calls) == interrupt_at:
            raise KeyboardInterrupt
        real_clear_screen(term)

    monkeypatch.setattr(
        clear_tx_module, "clear_screen_move_to_bottom", interrupting_clear_screen
    )
    answers("", "a")

    with pytest.raises(KeyboardInterrupt):
        clear_tx(ledger, term)

    # Whatever was cleared before the interrupt is saved, in order
    cleared = [h for h in headers(ledger)[1:] if " * " in h]
    expected = [
        "2024-01-02 * groceries",
        "2024-01-03 * pending rent",
        "01-04 * no year",
    ]
    assert cleared == expected[:saved]


@requires_hledger
def test_invalid_journal_returns_to_menu(tmp_path: Path, term, answers) -> None:
    ledger = tmp_path / "my.ledger"
    unbalanced = "2024-01-01 a\n    x  1 USD\n    y  1 USD\n"
    ledger.write_text(unbalanced)
    answers("", "a")

    assert clear_tx(ledger, term) == STATUS.WAIT
    assert ledger.read_text() == unbalanced


@requires_hledger
def test_relative_include_resolves_from_any_directory(
    tmp_path: Path, term, answers, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "accounts.journal").write_text("account assets:bank\n")
    ledger = tmp_path / "my.ledger"
    ledger.write_text(
        "include sub/accounts.journal\n\n"
        "2024-01-01 a\n    expenses:x  1 USD\n    assets:bank\n"
    )
    monkeypatch.chdir("/")
    answers("", "a")

    clear_tx(ledger, term)

    assert "2024-01-01 * a" in ledger.read_text()
