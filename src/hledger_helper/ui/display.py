def press_key_to_continue(term):
    with term.cbreak(), term.hidden_cursor():
        print(term.bold_white_on_green("Press any key to continue"), end="", flush=True)

        term.inkey()


def clear_screen_move_to_bottom(term):
    print(term.clear() + term.home() + term.move_y(term.height))
