from __future__ import annotations

import csv
import io
import shlex
import subprocess
from collections import Counter, defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

from hhelper.helpers.similarity import (
    looks_like_typo,
    relation,
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


def accounts_under(counts: Counter[str], account: str, limit: int = 3) -> str:
    # The accounts with postings under a variant, so it can be found
    used = sorted(
        name
        for name, count in counts.items()
        if count and name.startswith(account + ":")
    )
    if not used:
        return ""
    shown = ", ".join(used[:limit])
    more = f" and {len(used) - limit} more" if len(used) > limit else ""
    return f"; in {shown}{more}"


_ACCOUNT_SED = (
    r"sed -i -E 's/^([[:space:]]+([*!][[:space:]]*)?[([]?)OLD\b/\1NEW/;"
    r" s/^account OLD\b/account NEW/'"
)
_DESCRIPTION_SED = (
    r"sed -i -E 's/^([0-9][^ ]* +([*!] +)?(\([^)]*\) +)?)OLD( *;.*)?$/\1NEW\4/'"
)


def how_to(ledger_path: Path, files: list[str]) -> list[str]:
    file_list = " ".join(shlex.quote(f) for f in files)
    return [
        "How to read it",
        "  Each group starts with its most used name, the likely one to keep. The",
        "  others say how they differ from it:",
        "    written differently  same apart from case, spacing or punctuation",
        "    with bank extras     same apart from a web address (.com), store number",
        "                         (#1234) or payment prefix (SQ *, PAYPAL *)",
        "    similar              one or two typing errors apart (names of 5 or more",
        "                         characters, without digits)",
        "    longer/shorter name  one contains the other (4 or more characters); this",
        "                         also matches inside words, e.g. Rent and Current",
        "  Counts are transactions for descriptions and postings for accounts.",
        "",
        "How to fix it (this report changes nothing)",
        "  Names from bank imports: map them in your CSV rules, so they stay fixed.",
        "  An account, without editing past entries: add an alias to your header file:",
        "    alias OLD = NEW",
        "  Or rename in the files. Back up first; this needs GNU sed (gsed on macOS),",
        "  and OLD is a regular expression, so put a \\ before . * ( ) [ ] in it:",
        f"    account:      {_ACCOUNT_SED} {file_list}",
        f"    description:  {_DESCRIPTION_SED} {file_list}",
        f"  then check the result: hledger check -f {shlex.quote(str(ledger_path))}",
        "  Also useful: hledger accounts --unused (declared but never used) and",
        "  hledger check accounts (fails on undeclared accounts, e.g. typos).",
    ]


def similar_report(ledger_path: Path) -> str:
    descriptions = description_counts(ledger_path)
    accounts = account_counts(ledger_path)
    lines: list[str] = []

    # Each group starts with its most used name, the likely one to keep; the
    # others are marked with how they differ from it
    description_groups = similar_groups(descriptions)
    lines.append(f"Descriptions: {_groups(len(description_groups))}")
    for first, *others in description_groups:
        lines.append(f"  {first!r}  ({descriptions[first]})")
        lines += [
            f"    {d!r}  ({descriptions[d]})  {relation(d, first)}" for d in others
        ]

    account_groups = similar_accounts(set(accounts))
    lines.append("")
    lines.append(f"Accounts: {_groups(len(account_groups))}")
    for group in account_groups:
        first, *others = sorted(group, key=lambda a: (-subtree_count(accounts, a), a))
        lines.append(f"  {first}  ({subtree_count(accounts, first)})")
        for account in others:
            how = relation(account.rsplit(":", 1)[-1], first.rsplit(":", 1)[-1])
            lines.append(
                f"    {account}  ({subtree_count(accounts, account)})  {how}"
                f"{accounts_under(accounts, account)}"
            )

    files = run_hledger(("files",), ledger_path).splitlines()
    lines += ["", *how_to(ledger_path, files)]
    return "\n".join(lines)
