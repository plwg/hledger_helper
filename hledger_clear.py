# TODO: add check to guard against corruption
import re
import shutil
from enum import Enum
from pathlib import Path
from pprint import pprint

line_type = Enum(
    "Type",
    ["CLEARED", "UNCLEARED_HEAD", "UNCLEARED_BODY", "GENERATED_COMMENTS", "DELETE"],
)
search_string_type = Enum("Type", ["ALL", "QUIT"])
tx_decision_type = Enum("Type", ["YES", "NO", "QUIT"])


def get_tx_decision():
    try:
        user_input = input("Clear Transaction (Y/n/q): ")

        if user_input.lower() in {"quit", "q"}:
            return tx_decision_type.QUIT
        elif user_input.lower() in {"", "y", "yes"}:
            return tx_decision_type.YES
        else:
            return tx_decision_type.NO

    except KeyboardInterrupt:
        print("Interrupted")
        print("Bye!")
        return tx_decision_type.QUIT

    except EOFError:
        print("Interrupted")
        print("Bye!")
        return tx_decision_type.QUIT


def get_regex_search_string():
    try:
        search_string = input(
            "Regex for filtering transaction (leave blank for no filter): "
        )

        if search_string.lower() in {"quit", "q"}:
            return search_string_type.QUIT
        elif search_string == "":
            return search_string_type.ALL
        else:
            return search_string

    except KeyboardInterrupt:
        print("Interrupted")
        print("Bye!")
        return search_string_type.QUIT

    except EOFError:
        print("Interrupted")
        print("Bye!")
        return search_string_type.QUIT


def count_uncleared(lines_status):
    return sum([1 for k, v in lines_status.items() if v == line_type.UNCLEARED_HEAD])


def initialize_line_status(n):
    return {i: line_type.CLEARED for i in range(1, n + 1)}


def update_lines_status(lines_status, lines):
    for line_number in lines_status.keys():
        line = lines[line_number - 1]

        if re.search(r"^\d\d\d\d-\d\d-\d\d", line) and not re.search(
            r"^\d\d\d\d-\d\d-\d\d \* ", line
        ):
            lines_status[line_number] = line_type.UNCLEARED_HEAD

        elif (
            line_number > 1
            and lines_status[line_number - 1] == line_type.UNCLEARED_HEAD
            and line.strip().startswith("; generated-transaction:")
        ):
            lines_status[line_number] = line_type.GENERATED_COMMENTS

        elif (
            line_number > 1
            and lines_status[line_number - 1]
            in {line_type.UNCLEARED_HEAD, line_type.UNCLEARED_BODY}
            and line.startswith("    ")
        ):
            lines_status[line_number] = line_type.UNCLEARED_BODY

        elif (
            line_number > 2
            and lines_status[line_number - 2] == line_type.UNCLEARED_HEAD
            and lines_status[line_number - 1] == line_type.GENERATED_COMMENTS
        ):
            lines_status[line_number] = line_type.UNCLEARED_BODY

        else:
            lines_status[line_number] = line_type.CLEARED

    return lines_status


def main():
    file_path_str = "./my.ledger"
    bak_file_path_str = file_path_str + ".bak"

    file_path = Path(file_path_str).expanduser()
    bak_file_path = Path(bak_file_path_str).expanduser()

    shutil.copy(file_path, bak_file_path)

    greeting_message = """
  _    _ _          _                    _____ _                   _    _      _                 
 | |  | | |        | |                  / ____| |                 | |  | |    | |                
 | |__| | | ___  __| | __ _  ___ _ __  | |    | | ___  __ _ _ __  | |__| | ___| |_ __   ___ _ __ 
 |  __  | |/ _ \/ _` |/ _` |/ _ \ '__| | |    | |/ _ \/ _` | '__| |  __  |/ _ \ | '_ \ / _ \ '__|
 | |  | | |  __/ (_| | (_| |  __/ |    | |____| |  __/ (_| | |    | |  | |  __/ | |_) |  __/ |   
 |_|  |_|_|\___|\__,_|\__, |\___|_|     \_____|_|\___|\__,_|_|    |_|  |_|\___|_| .__/ \___|_|   
                       __/ |                                                    | |              
                      |___/                                                     |_|              
"""

    print(greeting_message)
    print("=============================================")
    print(f"File: {file_path}")
    print(f"Backup file: {bak_file_path}")
    print("=============================================")
    print("Enter regex expression to filter transaction.")
    print("Type 'q', 'quit', CTRL+C, or CTRL+D to quit.")
    print("=============================================")

    with open(file_path, "r") as f:
        lines = f.readlines()

    lines_status = initialize_line_status(len(lines))

    while True:
        update_lines_status(lines_status, lines)

        uncleared_count = count_uncleared(lines_status)

        if uncleared_count == 0:
            print("All cleared. Bye!")
            break

        else:
            print(f"{uncleared_count} uncleared transaction left.")

        search_string = get_regex_search_string()

        if search_string == search_string_type.QUIT:
            break

        uncleared_txs = [
            [k] for k, v in lines_status.items() if v == line_type.UNCLEARED_HEAD
        ]

        tx_text = {}

        for tx in uncleared_txs:
            text = []

            header = tx[0]

            text.append(lines[header - 1])

            ptr = header + 1

            while lines_status.get(ptr) in {
                line_type.GENERATED_COMMENTS,
                line_type.UNCLEARED_BODY,
            }:
                tx.append(lines_status[ptr])
                text.append(lines[ptr - 1])

                ptr += 1

            tx_text[header] = "".join(text)

        pprint(uncleared_txs)
        pprint(tx_text)

        if search_string != search_string_type.ALL:
            uncleared_txs = [
                tx
                for tx in uncleared_txs
                if re.search(search_string, tx_text[tx[0]], flags=re.I)
            ]

            tx_text = {
                k: v
                for k, v in tx_text.items()
                if re.search(search_string, v, flags=re.I)
            }

        pprint(uncleared_txs)
        pprint(tx_text)


if __name__ == "__main__":
    main()
