#!/usr/bin/env python3

import os
import subprocess
import shutil

def main():

    # Ask whether to create backup

    is_back_up = input("Create backup? (Y/N)")

    # Define file paths
    LEDGER_FILE_PATH = os.path.expanduser("~/code/hledger_helper/my.ledger")
    LEDGER_HEADER_FILE_PATH = os.path.expanduser("~/finance/my.ledger.header")

    if is_back_up.lower() in {'y','yes'}:

        shutil.copy(LEDGER_FILE_PATH,LEDGER_FILE_PATH + ".bak")

    # Generate the ledger content
    sorted_ledger = subprocess.run(["hledger","print", "-x" ,"-f", LEDGER_FILE_PATH], capture_output=True, text=True).stdout

    # Read the header file
    with open(LEDGER_HEADER_FILE_PATH, "r") as header_file:
        header_content = header_file.read()

    # Prepend the header to the ledger file
    with open(LEDGER_FILE_PATH, "r+") as ledger_file:
        ledger_file.write(f"{header_content}\n\n\n{sorted_ledger}")

if __name__ == "__main__":

    main()
