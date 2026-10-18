from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from blessed import Terminal


def move_y(term: Terminal, row: int) -> str:
    # blessed annotates capability strings as taking str, but move_y takes a row
    return cast("Callable[[int], str]", term.move_y)(row)


def press_key_to_continue(term: Terminal) -> None:
    with term.cbreak(), term.hidden_cursor():
        print(term.bold_white_on_green("Press any key to continue"), end="", flush=True)

        term.inkey()


def clear_screen_move_to_bottom(term: Terminal) -> None:
    print(term.clear() + term.home() + move_y(term, term.height))


def ask_yes_no(term: Terminal, prompt: str, *, default: bool) -> bool:
    # "q"/"quit" count as no; anything unrecognised asks again
    while True:
        answer = input(term.green(prompt)).lower()

        if answer == "":
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no", "q", "quit"}:
            return False

        print(term.red(f"Invalid input: {answer!r}"))
