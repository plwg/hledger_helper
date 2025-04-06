import datetime
import re
import sys
from collections import OrderedDict
from enum import Enum
from functools import cache

from hhelper.helpers.check_valid_journal import check_valid_journal
from hhelper.helpers.return_status import STATUS
from hhelper.ui.display import clear_screen_move_to_bottom, press_key_to_continue

line_type = Enum(
    "Type",
    ["CLEARED", "UNCLEARED_HEAD", "UNCLEARED_BODY", "GENERATED_COMMENTS"],
)
search_string_type = Enum("Type", ["ALL", "QUIT"])
tx_decision_type = Enum(
    "Type",
    ["YES_CLEAR", "YES_CLEAR_ALL", "DONT_CLEAR", "VIEW_REST", "QUIT", "REGEX", "HELP"],
)


def get_tx_decision(prefix, tx, term):
    while True:
        print(prefix)
        print(tx, end="", flush=True)
        try:
            user_input = input(
                term.green("Clear Transaction (y/n/q/a/v/r/h): ")
            ).lower()

            if user_input in {"", "y", "yes"}:
                return tx_decision_type.YES_CLEAR
            if user_input in {"n", "no"}:
                return tx_decision_type.DONT_CLEAR
            if user_input in {"q", "quit"}:
                return tx_decision_type.QUIT
            if user_input in {"a", "all"}:
                return tx_decision_type.YES_CLEAR_ALL
            if user_input in {"v", "view"}:
                return tx_decision_type.VIEW_REST
            if user_input in {"r", "regex"}:
                return tx_decision_type.REGEX
            if user_input in {"h", "help"}:
                return tx_decision_type.HELP

        except (KeyboardInterrupt, EOFError):
            print("Interrupted")
            print("Bye!")
            sys.exit()


def get_regex_search_string(term):
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
            return search_string_type.QUIT
        if search_string == "":
            return search_string_type.ALL
        return search_string


@cache
def is_transaction_header(text):
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
def is_transaction_header_cleared(text):
    if is_transaction_header(text):
        # Return match
        return (
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

    return False


def update_line_status(lines, start_line):
    line_status = {}
    uncleared_tx = {}
    uncleared_tx_text = {}
    num_unclear = 0

    for line_number, line in lines.items():
        if line_number < start_line:
            pass

        elif is_transaction_header(line) and not is_transaction_header_cleared(line):
            line_status[line_number] = line_type.UNCLEARED_HEAD

            uncleared_tx[line_number] = [line_type.UNCLEARED_HEAD]
            uncleared_tx_text[line_number] = [line]

            current_unclear_head = line_number

            num_unclear += 1

        elif (
            line_number >= start_line + 1
            and line_status[line_number - 1] == line_type.UNCLEARED_HEAD
            and line.strip().startswith("; generated-transaction:")
        ):
            line_status[line_number] = line_type.GENERATED_COMMENTS

            uncleared_tx[current_unclear_head].append(line_type.GENERATED_COMMENTS)
            uncleared_tx_text[current_unclear_head].append(line)

        elif (
            line_number >= start_line + 1
            and line_status[line_number - 1]
            in {line_type.UNCLEARED_HEAD, line_type.UNCLEARED_BODY}
            and re.match(r"\s+\w+", line)
        ) or (
            line_number >= start_line + 2
            and line_status[line_number - 2] == line_type.UNCLEARED_HEAD
            and line_status[line_number - 1] == line_type.GENERATED_COMMENTS
        ):
            line_status[line_number] = line_type.UNCLEARED_BODY

            uncleared_tx[current_unclear_head].append(line_type.UNCLEARED_BODY)
            uncleared_tx_text[current_unclear_head].append(line)
        else:
            line_status[line_number] = line_type.CLEARED

    uncleared_tx_text = {k: "".join(v) for k, v in uncleared_tx_text.items()}

    return uncleared_tx, uncleared_tx_text, num_unclear


def print_help_string():
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


def clear_tx(ledger_path, term):
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

        lines = OrderedDict(
            [(index, line) for index, line in enumerate(lines, start=1)]
        )

        clear_screen_move_to_bottom(term)
        uncleared_tx, uncleared_tx_text, uncleared_count = update_line_status(
            lines, starting_line
        )

        if uncleared_count == 0:
            print("All cleared. Bye!")
            return STATUS.WAIT

        print(term.yellow(f"{uncleared_count} uncleared transaction left."))

        while True:
            search_string = get_regex_search_string(term)
            clear_screen_move_to_bottom(term)

            if search_string == search_string_type.QUIT:
                return STATUS.NOWAIT
            if search_string == search_string_type.ALL:
                break
            elif search_string != search_string_type.ALL:
                uncleared_tx_text = {
                    k: v
                    for k, v in uncleared_tx_text.items()
                    if re.search(search_string, v, flags=re.IGNORECASE)
                }

                uncleared_tx = {
                    k: v for k, v in uncleared_tx.items() if k in uncleared_tx_text
                }

                break

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
                decision = tx_decision_type.YES_CLEAR_ALL
            else:
                decision = get_tx_decision(f"[{index}/{total_num}]", v, term)

            if decision == tx_decision_type.HELP:
                clear_screen_move_to_bottom(term)
                print_help_string()
                press_key_to_continue(term)
                clear_screen_move_to_bottom(term)

                index -= 1
                continue

            if decision == tx_decision_type.REGEX:
                clear_screen_move_to_bottom(term)
                break

            if decision == tx_decision_type.QUIT:
                return STATUS.NOWAIT

            if decision == tx_decision_type.DONT_CLEAR:
                clear_screen_move_to_bottom(term)

            elif decision == tx_decision_type.VIEW_REST:
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
                tx_decision_type.YES_CLEAR,
                tx_decision_type.YES_CLEAR_ALL,
            }:
                if decision == tx_decision_type.YES_CLEAR_ALL:
                    clear_all_flag = True

                lines[k] = unclear_query_pattern.sub(r"\2* ", lines[k])

                if uncleared_tx[k][1] == line_type.GENERATED_COMMENTS:
                    lines.pop(k + 1)

                with ledger_path.open("w") as f:
                    for line in lines.values():
                        f.write(line)
                clear_screen_move_to_bottom(term)
            else:
                raise NotImplementedError
