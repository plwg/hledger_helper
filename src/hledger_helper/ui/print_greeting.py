from blessed import Terminal

term = Terminal()


def print_greeting():
    greeting_message = "Hledger Helper"
    print(term.green(term.center(greeting_message)))
