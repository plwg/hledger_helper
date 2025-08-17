from __future__ import annotations

import datetime
import re
import sys
from collections import OrderedDict
from enum import Enum, auto
from functools import cache
from typing import TYPE_CHECKING

from hhelper.helpers.check_valid_journal import check_valid_journal
from hhelper.helpers.return_status import STATUS
from hhelper.ui.display import clear_screen_move_to_bottom, press_key_to_continue

if TYPE_CHECKING:
    from pathlib import Path

    from blessed import Terminal


class LineType(Enum):
    CLEARED = auto()
    UNCLEARED_HEAD = auto()
    UNCLEARED_BODY = auto()
    GENERATED_COMMENTS = auto()


class SearchStringType(Enum):
    ALL = auto()
    QUIT = auto()


class TxDecisionType(Enum):
    YES_CLEAR = auto()
    YES_CLEAR_ALL = auto()
    DONT_CLEAR = auto()
    VIEW_REST = auto()
    QUIT = auto()
    REGEX = auto()
    HELP = auto()


def get_tx_decision(prefix: str, tx: str, term: Terminal) -> TxDecisionType:
    while True:
        print(prefix)
        print(tx, end="", flush=True)
        try:
            user_input = input(
                term.green("Clear Transaction (y/n/q/a/v/r/h): ")
            ).lower()

            if user_input in {"", "y", "yes"}:
                return TxDecisionType.YES_CLEAR
            if user_input in {"n", "no"}:
                return TxDecisionType.DONT_CLEAR
            if user_input in {"q", "quit"}:
                return TxDecisionType.QUIT
            if user_input in {"a", "all"}:
                return TxDecisionType.YES_CLEAR_ALL
            if user_input in {"v", "view"}:
                return TxDecisionType.VIEW_REST
            if user_input in {"r", "regex"}:
                return TxDecisionType.REGEX
            if user_input in {"h", "help"}:
                return TxDecisionType.HELP

        except (KeyboardInterrupt, EOFError):
            print("Interrupted")
            print("Bye!")
            sys.exit()


def get_regex_search_string(term: Terminal) -> str | SearchStringType:
    try:
        search_string = input(
            term.green(
                'Regex query for transaction (leave blank for no filter, "q" or "quit" for menu): '
            )
        )
    except (KeyboardInterrupt, EOFError):
        print("Interrupted")
        print("Bye!")
        sys.exit()
    else:
        if search_string.lower() in {"q", "quit"}:
            return SearchStringType.QUIT
        if search_string == "":
            return SearchStringType.ALL
        return search_string


@cache
def is_transaction_header(text: str) -> bool:
    match = (
        re.match(r"((?P<year>\d{4})-)?(?P<month>\d{1,2})-(?P<day>\d{1,2}) .*", text)
        or re.match(
            r"((?P<year>\d{4})\.)?(?P<month>\d{1,2})\.(?P<day>\d{1,2}) .*", text
        )
        or re.match(r"((?P<year>\d{4})/)?(?P<month>\d{1,2})/(?P<day>\d{1,2}) .*", text)
    )

    if match:
        try:
            month = int(match.group("month"))
            day = int(match.group("day"))

            if match.group("year"):
                year = int(match.group("year"))
                datetime.date(year=year, month=month, day=day)
            else:
                # If year is not provided, just validate month and day
                datetime.date(
                    year=2000, month=month, day=day
                )  # Use a leap year to allow Feb 29
        except (ValueError, TypeError):
            return False
        else:
            return True
    else:
        return False


@cache
def is_transaction_header_cleared(text: str) -> bool:
    if is_transaction_header(text):
        # Return match
        match = (
            re.match(
                r"((?P<year>\d{4})-)?(?P<month>\d{1,2})-(?P<day>\d{1,2}) \* ", text
            )
            or re.match(
                r"((?P<year>\d{4})\.)?(?P<month>\d{1,2})\.(?P<day>\d{1,2}) \* ", text
            )
            or re.match(
                r"((?P<year>\d{4})/)?(?P<month>\d{1,2})/(?P<day>\d{1,2}) \* ", text
            )
        )

        return match is not None

    return False


