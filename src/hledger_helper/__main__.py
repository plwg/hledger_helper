from pathlib import Path

from blessed import Terminal

from .helpers.backup import backup_file
from .helpers.options import get_selected_option
from .ui.menu import menu


def main():
    term = Terminal()

    ledger_path = Path("~/finance/my.ledger").expanduser()
    price_path = Path("~/finance/fetched_prices.txt").expanduser()
    while True:
        selection = menu()

        helper = get_selected_option(selection)

        if helper.name == "Fetch Price":
            backup_file(price_path)
            helper.function(price_path)

        else:
            backup_file(ledger_path)
            helper.function(ledger_path)

        with term.cbreak():
            print(term.bold_black_on_green("Press Any Key to Continue."), end="")
            term.inkey()


if __name__ == "__main__":
    main()
