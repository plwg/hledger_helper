from __future__ import annotations

import difflib
import os
import re
import subprocess
from typing import TYPE_CHECKING

from hhelper.helpers.align_posting import align_amounts
from hhelper.helpers.check_valid_journal import run_hledger_on_text
from hhelper.helpers.return_status import STATUS
from hhelper.helpers.safe_write import safe_write
from hhelper.ui.display import ask_yes_no, move_y

if TYPE_CHECKING:
    from pathlib import Path

    from blessed import Terminal


# Directives that hledger applies only within their own file (and the files it
# includes). They do not reach the ledger from an included header, and
# clean-up keeps the ledger's own as written, since hledger print drops them
_FILE_SCOPED_DIRECTIVE = re.compile(
    r"(?:alias|end aliases|apply account|end apply account|apply year|year|Y|D)(?:\s|\d|$)"
)


def header_start(
    ledger_path: Path,
    header_path: Path,
    header_content: str,
    ledger_text: str,
    term: Terminal,
) -> str:
    # What the cleaned ledger starts with: the ledger's own file-scoped
    # directives, untouched and in order, then the header. Including the header
    # keeps one copy of its directives, which every command then reads; a
    # header with file-scoped directives has to be copied in for them to apply
    ledger_directives = [
        line for line in ledger_text.splitlines() if _FILE_SCOPED_DIRECTIVE.match(line)
    ]
    file_scoped = [
        line
        for line in header_content.splitlines()
        if _FILE_SCOPED_DIRECTIVE.match(line)
    ]

    if file_scoped:
        print(
            term.bold_white(
                f"Copied the header file {header_path} into the ledger: it has"
                f" {file_scoped[0].split()[0]} directives, which hledger only applies"
                " within the file they are in"
            )
        )
        # Lines the copied header already has are not repeated
        header_lines = set(header_content.splitlines())
        kept = [line for line in ledger_directives if line not in header_lines]
        return "".join(f"{line}\n" for line in kept) + header_content + "\n"

    # Absolute, as configured (symlinks are not resolved)
    absolute = os.path.abspath(header_path)
    print(term.bold_white(f"Included the header file {header_path}"))
    return "".join(f"{line}\n" for line in ledger_directives) + f"include {absolute}\n"


def clean_up_journal(
    ledger_path: Path,
    header_path: Path | None,
    backup_ledger_path: Path,
    term: Terminal,
) -> STATUS:
    # The header is the only way directives and comments survive clean-up, so
    # refuse rather than silently dropping them
    if header_path is None or not header_path.is_file():
        problem = (
            "header_file is not set in ~/.config/hhelper/config.toml."
            if header_path is None
            else f"The header file {header_path} does not exist."
        )
        for msg in (
            problem,
            (
                "Clean-up rebuilds the ledger from hledger print, which drops"
                " directives and comments; the header file is what keeps them."
            ),
            (
                "Create the header file (it can be empty) or fix header_file in the"
                f" config. {ledger_path} is left unchanged."
            ),
        ):
            print(term.bold_red(msg))
        return STATUS.WAIT

    with term.hidden_cursor():
        warning_message = (
            "Relying on hledger print, cleaning up has the following behaviors:",
            "- All amounts are shown explicity. Balance assignments are converted into balance assertions.",
            "- Amounts are renormalized to commodity display style.",
            "- All decimal places are shown.",
            "- Directives and inter-transaction comments in the ledger are lost, except",
            "  alias, apply account, Y and D lines (and their end lines), which hledger",
            "  applies only within their own file: they are kept as written, at the top.",
            "  Keep other directives in the header file, which the ledger then includes",
            "  (or copies in, if it has alias, apply account, Y or D directives).",
            "- Valuation affects posting amounts but not balance assertion or balance assignment amounts",
            "  potentially causing those to fail.",
            "- Auto postings can generate postings with too many missing amounts.",
            "- Account aliases can generate bad account names.",
            "- Amounts across transactions are aligned based on decimal point location.",
            "",
            "The cleaner will check that the resulting ledger is a valid journal before writing back to the file.",
            f"The unmodified journal can be found at {backup_ledger_path}",
        )

        max_len = max(len(m) for m in warning_message)
        warning_message = [m.ljust(max_len) for m in warning_message]

        print(term.home + move_y(term, term.height // 2 - len(warning_message) // 2))

        for msg in warning_message:
            print(term.center(term.bold(msg)))

        print(move_y(term, term.height))

        if not ask_yes_no(term, "Continue? (Y/n/q): ", default=True):
            return STATUS.NOWAIT

    print(term.clear + move_y(term, term.height))

    # Generate the ledger content
    print_result = subprocess.run(
        ["hledger", "print", "-x", "-f", str(ledger_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    # On failure stdout is empty; writing it back would leave only the header
    if print_result.returncode != 0:
        print(print_result.stderr)
        print(term.bold_red(f"hledger print failed, {ledger_path} is left unchanged"))
        return STATUS.WAIT

    sorted_ledger = print_result.stdout

    # NOTE: There is no need to account for header here since it is not in the hledger print's output
    sorted_ledger = align_amounts(sorted_ledger)

    with header_path.open() as header_file:
        header_content = header_file.read()

    start = header_start(
        ledger_path, header_path, header_content, ledger_path.read_text(), term
    )
    sorted_ledger = f"{start}\n\n{sorted_ledger}"

    returncode, cleaned_print, err = run_hledger_on_text(
        ("print", "-x"), sorted_ledger, ledger_path
    )

    if returncode != 0:
        print(err)
        print(
            term.bold_red(
                f"Cleaned journal is invalid, {ledger_path} is left unchanged"
            )
        )
        return STATUS.WAIT

    # The cleaned journal must read exactly like the current one. It would not
    # if the header includes a file with transactions (counted twice) or has an
    # alias (applied twice)
    if cleaned_print != print_result.stdout:
        diff = difflib.unified_diff(
            print_result.stdout.splitlines(keepends=True),
            cleaned_print.splitlines(keepends=True),
            "current journal",
            "cleaned journal",
            n=1,
        )
        print("".join(list(diff)[:30]))
        print(
            term.bold_red(
                "The cleaned journal would read differently from the current one,"
                " usually because the header file includes a file with transactions"
                " or has an alias directive."
                f" {ledger_path} is left unchanged"
            )
        )
        return STATUS.WAIT

    # Write the sorted ledger to the file
    safe_write(ledger_path, sorted_ledger)

    print(term.bold_white(f"Write sorted ledger to {ledger_path}"))

    return STATUS.WAIT
