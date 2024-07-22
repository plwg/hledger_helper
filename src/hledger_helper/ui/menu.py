from blessed import Terminal

from .print_greeting import print_greeting

# Initialize blessed's Terminal
term = Terminal()


# Function to display the menu
def display_menu(options, max_len, len_options, selected_index):
    print(term.home + term.move_y(term.height // 2 - len_options // 2))
    print_greeting()
    for index, option in enumerate(options):
        if index == selected_index:
            print(term.center(term.bold_white_on_green(f"{option}".ljust(max_len))))
        else:
            print(term.center(term.white(f"{option}".ljust(max_len))))


# Main loop for the menu
def menu(options):
    selected_index = 0

    max_len = max(len(o) for o in options)
    len_options = len(options)
    end = len_options - 1

    with term.cbreak(), term.hidden_cursor(), term.fullscreen():
        display_menu(options, max_len, len_options, selected_index)
        while True:
            key = term.inkey()

            if key.name == "KEY_ENTER":
                break
            elif key.name == "KEY_UP":
                if selected_index == 0:
                    selected_index = end

                else:
                    selected_index -= 1
                display_menu(options, max_len, len_options, selected_index)
            elif key.name == "KEY_DOWN":
                if selected_index == end:
                    selected_index = 0
                else:
                    selected_index += 1
                display_menu(options, max_len, len_options, selected_index)
            else:
                pass

    return options[selected_index]
