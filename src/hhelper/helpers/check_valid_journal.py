from __future__ import annotations

import subprocess
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def run_hledger_on_text(
    args: tuple[str, ...], text: str, ledger_path: Path
) -> tuple[int, str, str]:
    # The text goes in on stdin, with hledger started in the ledger's directory
    # so relative include directives resolve as they do for the ledger itself.
    # Returns (exit code, stdout, stderr)
    result = subprocess.run(
        ["hledger", *args, "-f", "-"],
        input=text,
        cwd=ledger_path.resolve().parent,
        text=True,
        capture_output=True,
        check=False,
    )

    # hledger names stdin "-"; report problems against the ledger instead
    stderr = result.stderr.replace("Error: -:", f"Error: {ledger_path}:")
    return result.returncode, result.stdout, stderr


@cache
def _run_hledger_check(text: str, ledger_path: Path) -> tuple[int, str]:
    returncode, _, stderr = run_hledger_on_text(("check",), text, ledger_path)
    return returncode, stderr


def check_valid_journal(text: str, ledger_path: Path) -> bool:
    # hledger may print warnings to stderr; only a non-zero exit code is an error
    returncode, err = _run_hledger_check(text, ledger_path)

    if err != "":
        print(err)

    return returncode == 0
