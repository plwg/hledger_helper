import re
import shutil
from pathlib import Path


def main():
    file_path_str = "~/finance/my.ledger"
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

    aborted = False
    uncleared_counter = 0
    pass_done = 0

    while True:
        if pass_done > 0:
            cleared_counter = 0

            try:
                search_string = input(
                    "Regex for filtering transaction (leave blank for no filter): "
                )

                if search_string.lower() in {"quit", "q"}:
                    aborted = True

                    break
            except KeyboardInterrupt:
                print("Interrupted")
                print("Bye!")
                break
            except EOFError:
                print("Interrupted")
                print("Bye!")
                break

        else:
            search_string = ""

        with open(file_path, "r") as f:
            lines = f.readlines()

        encountered_first_posting = False

        with open(file_path, "w", buffering=1) as f:
            for index, line in enumerate(lines):
                encountered_first_posting = re.search(r"^\d\d\d\d-\d\d-\d\d.*", line)

                if encountered_first_posting:
                    break
                else:
                    f.write(line)

            first_posting_index = index

            for index, line in enumerate(lines[index:], start=first_posting_index):
                if aborted:
                    f.write(line)

                elif re.search(r"^\d\d\d\d-\d\d-\d\d", line) and not re.search(
                    r"^\d\d\d\d-\d\d-\d\d \* ", line
                ):
                    unclear_index = index

                    if pass_done == 0:
                        uncleared_counter += 1

                    if pass_done > 0:
                        unclear_tx = []

                        unclear_tx.append(lines[unclear_index])

                        for line in lines[unclear_index + 1 :]:
                            if line.startswith("    "):
                                unclear_tx.append(line)

                            else:
                                break

                        tx_string = "".join(unclear_tx)

                        if (
                            re.search(search_string, tx_string, flags=re.I)
                            or search_string == ""
                        ):
                            print(tx_string)

                            try:
                                user_descision = input(
                                    "Clear this transaction? (Y/n/q): "
                                )

                                if user_descision.lower() in {"y", "yes", ""}:
                                    lines[unclear_index] = re.sub(
                                        r"^(\d\d\d\d-\d\d-\d\d) ",
                                        r"\1 * ",
                                        lines[unclear_index],
                                    )

                                    uncleared_counter -= 1
                                    cleared_counter += 1

                                elif user_descision.lower() in {"q", "quit"}:
                                    aborted = True

                            except KeyboardInterrupt:
                                aborted = True
                                print("")

                            except EOFError:
                                aborted = True
                                print("")

                    f.write(lines[unclear_index])

                elif re.search(
                    r"^\d\d\d\d-\d\d-\d\d \* ", lines[index - 1]
                ) and line.strip().startswith("; generated-transaction:"):
                    pass

                else:
                    f.write(line)

        if uncleared_counter == 0:
            if pass_done > 0:
                print(f"{cleared_counter} transaction(s) cleared.")

            print("No more uncleared transaction remaining! Bye!")
            break

        elif aborted:
            print("Aborted! Bye!")
            break

        else:
            if pass_done > 0:
                print(f"{cleared_counter} transaction(s) cleared.")

            print(f"{uncleared_counter} uncleared transaction(s) remaining.")
            pass_done += 1


# TODO: add check to guard against corruption

if __name__ == "__main__":
    main()
