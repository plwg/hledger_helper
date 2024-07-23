from blessed import Terminal

term = Terminal()


def print_greeting():
    greeting_message = (
        " _   _ _          _                   _   _      _                 ",
        "| | | | |        | |                 | | | |    | |                ",
        "| |_| | | ___  __| | __ _  ___ _ __  | |_| | ___| |_ __   ___ _ __ ",
        "|  _  | |/ _ \/ _` |/ _` |/ _ \ '__| |  _  |/ _ \ | '_ \ / _ \ '__|",
        "| | | | |  __/ (_| | (_| |  __/ |    | | | |  __/ | |_) |  __/ |   ",
        "\_| |_/_|\___|\__,_|\__, |\___|_|    \_| |_/\___|_| .__/ \___|_|   ",
        "                     __/ |                        | |              ",
        "                    |___/                         |_|              ",
    )
    for line in greeting_message:
        print(term.green(term.center(line)))
    print()
