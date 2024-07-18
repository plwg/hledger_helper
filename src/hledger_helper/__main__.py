from pathlib import Path

from blessed import Terminal

from .helpers.backup import backup_file
from .helpers.options import get_selected_option
from .ui.menu import menu


def main():
    term = Terminal()

    while True:
        selection = menu()

        ledger_path = Path("~/finance/my.ledger").expanduser()
        price_path = Path("~/finance/fetched_prices.txt").expanduser()

        helper = get_selected_option(selection)

        if helper[0] == "Fetch Price":
            backup_file(price_path)
            helper[1](price_path)

        else:
            backup_file(ledger_path)
            helper[1](ledger_path)

        with term.cbreak():
            print(term.bold_black_on_green("Press Any Key to Continue."), end="")
            term.inkey()


if __name__ == "__main__":
    main()
