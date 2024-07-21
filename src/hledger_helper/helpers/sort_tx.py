#!/usr/bin/env python3
import subprocess

from blessed import Terminal

from .check_valid_journal import check_valid_journal
from .status import STATUS


def sort_tx(ledger_path, header_path):
    term = Terminal()
    print(term.clear + term.move_y(term.height))

    # Generate the ledger content
    sorted_ledger = subprocess.run(
        ["hledger", "print", "-x", "-f", str(ledger_path)],
        capture_output=True,
        text=True,
    ).stdout

    # Read the header file
    with open(header_path, "r") as header_file:
        header_content = header_file.read()
    print(term.bold_white(f"Read header file from {header_path}"))

    # Check the result ledger
    sorted_ledger = f"{header_content}\n\n\n{sorted_ledger}"

    check_valid_journal(sorted_ledger)

    # Write the sorted ledger to the file
    with open(ledger_path, "w") as ledger_file:
        ledger_file.write(sorted_ledger)

    print(term.bold_white(f"Write sorted ledger to {ledger_path}"))

    return STATUS.WAIT
