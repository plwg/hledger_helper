import subprocess
import sys
from functools import cache


@cache
def check_valid_journal(text: str) -> None:
    result = subprocess.run(
        ["hledger", "check", "-f", "-"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    err = result.stderr

    if err != "":
        print(err)
        sys.exit()
