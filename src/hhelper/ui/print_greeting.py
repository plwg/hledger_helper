from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blessed import Terminal


def print_greeting(term: Terminal) -> None:
    greeting_message = (
        r" _   _ _          _                   _   _      _                 ",
        r"| | | | |        | |                 | | | |    | |                ",
        r"| |_| | | ___  __| | __ _  ___ _ __  | |_| | ___| |_ __   ___ _ __ ",
        r"|  _  | |/ _ \/ _` |/ _` |/ _ \ '__| |  _  |/ _ \ | '_ \ / _ \ '__|",
        r"| | | | |  __/ (_| | (_| |  __/ |    | | | |  __/ | |_) |  __/ |   ",
        r"\_| |_/_|\___|\__,_|\__, |\___|_|    \_| |_/\___|_| .__/ \___|_|   ",
        r"                     __/ |                        | |              ",
        r"                    |___/                         |_|              ",
    )
    for line in greeting_message:
        print(term.green(term.center(line)))
    print()