def update_line_status(
    lines: dict[int, str], start_line: int
) -> tuple[dict[int, list[LineType]], dict[int, str], int]:
    line_status = {}
    uncleared_tx = {}
    uncleared_tx_text = {}
    num_unclear = 0

    current_unclear_head = 0

    for line_number, line in lines.items():
        if line_number < start_line:
            pass

        elif is_transaction_header(line) and not is_transaction_header_cleared(line):
            line_status[line_number] = LineType.UNCLEARED_HEAD

            uncleared_tx[line_number] = [LineType.UNCLEARED_HEAD]
            uncleared_tx_text[line_number] = [line]

            current_unclear_head = line_number

            num_unclear += 1

        elif (
            line_number >= start_line + 1
            and line_status[line_number - 1] == LineType.UNCLEARED_HEAD
            and line.strip().startswith("; generated-transaction:")
        ):
            line_status[line_number] = LineType.GENERATED_COMMENTS

            uncleared_tx[current_unclear_head].append(LineType.GENERATED_COMMENTS)
            uncleared_tx_text[current_unclear_head].append(line)

        elif (
            line_number >= start_line + 1
            and line_status[line_number - 1]
            in {LineType.UNCLEARED_HEAD, LineType.UNCLEARED_BODY}
            and re.match(r"\s+\w+", line)
        ) or (
            line_number >= start_line + 2
            and line_status[line_number - 2] == LineType.UNCLEARED_HEAD
            and line_status[line_number - 1] == LineType.GENERATED_COMMENTS
        ):
            line_status[line_number] = LineType.UNCLEARED_BODY

            uncleared_tx[current_unclear_head].append(LineType.UNCLEARED_BODY)
            uncleared_tx_text[current_unclear_head].append(line)
        else:
            line_status[line_number] = LineType.CLEARED

    uncleared_tx_text = {k: "".join(v) for k, v in uncleared_tx_text.items()}

    return uncleared_tx, uncleared_tx_text, num_unclear


def print_help_string() -> None:
    print(
        "y/yes: clear current transaction",
        "n/no: don't clear current transaction",
        "q/quit: quit to main menu",
        "a/all: clear all the remaining transaction in current query",
        "v/view: view remaining transaction in current query",
        "r/regex: enter new regex query",
        "h/help: print this help",
        "",
        "If any, modifications will be written out to file upon each selection.",
        sep="\n",
    )


def clear_tx(ledger_path: Path, term: Terminal) -> STATUS:
    unclear_query_pattern = "|".join(
        [
            r"((\d{4}-)?\d{1,2}-\d{1,2} )(! )?",
            r"((\d{4}/)?\d{1,2}/\d{1,2} )(! )?",
            r"((\d{4}\.)?\d{1,2}\.\d{1,2} )(! )?",
        ]
    )

    unclear_query_pattern = re.compile(f"^({unclear_query_pattern})")
    starting_line = 1

    while True:
        with ledger_path.open() as f:
            lines = f.readlines()

        check_valid_journal("".join(lines))

        line_dict = OrderedDict(
            [(index, line) for index, line in enumerate(lines, start=1)]
        )

        clear_screen_move_to_bottom(term)
        uncleared_tx, uncleared_tx_text, uncleared_count = update_line_status(
            line_dict, starting_line
        )

        if uncleared_count == 0:
            print("All cleared. Bye!")
            return STATUS.WAIT

        print(term.yellow(f"{uncleared_count} uncleared transaction left."))

        search_string = get_regex_search_string(term)
        clear_screen_move_to_bottom(term)

        if search_string == SearchStringType.QUIT:
            return STATUS.NOWAIT
        if search_string == SearchStringType.ALL:
            pass
        elif isinstance(search_string, str):
            uncleared_tx_text = {
                k: v
                for k, v in uncleared_tx_text.items()
                if re.search(search_string, v, flags=re.IGNORECASE)
            }

            uncleared_tx = {
                k: v for k, v in uncleared_tx.items() if k in uncleared_tx_text
            }
        else:
            raise ValueError

        keys = list(uncleared_tx_text.keys())
        total_num = len(keys)
        max_index = total_num - 1

        index = 0
        clear_all_flag = False
        while index <= max_index:
            k = keys[index]
            v = uncleared_tx_text[k]

            index += 1

            if clear_all_flag:
                decision = TxDecisionType.YES_CLEAR_ALL
            else:
                decision = get_tx_decision(f"[{index}/{total_num}]", v, term)

            if decision == TxDecisionType.HELP:
                clear_screen_move_to_bottom(term)
                print_help_string()
                press_key_to_continue(term)
                clear_screen_move_to_bottom(term)

                index -= 1
                continue

            if decision == TxDecisionType.REGEX:
                clear_screen_move_to_bottom(term)
                break

            if decision == TxDecisionType.QUIT:
                return STATUS.NOWAIT

            if decision == TxDecisionType.DONT_CLEAR:
                clear_screen_move_to_bottom(term)

            elif decision == TxDecisionType.VIEW_REST:
                remaining_items = [
                    value for key, value in uncleared_tx_text.items() if key >= k
                ]

                num_remaining = len(remaining_items)

                clear_screen_move_to_bottom(term)
                for i, item in enumerate(remaining_items, start=1):
                    print(f"[{i}/{num_remaining}]")
                    print(item)

                for _ in range(2):
                    print("*" * term.width)

                print()

                index -= 1

            elif decision in {
                TxDecisionType.YES_CLEAR,
                TxDecisionType.YES_CLEAR_ALL,
            }:
                if decision == TxDecisionType.YES_CLEAR_ALL:
                    clear_all_flag = True

                line_dict[k] = unclear_query_pattern.sub(r"\2* ", line_dict[k])

                if uncleared_tx[k][1] == LineType.GENERATED_COMMENTS:
                    line_dict.pop(k + 1)

                with ledger_path.open("w") as f:
                    for line in line_dict.values():
                        f.write(line)
                clear_screen_move_to_bottom(term)
            else:
                raise NotImplementedError
