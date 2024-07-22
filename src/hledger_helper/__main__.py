from pathlib import Path

import tomllib
from blessed import Terminal

from .helpers.backup import backup_file
from .helpers.options import get_main_menu_options, get_selected_option
from .helpers.status import STATUS
from .ui.menu import menu
from .ui.press_key_to_continue import press_key_to_continue


def main():
    with open(Path(__file__).resolve().parent / "config" / "config.toml", "rb") as f:
        config = tomllib.load(f)

    paths = config["paths"]

    directory = Path(paths["directory"]).expanduser()

    ledger_path = directory / paths["ledger_file"]
    price_path = directory / paths["price_file"]
    header_path = directory / paths["header_file"]
    recurring_tx_path = directory / paths["recurring_tx_file"]

    term = Terminal()

    while True:
        selection = menu(get_main_menu_options())

        helper = get_selected_option(selection)

        if helper.name == "Fetch Price":
            commodity_pairs = config["commodities"]["commodity_pairs"]

            backup_file(price_path)
            status = helper.function(price_path, commodity_pairs)

        elif helper.name == "Clear Transaction":
            backup_file(ledger_path)
            status = helper.function(ledger_path)

        elif helper.name == "Sort Ledger":
            backup_file(ledger_path)
            backup_file(header_path)
            status = helper.function(ledger_path, header_path)

        elif helper.name == "Generate Recurring Transaction":
            backup_file(ledger_path)

            status = helper.function(ledger_path, recurring_tx_path)

        else:
            raise NotImplementedError

        if status == STATUS.WAIT:
            press_key_to_continue(term)

        elif status == STATUS.NOWAIT:
            pass

        else:
            raise ValueError


if __name__ == "__main__":
    main()
