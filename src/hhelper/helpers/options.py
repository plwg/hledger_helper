import sys
from collections import namedtuple
from enum import Enum, auto

from hhelper.helpers.clean_up_journal import clean_up_journal
from hhelper.helpers.clear_tx import clear_tx
from hhelper.helpers.fetch_price import fetch_price
from hhelper.helpers.generate_recurring_tx import generate_recurring_tx

Helper = namedtuple("Helper", ["name", "function"])


class AvailableHelpers(Enum):
    MARK_CLEAR = auto()
    CLEAN_UP = auto()
    FETCH_PRICE = auto()
    GEN_RECUR = auto()


_helpers = {
    AvailableHelpers.MARK_CLEAR: Helper("Mark Transactions as Cleared", clear_tx),
    AvailableHelpers.CLEAN_UP: Helper("Clean Up Journal", clean_up_journal),
    AvailableHelpers.FETCH_PRICE: Helper("Fetch Prices", fetch_price),
    AvailableHelpers.GEN_RECUR: Helper(
        "Generate Recurring Transactions", generate_recurring_tx
    ),
}


def get_main_menu_options():
    menu_options = sorted(helper.name for helper in _helpers.values())
    menu_options.append("Exit")
    return tuple(menu_options)


def get_selected_option(option, term):
    if option == "Exit":
        print(term.clear + term.home)

        sys.exit()

    for k, v in _helpers.items():
        if v.name == option:
            return k, v.function

    msg = f"Invalid option: {option}"
    raise ValueError(msg)
