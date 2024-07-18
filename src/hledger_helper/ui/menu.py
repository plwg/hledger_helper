from blessed import Terminal
from hledger_helper.ui.print_greeting import print_greeting

# Initialize blessed's Terminal
term = Terminal()

# Menu options
options = [
    "Clear Transaction",
    "Sort Ledger",
    "Generate Recurring Transaction",
    "Fetch Price",
]
options.sort()
options.append("Exit")
max_len = max(len(opt) for opt in options)


# Function to display the menu
def display_menu(selected_index):
    print(term.home + term.clear + term.move_y(term.height // 2 - len(options) // 2))
    print_greeting()
    for index, option in enumerate(options):
        if index == selected_index:
            print(term.center(term.bold_white_on_green(f"{option}".ljust(max_len))))
        else:
            print(term.center(term.white(f"{option}".ljust(max_len))))


# Main loop for the menu
def menu():
    selected_index = 0

    with term.cbreak(), term.hidden_cursor(), term.fullscreen():
        while True:
            display_menu(selected_index)

            key = term.inkey()

            if key.name == "KEY_ENTER":
                break
            elif key.name == "KEY_UP":
                if selected_index == 0:
                    selected_index = len(options) - 1

                else:
                    selected_index = selected_index - 1
            elif key.name == "KEY_DOWN":
                if selected_index == len(options) - 1:
                    selected_index = 0
                else:
                    selected_index = selected_index + 1

    return options[selected_index]
