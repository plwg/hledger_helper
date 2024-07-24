def press_key_to_continue(term):
    with term.cbreak(), term.hidden_cursor():
        print(term.bold_white_on_green("Press any key to continue"), end="", flush=True)

        term.inkey()
