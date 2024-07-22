import subprocess

from blessed import Terminal

from ..ui.press_key_to_continue import press_key_to_continue
from .status import STATUS


def generate_recurring_tx(ledger_path, recurring_tx_path):
    term = Terminal()

    while True:
        print(term.clear + term.home)
        print(term.move_y(term.height))
        period_expression = input(
            term.green("Input a period expression, or q to quit, or ? for help: ")
        )

        if period_expression.lower() in {"q", "quit"}:
            return STATUS.NOWAIT

        elif period_expression == "?":
            print(term.clear + term.home + term.move_y(term.height))
            print(
                """Valid period expressions include: "..", "apr", "april", "aug", "august", "bimonthly", "biweekly", "daily", "dec", "december", "every", "feb", "february", "fortnightly", "from", "in", "jan", "january", "jul", "july", "jun", "june", "last", "mar", "march", "may", "monthly", "next", "nov", "november", "oct", "october", "quarterly", "sep", "september", "this", "to", "today", "tomorrow", "until", "weekly", "yearly", "yesterday", '+', '-', 'Q', 'q', digit, integer, or year."""
            )
            press_key_to_continue(term)

            continue

        else:
            recurring_tx_result = subprocess.run(
                [
                    "hledger",
                    f"--file={str(recurring_tx_path)}",
                    "print",
                    "--forecast",
                    "-p",
                    period_expression,
                ],
                capture_output=True,
                text=True,
            )

            if recurring_tx_result.stderr != "":
                print(recurring_tx_result.stderr)

                press_key_to_continue(term)

                continue

            else:
                recur_tx = recurring_tx_result.stdout

                print(recur_tx)

                decision = input(term.green("Append this to jorunal? (y/N): ")).lower()

                if decision in {"y", "yes"}:
                    with open(ledger_path, "a") as f:
                        f.write(recur_tx)

                elif decision in {"", "n", "no"}:
                    continue

                else:
                    raise ValueError
