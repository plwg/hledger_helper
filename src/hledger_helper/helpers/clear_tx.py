# TODO: add check to guard against corruption
import re
from collections import OrderedDict
from enum import Enum

from blessed import Terminal

from .check_valid_journal import check_valid_journal
from .status import STATUS

line_type = Enum(
    "Type",
    ["CLEARED", "UNCLEARED_HEAD", "UNCLEARED_BODY", "GENERATED_COMMENTS"],
)
search_string_type = Enum("Type", ["ALL", "QUIT"])
tx_decision_type = Enum("Type", ["YES_CLEAR", "YES_CLEAR_ALL", "DONT_CLEAR", "QUIT"])

term = Terminal()


def get_tx_decision():
    try:
        user_input = input(term.green("Clear Transaction (y/n/q/a): ")).lower()

        print(term.clear + term.home)

        if user_input in {"q", "quit"}:
            return tx_decision_type.QUIT
        elif user_input in {"", "y", "yes"}:
            return tx_decision_type.YES_CLEAR
        elif user_input in {"n", "no"}:
            return tx_decision_type.DONT_CLEAR
        elif user_input in {"a", "all"}:
            return tx_decision_type.YES_CLEAR_ALL

    except (KeyboardInterrupt, EOFError):
        print("Interrupted")
        print("Bye!")
        exit()


def get_regex_search_string():
    try:
        search_string = input(
            term.green(
                'Regex for filtering transaction (leave blank for no filter, "q" or "quit" to menu): '
            )
        )

        if search_string.lower() in {"q", "quit"}:
            return search_string_type.QUIT
        elif search_string == "":
            return search_string_type.ALL
        else:
            return search_string
    except (KeyboardInterrupt, EOFError):
        print("Interrupted")
        print("Bye!")
        exit()


def update_line_status(lines):
    line_status = {}
    uncleared_tx = {}
    uncleared_tx_text = {}
    num_unclear = 0

    for line_number, line in lines.items():
        if re.match(r"\d{4}-\d{2}-\d{2}", line) and not re.match(
            r"\d{4}-\d{2}-\d{2} \* ", line
        ):
            line_status[line_number] = line_type.UNCLEARED_HEAD

            uncleared_tx[line_number] = [line_type.UNCLEARED_HEAD]
            uncleared_tx_text[line_number] = [line]

            current_unclear_head = line_number

            num_unclear += 1

        elif (
            line_number >= 2
            and line_status[line_number - 1] == line_type.UNCLEARED_HEAD
            and line.strip().startswith("; generated-transaction:")
        ):
            line_status[line_number] = line_type.GENERATED_COMMENTS

            uncleared_tx[current_unclear_head].append(line_type.GENERATED_COMMENTS)
            uncleared_tx_text[current_unclear_head].append(line)

        elif (
            line_number >= 2
            and line_status[line_number - 1]
            in {line_type.UNCLEARED_HEAD, line_type.UNCLEARED_BODY}
            and line.startswith("    ")
        ):
            line_status[line_number] = line_type.UNCLEARED_BODY

            uncleared_tx[current_unclear_head].append(line_type.UNCLEARED_BODY)
            uncleared_tx_text[current_unclear_head].append(line)

        elif (
            line_number >= 3
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


def clear_tx(ledger_path):
    print(term.move_y(term.height))

    with open(ledger_path, "r") as f:
        lines = f.readlines()

    check_valid_journal("".join(lines))

    lines = OrderedDict([(index, line) for index, line in enumerate(lines, start=1)])

    while True:
        uncleared_tx, uncleared_tx_text, uncleared_count = update_line_status(lines)

        print(term.move_y(term.height))
        if uncleared_count == 0:
            print("All cleared. Bye!")
            return STATUS.WAIT

        else:
            print(term.yellow(f"{uncleared_count} uncleared transaction left."))

        search_string = get_regex_search_string()
        print(term.clear + term.home)

        if search_string == search_string_type.QUIT:
            return STATUS.NOWAIT
        elif search_string != search_string_type.ALL:
            uncleared_tx_text = {
                k: v
                for k, v in uncleared_tx_text.items()
                if re.search(search_string, v, flags=re.I)
            }

            uncleared_tx = {
                k: v for k, v in uncleared_tx.items() if k in uncleared_tx_text
            }
        elif search_string == search_string_type.ALL:
            pass
        else:
            raise ValueError

        clear_all_flag = False

        for k, v in uncleared_tx_text.items():
            print(term.move_y(term.height))

            print(v)

            if clear_all_flag:
                decision = tx_decision_type.YES_CLEAR

            else:
                decision = get_tx_decision()

            if decision == tx_decision_type.QUIT:
                return STATUS.NOWAIT

            elif decision == tx_decision_type.DONT_CLEAR:
                pass

            elif decision in {
                tx_decision_type.YES_CLEAR,
                tx_decision_type.YES_CLEAR_ALL,
            }:
                lines[k] = re.sub(r"^(\d{4}-\d{2}-\d{2}) ", r"\1 * ", lines[k])

                if uncleared_tx[k][1] == line_type.GENERATED_COMMENTS:
                    del lines[k + 1]

                with open(ledger_path, "w") as f:
                    for line in lines.values():
                        f.write(line)

                if decision == tx_decision_type.YES_CLEAR_ALL:
                    clear_all_flag = True

            else:
                raise NotImplementedError

        lines = OrderedDict(
            [(index, lines[k]) for index, k in enumerate(lines.keys(), start=1)]
        )
