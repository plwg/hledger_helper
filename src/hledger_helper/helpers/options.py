from .clear_tx import clear_tx
from .fetch_price import fetch_price
from .sort_tx import sort_tx

_options = {
    "Clear Transaction": clear_tx,
    "Sort Ledger": sort_tx,
    "Fetch Price": fetch_price,
    # "Generate Recurring Transaction": generate_recurring_tx,  # Uncomment when implemented
}


def get_menu_options():
    # Menu options
    menu_options = list(_options.keys())  # Use () instead of []
    menu_options.sort()
    menu_options.append("Exit")

    return tuple(menu_options)


def get_selected_option(option):
    if option not in _options:
        exit()

    else:
        return _options[option]
