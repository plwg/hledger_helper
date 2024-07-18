#!/usr/bin/env python3
import subprocess
from pathlib import Path

from blessed import Terminal


def sort_tx(ledger_path):
    term = Terminal()
    print(term.clear + term.move_y(term.height))
    # Define file paths
    LEDGER_HEADER_FILE_PATH = Path("~/finance/my.ledger.header").expanduser()

    # Generate the ledger content
    sorted_ledger = subprocess.run(
        ["hledger", "print", "-x", "-f", str(ledger_path)],
        capture_output=True,
        text=True,
    ).stdout

    # Read the header file
    with open(LEDGER_HEADER_FILE_PATH, "r") as header_file:
        header_content = header_file.read()
    print(term.bold_white(f"Read header file from {LEDGER_HEADER_FILE_PATH}"))

    # Check the result ledger
    sorted_ledger = f"{header_content}\n\n\n{sorted_ledger}"
    subprocess.run(
        ["hledger", "check", "-f", "-"], input=sorted_ledger, text=True, check=True
    )

    # Write the sorted ledger to the file
    with open(ledger_path, "w") as ledger_file:
        ledger_file.write(sorted_ledger)

    print(term.bold_white(f"Write sorted ledger to {ledger_path}"))
