from __future__ import annotations

import csv
import io
import subprocess
from collections import Counter, defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

from hhelper.helpers.similarity import (
    looks_like_typo,
    name_key,
    similar_groups,
    variant_groups,
)

if TYPE_CHECKING:
    from pathlib import Path


class HledgerError(Exception):
    pass


def run_hledger(args: tuple[str, ...], ledger_path: Path) -> str:
    # Reads the ledger and everything it includes
    result = subprocess.run(
        ["hledger", *args, "-f", str(ledger_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HledgerError(result.stderr)
    return result.stdout


def description_counts(ledger_path: Path) -> Counter[str]:
    # Transactions per description; print's CSV has one row per posting
    rows = csv.DictReader(io.StringIO(run_hledger(("print", "-O", "csv"), ledger_path)))
    transactions = {(row["txnidx"], row["description"]) for row in rows}
    return Counter(description for _, description in transactions)


def account_counts(ledger_path: Path) -> Counter[str]:
    # Postings per account, including accounts that are declared but unused
    accounts = run_hledger(("accounts",), ledger_path).splitlines()
    counts: Counter[str] = Counter(dict.fromkeys(accounts, 0))
    report = run_hledger(("balance", "--count", "-N", "-E", "-O", "csv"), ledger_path)
    for account, count in list(csv.reader(io.StringIO(report)))[1:]:
        counts[account] = int(count)
    return counts


def similar_accounts(names: set[str]) -> list[tuple[str, ...]]:
    # Siblings (accounts with the same parent) written differently or looking
    # like typos of each other. Comparing siblings only keeps assets:bank and
    # liabilities:bank apart, and catches a misspelt parent once
    children: dict[str, set[str]] = defaultdict(set)
    for name in names:
        parts = name.split(":")
        for depth in range(len(parts)):
            children[":".join(parts[:depth])].add(parts[depth])

    def full(parent: str, segment: str) -> str:
        return f"{parent}:{segment}" if parent else segment

    found: list[tuple[str, ...]] = []
    for parent in sorted(children):
        segments = sorted(children[parent])
        found += [tuple(full(parent, s) for s in g) for g in variant_groups(segments)]
        found += [
            (full(parent, a), full(parent, b))
            for a, b in combinations(segments, 2)
            if looks_like_typo(a, b)
        ]
    return found


def subtree_count(counts: Counter[str], account: str) -> int:
    return sum(
        count
        for name, count in counts.items()
        if name == account or name.startswith(account + ":")
    )


def _groups(count: int) -> str:
    return f"{count} group{'' if count == 1 else 's'} of possible variants"


def _label(names: tuple[str, ...] | list[str]) -> str:
    keys = {name_key(name.rsplit(":", 1)[-1]) for name in names}
    return "written differently" if len(keys) == 1 else "similar"


def similar_report(ledger_path: Path) -> str:
    descriptions = description_counts(ledger_path)
    accounts = account_counts(ledger_path)
    lines: list[str] = []

    description_groups = similar_groups(descriptions)
    lines.append(f"Descriptions: {_groups(len(description_groups))}")
    for group in description_groups:
        variants = sorted(group, key=lambda d: (-descriptions[d], d))
        lines.append(f"  {_label(group)}:")
        lines += [f"    {d!r}  ({descriptions[d]})" for d in variants]

    account_groups = similar_accounts(set(accounts))
    lines.append("")
    lines.append(f"Accounts: {_groups(len(account_groups))}")
    for group in account_groups:
        lines.append(f"  {_label(group)}:")
        lines += [f"    {a}  ({subtree_count(accounts, a)})" for a in group]

    lines += [
        "",
        "Counts are transactions for descriptions and postings for accounts.",
        "This report only reads your journal. To fix what it finds:",
        "  - names from bank imports: map them in your CSV rules",
        "  - accounts: add an alias directive, e.g. alias expenses:grocerys = expenses:groceries,",
        "    or rename them in the files",
        "  - also see hledger accounts --unused and hledger check accounts",
    ]
    return "\n".join(lines)
