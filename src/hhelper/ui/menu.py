from __future__ import annotations

import time
from functools import lru_cache
from typing import TYPE_CHECKING

from hhelper.ui.print_greeting import print_greeting

if TYPE_CHECKING:
    from collections.abc import Iterable

    from blessed import Terminal


@lru_cache(maxsize=1)
def format_options(options: Iterable[str]) -> list[str]:
    formatted_options = []

    for index, option in enumerate(options):
        formatted_options.append(f"{index + 1}. {option}")

    max_len = max(len(o) for o in formatted_options) + 1

    # Return formmated options
    return [o.ljust(max_len) for o in formatted_options]


def display_menu(
    options: tuple[str, ...],
    term: Terminal,
    len_options: int,
    selected_index: int,
    is_jump: bool,
) -> None:
    print(term.home + term.move_y(term.height // 2 - len_options // 2 - 8))
    print_greeting(term)

    highlight_color_funct = (
        term.bold_white_on_yellow if is_jump else term.bold_white_on_green
    )

    menu_options = format_options(options)

    for index, option in enumerate(menu_options):
        if index == selected_index:
            print(term.center(highlight_color_funct(option)))
        else:
            print(term.center(term.white(option)))


def menu(options: tuple[str, ...], term: Terminal) -> str:
    print(term.clear + term.home)

    selected_index = 0

    len_options = len(options)
    end = len_options - 1

    num_key_option = {str(i) for i in range(1, len_options + 1)}

    with term.cbreak(), term.hidden_cursor():
        display_menu(options, term, len_options, selected_index, is_jump=False)
        while True:
            key = term.inkey()

            if key in num_key_option:
                selected_index = int(key) - 1
                display_menu(options, term, len_options, selected_index, is_jump=True)
                time.sleep(0.2)
                break

            if key.name == "KEY_ENTER":
                display_menu(options, term, len_options, selected_index, is_jump=True)
                time.sleep(0.2)
                break
            if key.name == "KEY_UP":
                if selected_index == 0:
                    selected_index = end

                else:
                    selected_index -= 1
                display_menu(options, term, len_options, selected_index, is_jump=False)
            elif key.name == "KEY_DOWN":
                if selected_index == end:
                    selected_index = 0
                else:
                    selected_index += 1
                display_menu(options, term, len_options, selected_index, is_jump=False)
            else:
                pass

    return options[selected_index]
