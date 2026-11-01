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


def hledger(path: Path, *args: str) -> str:
    return subprocess.run(
        ["hledger", *args, "-f", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


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
def test_sorts_and_includes_the_header(files, term, answers) -> None:
    ledger, header = files
    before = hledger_print(ledger)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT

    text = ledger.read_text()
    # The header's directives are read from the header file, not copied
    assert text.startswith(f"include {header}\n")
    assert "account assets:bank" not in text
    assert text.index("earlier") < text.index("later")
    assert hledger_print(ledger) == before
    assert "assets:bank" in hledger(ledger, "accounts", "--declared")


@requires_hledger
def test_header_changes_are_seen_without_another_clean_up(files, term, answers) -> None:
    ledger, header = files
    answers("y")
    clean_up_journal(ledger, header, ledger, term)

    header.write_text(header.read_text() + "account expenses:new\n")

    assert "expenses:new" in hledger(ledger, "accounts", "--declared")


@requires_hledger
def test_ledger_still_finds_the_header_after_moving(
    tmp_path: Path, files, term, answers
) -> None:
    # The include does not depend on where the ledger is
    ledger, header = files
    answers("y")
    clean_up_journal(ledger, header, ledger, term)
    (tmp_path / "elsewhere").mkdir()
    moved = ledger.rename(tmp_path / "elsewhere" / "my.ledger")

    assert "assets:bank" in hledger(moved, "accounts", "--declared")


@requires_hledger
def test_running_twice_changes_nothing_more(files, term, answers) -> None:
    ledger, header = files
    answers("y")
    clean_up_journal(ledger, header, ledger, term)
    once = ledger.read_text()
    answers("y")
    clean_up_journal(ledger, header, ledger, term)

    assert ledger.read_text() == once


@requires_hledger
def test_header_in_another_directory_is_included_by_absolute_path(
    tmp_path: Path, files, term, answers
) -> None:
    ledger, _ = files
    (tmp_path / "config").mkdir()
    header = tmp_path / "config" / "header.journal"
    header.write_text("account assets:bank\n")
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT
    assert ledger.read_text().startswith(f"include {header}\n")
    assert header.is_absolute()


@requires_hledger
@pytest.mark.parametrize(
    "directive",
    [
        "alias food = expenses:food",
        "apply account personal",
        "Y 2024",
        "D 1,000.00 USD",
    ],
)
def test_header_with_file_scoped_directives_is_copied(
    files, term, answers, capsys: pytest.CaptureFixture, directive: str
) -> None:
    # hledger applies these only within their own file, so they would not
    # reach the ledger's transactions from an included header
    ledger, header = files
    header_text = f"account assets:bank\n{directive}\n"
    header.write_text(header_text)
    ledger.write_text(header_text + "\n" + TRANSACTIONS)
    before = hledger_print(ledger)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT
    assert ledger.read_text().startswith(header_text)
    assert "include" not in ledger.read_text()
    assert hledger_print(ledger) == before
    assert "hledger only applies" in capsys.readouterr().out


DEFAULT_COMMODITY_JOURNAL = """\
D 1.000,00 EUR  ; default currency
account assets:bank

2024-01-02 later
    expenses:food  12,5
    assets:bank

2024-01-01 earlier
    expenses:rent  1.000
    assets:bank
"""


@requires_hledger
def test_default_commodity_line_is_kept_as_written(files, term, answers) -> None:
    ledger, header = files
    ledger.write_text(DEFAULT_COMMODITY_JOURNAL)
    before = hledger_print(ledger)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT

    assert ledger.read_text().startswith(
        f"D 1.000,00 EUR  ; default currency\ninclude {header}\n"
    )
    assert hledger_print(ledger) == before

    once = ledger.read_text()
    answers("y")
    clean_up_journal(ledger, header, ledger, term)
    assert ledger.read_text() == once


@requires_hledger
def test_default_commodity_in_a_copied_header_is_not_repeated(
    files, term, answers
) -> None:
    ledger, header = files
    header.write_text("D 1.000,00 EUR\naccount assets:bank\n")
    ledger.write_text(
        "D 1.000,00 EUR\naccount assets:bank\n\n"
        + DEFAULT_COMMODITY_JOURNAL.split("\n\n", 1)[1]
    )
    answers("y")

    clean_up_journal(ledger, header, ledger, term)

    assert ledger.read_text().count("D 1.000,00 EUR") == 1


@requires_hledger
def test_default_commodity_lines_between_transactions_are_kept_in_order(
    files, term, answers
) -> None:
    # Cleaned amounts carry their commodity, so moving the D lines to the top
    # changes nothing for them; a new amount at the end still gets the last D
    ledger, header = files
    original = (
        "D 1.000,00 EUR\n\n"
        "2024-01-01 a\n    expenses:food  5\n    assets:bank\n\n"
        "D 1,000.00 USD\n\n"
        "2024-01-02 b\n    expenses:food  7\n    assets:bank\n"
    )
    ledger.write_text(original)
    before = hledger_print(ledger)
    answers("y")

    assert clean_up_journal(ledger, header, ledger, term) == STATUS.WAIT
    assert ledger.read_text().startswith("D 1.000,00 EUR\nD 1,000.00 USD\n")
    assert hledger_print(ledger) == before

    new_entry = "\n2024-01-03 c\n    expenses:food  9\n    assets:bank\n"
    ledger.write_text(ledger.read_text() + new_entry)
    assert "9.00 USD" in hledger(ledger, "print", "date:2024-01-03")


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
