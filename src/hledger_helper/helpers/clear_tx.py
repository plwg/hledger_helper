# TODO: add check to guard against corruption
# TODO: add option to clear all
import re
from enum import Enum

from blessed import Terminal

line_type = Enum(
    "Type",
    ["CLEARED", "UNCLEARED_HEAD", "UNCLEARED_BODY", "GENERATED_COMMENTS"],
)
search_string_type = Enum("Type", ["ALL"])
tx_decision_type = Enum("Type", ["YES", "NO"])

term = Terminal()


def get_tx_decision():
    try:
        print(term.move_y(term.height))
        user_input = input(term.green("Clear Transaction (Y/n/q): "))
        print(term.clear + term.home)

        if user_input.lower() in {"quit", "q"}:
            print("Bye!")
            exit()
        elif user_input.lower() in {"", "y", "yes"}:
            return tx_decision_type.YES
        elif user_input.lower() in {"n", "no"}:
            return tx_decision_type.NO

    except (KeyboardInterrupt, EOFError):
        print("Interrupted")
        print("Bye!")
        exit()


def get_regex_search_string():
    try:
        search_string = input(
            term.green("Regex for filtering transaction (leave blank for no filter): ")
        )

        print(term.clear + term.home)

        if search_string.lower() in {"quit", "q"}:
            print("Bye!")
            exit()
        elif search_string == "":
            return search_string_type.ALL
        else:
            return search_string
    except (KeyboardInterrupt, EOFError):
        print("Interrupted")
        print("Bye!")
        exit()


def count_uncleared(line_status):
    return sum([1 for v in line_status.values() if v == line_type.UNCLEARED_HEAD])


def update_line_status(lines):
    line_status = {}

    for line_number in lines.keys():
        line = lines[line_number]

        if re.search(r"^\d\d\d\d-\d\d-\d\d", line) and not re.search(
            r"^\d\d\d\d-\d\d-\d\d \* ", line
        ):
            line_status[line_number] = line_type.UNCLEARED_HEAD

        elif (
            line_number >= 2
            and line_status[line_number - 1] == line_type.UNCLEARED_HEAD
            and line.strip().startswith("; generated-transaction:")
        ):
            line_status[line_number] = line_type.GENERATED_COMMENTS

        elif (
            line_number >= 2
            and line_status[line_number - 1]
            in {line_type.UNCLEARED_HEAD, line_type.UNCLEARED_BODY}
            and line.startswith("    ")
        ):
            line_status[line_number] = line_type.UNCLEARED_BODY

        elif (
            line_number >= 3
            and line_status[line_number - 2] == line_type.UNCLEARED_HEAD
            and line_status[line_number - 1] == line_type.GENERATED_COMMENTS
        ):
            line_status[line_number] = line_type.UNCLEARED_BODY

        else:
            line_status[line_number] = line_type.CLEARED

    return line_status


def clear_tx(ledger_path):
    print(term.home + term.clear + term.move_y(term.height // 2))

    print("=============================================")
    print("Enter regex expression to filter transaction.")
    print("Type 'q', 'quit', CTRL+C, or CTRL+D to quit.")
    print("=============================================")

    with open(ledger_path, "r") as f:
        lines = f.readlines()
        lines = {index: line for index, line in enumerate(lines)}
    while True:
        line_status = update_line_status(lines)

        uncleared_count = count_uncleared(line_status)

        print(term.move_y(term.height))
        if uncleared_count == 0:
            print("All cleared. Bye!")
            break

        else:
            print(term.yellow(f"{uncleared_count} uncleared transaction left."))

        search_string = get_regex_search_string()

        uncleared_transactions = [
            [k] for k, v in line_status.items() if v == line_type.UNCLEARED_HEAD
        ]

        tx_text = {}

        for tx in uncleared_transactions:
            text = []

            header = tx[0]

            text.append(lines[header])

            ptr = header + 1

            while line_status.get(ptr) in {
                line_type.GENERATED_COMMENTS,
                line_type.UNCLEARED_BODY,
            }:
                tx.append(line_status[ptr])
                text.append(lines[ptr])

                ptr += 1

            tx_text[header] = "".join(text)

        if search_string != search_string_type.ALL:
            uncleared_transactions = [
                tx
                for tx in uncleared_transactions
                if re.search(search_string, tx_text[tx[0]], flags=re.I)
            ]

            tx_text = {
                k: v
                for k, v in tx_text.items()
                if re.search(search_string, v, flags=re.I)
            }

        uncleared_transactions = {tx[0]: tx for tx in uncleared_transactions}

        for k, v in tx_text.items():
            print(
                term.home
                + term.clear
                + term.move_y(term.height - len(uncleared_transactions[k]))
            )
            print(v)

            decision = get_tx_decision()

            if decision == tx_decision_type.NO:
                pass

            elif decision == tx_decision_type.YES:
                lines[k] = re.sub(r"^(\d\d\d\d-\d\d-\d\d) ", r"\1 * ", lines[k])

                if uncleared_transactions[k][1] == line_type.GENERATED_COMMENTS:
                    del lines[k + 1]

                with open(ledger_path, "w") as f:
                    for k in sorted(lines.keys()):
                        f.write(lines[k])

            else:
                raise ValueError
