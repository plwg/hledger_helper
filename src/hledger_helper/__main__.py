from pathlib import Path

from blessed import Terminal

from .helpers.backup import backup_file
from .helpers.options import get_selected_option
from .helpers.status import STATUS
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
            status = helper.function(price_path)

        else:
            backup_file(ledger_path)
            status = helper.function(ledger_path)

        if status == STATUS.WAIT:
            with term.cbreak(), term.hidden_cursor():
                print(term.bold_white_on_green("Press Any Key to Continue."))
                term.inkey()

        elif status == STATUS.NOWAIT:
            pass

        else:
            raise ValueError


if __name__ == "__main__":
    main()
