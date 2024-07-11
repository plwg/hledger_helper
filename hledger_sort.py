#!/usr/bin/env python3
import subprocess
import shutil
from pathlib import Path


def main():
    # Ask whether to create backup
    is_back_up = input("Create backup? (Y/N)")

    # Expand the home directory
    ledger_dir_path = Path("~/finance").expanduser()

    # Define file paths
    LEDGER_FILE_PATH = ledger_dir_path / "my.ledger"
    LEDGER_HEADER_FILE_PATH = ledger_dir_path / "my.ledger.header"

    if is_back_up.lower() in {"y", "yes"}:
        backup_location = LEDGER_FILE_PATH.with_suffix(LEDGER_FILE_PATH.suffix + ".bak")
        shutil.copy(LEDGER_FILE_PATH, backup_location)
        print(f"Created backup at {backup_location}")

    # Generate the ledger content
    sorted_ledger = subprocess.run(
        ["hledger", "print", "-x", "-f", str(LEDGER_FILE_PATH)],
        capture_output=True,
        text=True,
    ).stdout

    # Read the header file
    with open(LEDGER_HEADER_FILE_PATH, "r") as header_file:
        header_content = header_file.read()
    print(f"Read header file from {LEDGER_HEADER_FILE_PATH}")

    # Check the result ledger
    sorted_ledger = f"{header_content}\n\n\n{sorted_ledger}"
    subprocess.run(
        ["hledger", "check", "-f", "-"], input=sorted_ledger, text=True, check=True
    )

    # Write the sorted ledger to the file
    with open(LEDGER_FILE_PATH, "w") as ledger_file:
        ledger_file.write(sorted_ledger)

    print(f"Write sorted ledger to {LEDGER_FILE_PATH}")


if __name__ == "__main__":
    main()
