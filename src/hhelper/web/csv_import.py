from __future__ import annotations

import csv
import io
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePath

# Accounts hledger gives a posting when no rule names its account2
UNKNOWN_ACCOUNTS = ("expenses:unknown", "income:unknown")

# File extensions hledger reads as CSV-like by itself; others get a csv: prefix
_CSV_SUFFIXES = (".csv", ".tsv", ".ssv")


class RulesPathError(ValueError):
    pass


def find_rules_files(rules_dir: Path) -> list[str]:
    # Paths relative to rules_dir, skipping hidden folders such as .hhelper
    if not rules_dir.is_dir():
        return []

    found = []
    for path in rules_dir.rglob("*.rules"):
        relative = path.relative_to(rules_dir)
        if path.is_file() and not any(p.startswith(".") for p in relative.parts):
            found.append(relative.as_posix())

    return sorted(found)


def resolve_rules_path(rules_dir: Path, relative: str) -> Path:
    # Keeps every rules file the web page reads or writes inside rules_dir
    if not relative or not relative.endswith(".rules"):
        msg = "A rules file name must end in .rules"
        raise RulesPathError(msg)

    pure = PurePath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        msg = f"Not a path inside the rules folder: {relative}"
        raise RulesPathError(msg)

    if any(part.startswith(".") for part in pure.parts):
        msg = f"Hidden files and folders are not allowed: {relative}"
        raise RulesPathError(msg)

    root = rules_dir.resolve()
    path = (root / pure).resolve()
    if not path.is_relative_to(root):
        msg = f"Not a path inside the rules folder: {relative}"
        raise RulesPathError(msg)

    return path


def _rules_stem(rules_path: str) -> str:
    # "a/card.csv.rules" -> "card"
    name = PurePath(rules_path).name.removesuffix(".rules")
    return PurePath(name).stem if PurePath(name).suffix in _CSV_SUFFIXES else name


def _words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if w}


@dataclass(frozen=True)
class RulesMatch:
    path: str | None
    reason: str


def match_rules(csv_name: str, rules_files: list[str]) -> RulesMatch:
    # hledger's own convention first (FILE.csv uses FILE.csv.rules), then a
    # rules name found inside the CSV name, e.g. "card (2).csv" -> card.csv.rules
    name = PurePath(csv_name).name
    stem = PurePath(name).stem.lower()

    for rules in rules_files:
        if PurePath(rules).name.lower() == f"{name.lower()}.rules":
            return RulesMatch(rules, f"{PurePath(rules).name} is named after the file")

    contained = [
        rules
        for rules in rules_files
        if _rules_stem(rules).lower() and _rules_stem(rules).lower() in stem
    ]
    if contained:
        best = max(contained, key=lambda r: len(_rules_stem(r)))
        return RulesMatch(
            best, f'The file name contains "{_rules_stem(best)}" from {best}'
        )

    # Words shared with the rules file's name or folder, e.g. the bank's name
    csv_words = _words(stem)
    scored = [
        (len(csv_words & _words(PurePath(r).as_posix().removesuffix(".rules"))), r)
        for r in rules_files
    ]
    scored = [(score, r) for score, r in scored if score]
    if scored:
        best_score = max(score for score, _ in scored)
        best = [r for score, r in scored if score == best_score]
        if len(best) == 1:
            return RulesMatch(best[0], f"The file name shares words with {best[0]}")

    return RulesMatch(None, "No rules file matches the file name; pick one")


@dataclass
class Posting:
    account: str
    amount: str
    unknown: bool


@dataclass
class Transaction:
    date: str
    description: str
    postings: list[Posting] = field(default_factory=list)

    @property
    def unknown(self) -> bool:
        return any(p.unknown for p in self.postings)


@dataclass
class Preview:
    journal: str = ""
    transactions: list[Transaction] = field(default_factory=list)
    error: str = ""


def _csv_file_name(csv_name: str) -> str:
    # A safe name for the temporary copy that keeps the extension hledger reads
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", PurePath(csv_name).name).lstrip(".")
    return name or "upload.csv"


def _format_amount(quantity: str, commodity: str) -> str:
    if not commodity:
        return quantity

    sign = "-" if quantity.startswith("-") else ""
    number = quantity.removeprefix("-")
    separator = " " if re.search(r"[A-Za-z]", commodity) else ""
    return f"{sign}{commodity}{separator}{number}"


def _parse_print_csv(text: str) -> list[Transaction]:
    transactions: dict[str, Transaction] = {}

    for row in csv.DictReader(io.StringIO(text)):
        index = row["txnidx"]
        if index not in transactions:
            transactions[index] = Transaction(row["date"], row["description"])

        account = row["account"]
        transactions[index].postings.append(
            Posting(
                account,
                _format_amount(row["amount"], row["commodity"]),
                account in UNKNOWN_ACCOUNTS,
            )
        )

    return list(transactions.values())


def _hledger(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["hledger", *args], capture_output=True, text=True, check=False, timeout=60
    )


def preview_csv(
    csv_content: bytes, csv_name: str, rules_path: Path, rules_content: str | None
) -> Preview:
    # Parses the CSV with hledger, as `hledger import` would, without
    # touching any journal. rules_content, if given, is used instead of the
    # saved file, so unsaved edits can be tried out.
    with tempfile.TemporaryDirectory(prefix="hhelper-") as tmp:
        csv_path = Path(tmp) / _csv_file_name(csv_name)
        csv_path.write_bytes(csv_content)

        if rules_content is not None:
            rules_path = Path(tmp) / "unsaved.rules"
            rules_path.write_text(rules_content)

        source = str(csv_path)
        if csv_path.suffix.lower() not in _CSV_SUFFIXES:
            source = f"csv:{source}"

        base = ["-f", source, "--rules", str(rules_path), "print"]

        try:
            journal = _hledger(base)
        except FileNotFoundError:
            return Preview(error="hledger is not installed or not on PATH")
        except subprocess.TimeoutExpired:
            return Preview(error="hledger took too long to read the file")

        if journal.returncode != 0:
            # Temporary paths mean nothing to the user
            message = journal.stderr.replace(str(csv_path), csv_name)
            return Preview(error=message.strip() or "hledger failed")

        table = _hledger([*base, "-O", "csv"])

    return Preview(
        journal=journal.stdout,
        transactions=_parse_print_csv(table.stdout) if table.returncode == 0 else [],
    )


def find_csv_on_disk(search_dir: Path, csv_name: str, content: bytes) -> Path | None:
    # The browser hides where an uploaded file came from; a file under
    # search_dir with the same name and content is taken to be it, so the
    # import command can name it and hledger finds its .latest dedup file
    name = PurePath(csv_name).name
    for path in sorted(search_dir.rglob(name)):
        relative = path.relative_to(search_dir)
        if any(p.startswith(".") for p in relative.parts) or not path.is_file():
            continue
        if path.stat().st_size == len(content) and path.read_bytes() == content:
            return path
    return None


def import_command(ledger: Path | None, csv_file: Path | str, rules: Path) -> str:
    # The hledger import command for this CSV and rules file, ready to paste
    args = ["hledger"]
    if ledger is not None:
        args += ["-f", str(ledger)]
    args += ["import", str(csv_file), "--rules", str(rules)]
    return shlex.join(args)
