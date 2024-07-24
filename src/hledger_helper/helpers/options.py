from collections import namedtuple

from blessed import Terminal

from .clean_up_journal import clean_up_journal
from .clear_tx import clear_tx
from .fetch_price import fetch_price
from .generate_recurring_tx import generate_recurring_tx

Helper = namedtuple("Helper", ["name", "function"])

_options = {
    "Mark Transactions as Cleared": clear_tx,
    "Clean Up Journal": clean_up_journal,
    "Fetch Prices": fetch_price,
    "Generate Recurring Transactions": generate_recurring_tx,
}


def get_main_menu_options():
    # Menu options
    menu_options = list(_options.keys())  # Use () instead of []
    menu_options.sort()
    menu_options.append("Exit")

    return tuple(menu_options)


def get_selected_option(option):
    if option not in _options:
        exit()

    else:
        term = Terminal()
        print(term.clear)
        print(term.move_y(term.height))

        return Helper(option, _options[option])
