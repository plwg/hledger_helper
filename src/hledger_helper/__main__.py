from hledger_helper.helpers.options import get_selected_option
from hledger_helper.ui.menu import menu


def main():
    selection = menu()
    print(get_selected_option(selection))


if __name__ == "__main__":
    main()
