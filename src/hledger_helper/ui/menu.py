from blessed import Terminal
from hledger_helper.ui.print_greeting import print_greeting


def menu():
    term = Terminal()

    print(term.home + term.clear + term.move_y(term.height // 2))
    print_greeting()
