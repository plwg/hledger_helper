import subprocess
from functools import cache


@cache
def check_valid_journal(text):
    result = subprocess.run(
        ["hledger", "check", "-f", "-"], input=text, text=True, capture_output=True
    )
    err = result.stderr

    if err != "":
        print(err)
        exit()
