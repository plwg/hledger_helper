import subprocess
from functools import cache


@cache
def _run_hledger_check(text: str) -> tuple[int, str]:
    result = subprocess.run(
        ["hledger", "check", "-f", "-"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stderr


def check_valid_journal(text: str) -> bool:
    # hledger may print warnings to stderr; only a non-zero exit code is an error
    returncode, err = _run_hledger_check(text)

    if err != "":
        print(err)

    return returncode == 0
