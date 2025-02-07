from pathlib import Path

import tomllib
from blessed import Terminal
from hh.helpers.backup import backup_file
from hh.helpers.options import (
    AvailableHelpers,
    get_main_menu_options,
    get_selected_option,
)
from hh.helpers.return_status import STATUS
from hh.ui.display import press_key_to_continue
from hh.ui.menu import menu


def main():
    config_path = Path().home() / ".config" / "hh" / "configx.toml"

    if config_path.is_file():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

    else:
        raise FileNotFoundError(
            (
                f"The config file is not found. Please create a config file at {config_path}.\n"
                f"You can find an example config file at https://github.com/plwg/hledger_helper"
            )
        )

    paths = config["paths"]

    directory = Path(paths["directory"]).expanduser()

    ledger_path = directory / paths["ledger_file"]
    price_path = directory / paths["price_file"]
    header_path = directory / paths["header_file"]
    recurring_tx_path = directory / paths["recurring_tx_file"]

    term = Terminal()

    while True:
        selection = menu(get_main_menu_options(), term)

        name, helper = get_selected_option(selection, term)

        print(term.clear + term.home)
        print(term.move_y(term.height))

        if name == AvailableHelpers.FETCH_PRICE:
            commodity_pairs = config["commodities"]["commodity_pairs"]

            backup_file(price_path)
            status = helper(price_path, commodity_pairs, term)

        elif name == AvailableHelpers.MARK_CLEAR:
            backup_file(ledger_path)
            status = helper(ledger_path, term)

        elif name == AvailableHelpers.CLEAN_UP:
            bak_up_path = backup_file(ledger_path)
            backup_file(header_path)
            status = helper(ledger_path, header_path, bak_up_path, term)

        elif name == AvailableHelpers.GEN_RECUR:
            backup_file(ledger_path)

            status = helper(ledger_path, recurring_tx_path, term)

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
