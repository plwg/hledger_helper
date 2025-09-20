from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from hhelper.helpers.align_posting import align_amounts
from hhelper.helpers.check_valid_journal import check_valid_journal
from hhelper.helpers.return_status import STATUS

if TYPE_CHECKING:
    from pathlib import Path

    from blessed import Terminal


def clean_up_journal(
    ledger_path: Path, header_path: Path, backup_ledger_path: Path, term: Terminal
) -> STATUS:
    with term.hidden_cursor():
        warning_message = (
            "Relying on hledger print, cleaning up has the following behaviors:",
            "- All amounts are shown explicity. Balance assignments are converted into balance assertions.",
            "- Amounts are renormalized to commodity display style.",
            "- All decimal places are shown.",
            "- Directives and inter-transaction comments are lost.",
            "- Valuation affects posting amounts but not balance assertion or balance assignment amounts",
            "  potentially causing those to fail.",
            "- Auto postings can generate postings with too many missing amounts.",
            "- Account aliases can generate bad account names.",
            "- Amounts across transactions are aligned based on decimal point location.",
            "",
            "The cleaner will check that the resulting ledger is a valid journal before writing back to the file.",
            f"The unmodified journal can be found at {backup_ledger_path}",
        )

        max_len = max(len(m) for m in warning_message)
        warning_message = [m.ljust(max_len) for m in warning_message]

        print(term.home + term.move_y(term.height // 2 - len(warning_message) // 2))

        for msg in warning_message:
            print(term.center(term.bold(msg)))

        print(term.move_y(term.height))

        descision = input(term.green("Continue? (Y/n/q): ")).lower()

        if descision in {"", "y", "yes"}:
            pass

        elif descision in {"n", "no", "q", "quit"}:
            return STATUS.NOWAIT

        else:
            raise ValueError

    print(term.clear + term.move_y(term.height))

    # Generate the ledger content
    sorted_ledger = subprocess.run(
        ["hledger", "print", "-x", "-f", str(ledger_path)],
        capture_output=True,
        text=True,
        check=False,
    ).stdout

    # NOTE: There is no need to account for header here since it is not in the hledger print's output
    sorted_ledger = align_amounts(sorted_ledger)

    # Read the header file
    with header_path.open() as header_file:
        header_content = header_file.read()
    print(term.bold_white(f"Read header file from {header_path}"))

    # Check the result ledger
    sorted_ledger = f"{header_content}\n\n\n{sorted_ledger}"

    check_valid_journal(sorted_ledger)

    # Write the sorted ledger to the file
    with ledger_path.open("w") as ledger_file:
        ledger_file.write(sorted_ledger)

    print(term.bold_white(f"Write sorted ledger to {ledger_path}"))

    return STATUS.WAIT
