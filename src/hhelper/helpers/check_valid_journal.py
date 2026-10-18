from __future__ import annotations

import os
import subprocess
import tempfile
from functools import cache
from pathlib import Path


def run_hledger_on_text(
    args: tuple[str, ...], text: str, ledger_path: Path
) -> tuple[int, str, str]:
    # Run from a temporary file next to the ledger rather than stdin, so
    # relative include directives resolve as they do for the ledger itself.
    # Returns (exit code, stdout, stderr)
    target = ledger_path.resolve()
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )

    try:
        with os.fdopen(fd, "w") as tmp_file:
            tmp_file.write(text)

        result = subprocess.run(
            ["hledger", *args, "-f", f"journal:{tmp_name}"],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        Path(tmp_name).unlink(missing_ok=True)

    # Report problems against the ledger, not the temporary file
    stderr = result.stderr.replace(tmp_name, str(ledger_path))
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
