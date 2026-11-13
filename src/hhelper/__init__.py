import argparse
import datetime
import os
import re
import sys
import tomllib
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import cast

from blessed import Terminal

from hhelper.helpers.backup import backup_file
from hhelper.helpers.clean_up_journal import clean_up_journal
from hhelper.helpers.clear_tx import clear_tx_until
from hhelper.helpers.fetch_price import CommodityPairConfig, fetch_price
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


def run_fetch_prices(
    price_path: Path,
    commodity_pairs: list[CommodityPairConfig],
    term: Terminal,
    *,
    confirm: bool = True,
) -> STATUS:
    # A missing price file is created; only its directory must exist
    if not price_path.parent.is_dir():
        print(term.bold_red(f"Directory not found: {price_path.parent}"))
        return STATUS.FAILED

    if price_path.is_file():
        backup_file(price_path)
    return fetch_price(price_path, commodity_pairs, term, confirm=confirm)


def run_clean_up(
    ledger_path: Path,
    header_path: Path | None,
    header_include: str | None,
    term: Terminal,
    *,
    confirm: bool = True,
) -> STATUS:
    if report_missing(term, ledger_path):
        return STATUS.FAILED

    back_up_path = Path(backup_file(ledger_path))
    if header_path is not None and header_path.is_file():
        backup_file(header_path)
    return clean_up_journal(
        ledger_path,
        header_path,
        back_up_path,
        term,
        header_include,
        confirm=confirm,
    )


def run_clear(
    ledger_path: Path, account: str, until: datetime.date, term: Terminal
) -> STATUS:
    if report_missing(term, ledger_path):
        return STATUS.FAILED

    backup_file(ledger_path)
    return clear_tx_until(ledger_path, account, until, term)


def parse_date(text: str) -> datetime.date:
    # Only YYYY-MM-DD; fromisoformat alone also accepts e.g. 20240131
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        msg = f"expected a date as YYYY-MM-DD, got {text!r}"
        raise ValueError(msg)
    return datetime.date.fromisoformat(text)


def exit_with(status: STATUS) -> None:
    # For the command-line actions: a failure exits non-zero
    if status == STATUS.FAILED:
        sys.exit(1)


def print_similar_report(ledger_path: Path) -> None:
    if not ledger_path.is_file():
        sys.exit(f"File not found: {ledger_path}")

    try:
        print(similar_report(ledger_path))
    except HledgerError as error:
        print(error, file=sys.stderr)
        sys.exit(f"hledger cannot read {ledger_path}")


def installed_version() -> str:
    # The installed package's version, which may differ from the source tree
    try:
        return version("hhelper")
    except PackageNotFoundError:
        return "unknown (not installed)"


def print_config(config_path: Path) -> None:
    # The location, then the file as written; works even if it does not parse
    print(f"Config file: {config_path}")

    if not config_path.is_file():
        sys.exit(
            "It does not exist yet. You can find an example config file at"
            " https://github.com/plwg/hledger_helper"
        )

    print()
    print(config_path.read_text(), end="")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hh",
        description="Helper functions for hledger plain text accounting."
        " Run without options for the TUI; run with an option for the CLI.",
    )
    parser.add_argument(
        "--version", action="version", version=f"hh {installed_version()}"
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--config",
        action="store_true",
        help="print the config file's location and content, then exit",
    )
    actions.add_argument(
        "--similar",
        action="store_true",
        help="list descriptions and accounts that look like variants of each"
        " other, then exit; nothing is changed",
    )
    actions.add_argument(
        "--clean-up",
        action="store_true",
        help="clean up the journal without asking, then exit",
    )
    actions.add_argument(
        "--fetch-prices",
        action="store_true",
        help="fetch prices and write them to the price file without asking, then exit",
    )
    actions.add_argument(
        "--clear",
        nargs=2,
        metavar=("ACCOUNT", "DATE"),
        help="clear, without asking, every uncleared transaction dated up to DATE"
        " (YYYY-MM-DD, inclusive) with a posting to exactly ACCOUNT, print them,"
        " then exit",
    )
    args = parser.parse_args(argv)

    if args.clear:
        try:
            clear_until = parse_date(args.clear[1])
        except ValueError as error:
            parser.error(f"--clear: {error}")

    config_path = Path().home() / ".config" / "hhelper" / "config.toml"

    if args.config:
        print_config(config_path)
        return

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
    # As written in the config, unexpanded, for the ledger's include line
    header_include = (
        os.path.join(paths["directory"], paths["header_file"])
        if "header_file" in paths
        else None
    )
    recurring_tx_path = directory / paths["recurring_tx_file"]

    if args.similar:
        print_similar_report(ledger_path)
        return

    term = Terminal()

    if args.clean_up:
        exit_with(
            run_clean_up(ledger_path, header_path, header_include, term, confirm=False)
        )
        return

    if args.clear:
        exit_with(run_clear(ledger_path, args.clear[0], clear_until, term))
        return

    if args.fetch_prices:
        exit_with(
            run_fetch_prices(
                price_path,
                config["commodities"]["commodity_pairs"],
                term,
                confirm=False,
            )
        )
        return

    while True:
        selection = menu(get_main_menu_options(), term)

        name, helper = get_selected_option(selection, term)

        helper = cast("Callable", helper)

        print(term.clear + term.home)
        print(move_y(term, term.height))

        if name == AvailableHelpers.FETCH_PRICE:
            status = run_fetch_prices(
                price_path, config["commodities"]["commodity_pairs"], term
            )

        elif name == AvailableHelpers.MARK_CLEAR:
            if report_missing(term, ledger_path):
                status = STATUS.WAIT
            else:
                backup_file(ledger_path)
                status = helper(ledger_path, term)

        elif name == AvailableHelpers.CLEAN_UP:
            status = run_clean_up(ledger_path, header_path, header_include, term)

        elif name == AvailableHelpers.GEN_RECUR:
            if report_missing(term, ledger_path, recurring_tx_path):
                status = STATUS.WAIT
            else:
                backup_file(ledger_path)
                status = helper(ledger_path, recurring_tx_path, term)

        else:
            raise NotImplementedError

        if status in (STATUS.WAIT, STATUS.FAILED):
            press_key_to_continue(term)

        elif status == STATUS.NOWAIT:
            pass

        else:
            raise ValueError


if __name__ == "__main__":
    main()
