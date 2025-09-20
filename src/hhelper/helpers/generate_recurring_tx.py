from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from hhelper.helpers.return_status import STATUS
from hhelper.ui.display import press_key_to_continue

if TYPE_CHECKING:
    from pathlib import Path

    from blessed import Terminal


def generate_recurring_tx(
    ledger_path: Path, recurring_tx_path: Path, term: Terminal
) -> STATUS:
    while True:
        print(term.clear + term.home)
        print(term.move_y(term.height))
        period_expression = input(
            term.green("Input a period expression, or q to quit, or ? for help: ")
        )

        if period_expression.lower() in {"q", "quit"}:
            return STATUS.NOWAIT

        if period_expression == "?":
            print(term.clear + term.home + term.move_y(term.height))
            print(
                """Valid period expressions include: "..", "apr", "april", "aug", "august", "bimonthly", "biweekly", "daily", "dec", "december", "every", "feb", "february", "fortnightly", "from", "in", "jan", "january", "jul", "july", "jun", "june", "last", "mar", "march", "may", "monthly", "next", "nov", "november", "oct", "october", "quarterly", "sep", "september", "this", "to", "today", "tomorrow", "until", "weekly", "yearly", "yesterday", '+', '-', 'Q', 'q', digit, integer, or year."""
            )
            press_key_to_continue(term)

            continue

        recurring_tx_result = subprocess.run(
            [
                "hledger",
                f"--file={recurring_tx_path!s}",
                "print",
                "--forecast",
                "-p",
                period_expression,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if recurring_tx_result.stderr != "":
            print(recurring_tx_result.stderr)

            press_key_to_continue(term)

            continue

        recur_tx = recurring_tx_result.stdout
        print(term.clear + term.home)
        print(term.move_y(term.height))

        print(recur_tx)

        decision = input(term.green("Append this to jorunal? (y/N/q): ")).lower()

        if decision in {"y", "yes"}:
            with ledger_path.open("a") as f:
                f.write(recur_tx)

        elif decision in {"", "n", "no", "q", "quit"}:
            continue

        else:
            raise ValueError
