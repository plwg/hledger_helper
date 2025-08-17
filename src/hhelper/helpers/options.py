from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, cast

from hhelper.helpers.clean_up_journal import clean_up_journal
from hhelper.helpers.clear_tx import clear_tx
from hhelper.helpers.fetch_price import fetch_price
from hhelper.helpers.generate_recurring_tx import generate_recurring_tx

if TYPE_CHECKING:
    from blessed import Terminal


@dataclass(frozen=True)
class Helper:
    name: str
    function: Callable


class AvailableHelpers(Enum):
    MARK_CLEAR = auto()
    CLEAN_UP = auto()
    FETCH_PRICE = auto()
    GEN_RECUR = auto()


_helpers = {
    AvailableHelpers.MARK_CLEAR: Helper(
        name="Mark Transactions as Cleared", function=clear_tx
    ),
    AvailableHelpers.CLEAN_UP: Helper(
        name="Clean Up Journal", function=clean_up_journal
    ),
    AvailableHelpers.FETCH_PRICE: Helper(name="Fetch Prices", function=fetch_price),
    AvailableHelpers.GEN_RECUR: Helper(
        name="Generate Recurring Transactions", function=generate_recurring_tx
    ),
}


def get_main_menu_options() -> tuple[str, ...]:
    menu_options = sorted(helper.name for helper in _helpers.values())
    menu_options.append("Exit")
    return tuple(menu_options)


def get_selected_option(option: str, term: Terminal) -> tuple[AvailableHelpers, Helper]:
    if option == "Exit":
        print(term.clear + term.home)

        sys.exit()

    for k, v in _helpers.items():
        if v.name == option:
            return k, cast("Helper", v.function)

    msg = f"Invalid option: {option}"
    raise ValueError(msg)
