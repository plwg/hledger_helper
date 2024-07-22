from collections import namedtuple

from blessed import Terminal

from .clear_tx import clear_tx
from .fetch_price import fetch_price
from .generate_recurring_tx import generate_recurring_tx
from .sort_tx import sort_tx

Helper = namedtuple("Helper", ["name", "function"])

_options = {
    "Clear Transaction": clear_tx,
    "Sort Ledger": sort_tx,
    "Fetch Price": fetch_price,
    "Generate Recurring Transaction": generate_recurring_tx,
}


def get_main_menu_options():
    # Menu options
    menu_options = list(_options.keys())  # Use () instead of []
    menu_options.sort()
    menu_options.append("Exit")

    return tuple(menu_options)


def get_selected_option(option):
    term = Terminal()
    print(term.clear)
    if option not in _options:
        exit()

    else:
        print(term.move_y(term.height))

        return Helper(option, _options[option])
