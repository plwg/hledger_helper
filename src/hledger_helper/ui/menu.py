import time
from functools import lru_cache

from blessed import Terminal

from .print_greeting import print_greeting

term = Terminal()


@lru_cache(maxsize=1)
def format_options(options):
    formatted_options = []

    for index, option in enumerate(options):
        formatted_options.append(f"{index+1}. {option}")

    max_len = max(len(o) for o in formatted_options) + 1

    formatted_options = [o.ljust(max_len) for o in formatted_options]

    return formatted_options


def display_menu(options, len_options, selected_index, is_jump=False):
    print(term.home + term.move_y(term.height // 2 - len_options // 2))
    print_greeting()

    highlight_color_funct = (
        term.bold_white_on_yellow if is_jump else term.bold_white_on_green
    )

    menu_options = format_options(options)

    for index, option in enumerate(menu_options):
        if index == selected_index:
            print(term.center(highlight_color_funct(option)))
        else:
            print(term.center(term.white(option)))


def menu(options):
    selected_index = 0

    len_options = len(options)
    end = len_options - 1

    num_key_option = {str(i) for i in range(1, len_options + 1)}

    with term.cbreak(), term.hidden_cursor(), term.fullscreen():
        display_menu(options, len_options, selected_index)
        while True:
            key = term.inkey()

            if key in num_key_option:
                selected_index = int(key) - 1
                display_menu(options, len_options, selected_index, is_jump=True)
                time.sleep(0.3)
                break

            elif key.name == "KEY_ENTER":
                display_menu(options, len_options, selected_index, is_jump=True)
                time.sleep(0.3)
                break
            elif key.name == "KEY_UP":
                if selected_index == 0:
                    selected_index = end

                else:
                    selected_index -= 1
                display_menu(options, len_options, selected_index)
            elif key.name == "KEY_DOWN":
                if selected_index == end:
                    selected_index = 0
                else:
                    selected_index += 1
                display_menu(options, len_options, selected_index)
            else:
                pass

    return options[selected_index]
