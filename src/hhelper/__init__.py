import argparse
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

from blessed import Terminal

from hhelper.helpers.backup import backup_file
from hhelper.helpers.options import (
    AvailableHelpers,
    get_main_menu_options,
    get_selected_option,
)
from hhelper.helpers.return_status import STATUS
from hhelper.helpers.similar_report import HledgerError, similar_report
from hhelper.ui.display import move_y, press_key_to_continue
from hhelper.ui.menu import menu


def report_missing(term: Terminal, *paths: Path) -> bool:
    # Returns whether any file is missing, after naming each one
    missing = [path for path in paths if not path.is_file()]

    for path in missing:
        print(term.bold_red(f"File not found: {path}"))

    if missing:
        print("Create it, or check the paths in ~/.config/hhelper/config.toml.")

    return bool(missing)


def print_similar_report(ledger_path: Path) -> None:
    if not ledger_path.is_file():
        sys.exit(f"File not found: {ledger_path}")

    try:
        print(similar_report(ledger_path))
    except HledgerError as error:
        print(error, file=sys.stderr)
        sys.exit(f"hledger cannot read {ledger_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hh", description="Helper functions for hledger plain text accounting."
    )
    parser.add_argument(
        "--similar",
        action="store_true",
        help="list descriptions and accounts that look like variants of each"
        " other, then exit; nothing is changed",
    )
    args = parser.parse_args(argv)

    config_path = Path().home() / ".config" / "hhelper" / "config.toml"

    try:
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)

    except FileNotFoundError:
        msg = (
            f"The config file is not found. Please create a config file at {config_path}.\n"
            f"You can find an example config file at https://github.com/plwg/hledger_helper"
        )
        print(msg)

        return

    paths = config["paths"]

    directory = Path(paths["directory"]).expanduser()

    ledger_path = directory / paths["ledger_file"]
    price_path = directory / paths["price_file"]
    # Optional here; Clean Up Journal explains what to do when it is missing
    header_path = directory / paths["header_file"] if "header_file" in paths else None
    recurring_tx_path = directory / paths["recurring_tx_file"]

    if args.similar:
        print_similar_report(ledger_path)
        return

    term = Terminal()

    while True:
        selection = menu(get_main_menu_options(), term)

        name, helper = get_selected_option(selection, term)

        helper = cast("Callable", helper)

        print(term.clear + term.home)
        print(move_y(term, term.height))

        if name == AvailableHelpers.FETCH_PRICE:
            commodity_pairs = config["commodities"]["commodity_pairs"]

            # A missing price file is created; only its directory must exist
            if not price_path.parent.is_dir():
                print(term.bold_red(f"Directory not found: {price_path.parent}"))
                status = STATUS.WAIT
            else:
                if price_path.is_file():
                    backup_file(price_path)
                status = helper(price_path, commodity_pairs, term)

        elif name == AvailableHelpers.MARK_CLEAR:
            if report_missing(term, ledger_path):
                status = STATUS.WAIT
            else:
                backup_file(ledger_path)
                status = helper(ledger_path, term)

        elif name == AvailableHelpers.CLEAN_UP:
            if report_missing(term, ledger_path):
                status = STATUS.WAIT
            else:
                back_up_path = backup_file(ledger_path)
                if header_path is not None and header_path.is_file():
                    backup_file(header_path)
                status = helper(ledger_path, header_path, back_up_path, term)

        elif name == AvailableHelpers.GEN_RECUR:
            if report_missing(term, ledger_path, recurring_tx_path):
                status = STATUS.WAIT
            else:
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
