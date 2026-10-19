from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def name_key(name: str) -> str:
    # Names with the same key differ only in case, spacing or punctuation
    return "".join(char for char in name.casefold() if char.isalnum())


# What banks add to a merchant's name: a payment processor prefix ("SQ *",
# "PAYPAL *"), a web address suffix (".com"), a store number ("#1234") or a
# reference after an asterisk ("AMZN Mktp US*2K3")
_EXTRAS = re.compile(
    r"^(?:sq|tst|sp|pp|paypal|py)\s*\*\s*"
    r"|\.(?:com|net|org|co\.uk|com\.au|co|io)\b"
    r"|#\s*\d+"
    r"|\*\S*"
)


def extras_key(name: str) -> str:
    # Names with the same key differ only in case, spacing, punctuation or
    # the extras banks add (see _EXTRAS)
    return name_key(_EXTRAS.sub(" ", name.casefold())) or name_key(name) or name


def relation(name: str, to: str) -> str:
    # How a name in a group relates to the name the group formed around
    if name_key(name) == name_key(to):
        return "written differently"
    if extras_key(name) == extras_key(to):
        return "with bank extras (.com, #1234, SQ *)"
    if not looks_like_typo(extras_key(name), extras_key(to)):
        if extras_key(to) in extras_key(name):
            return "longer name"
        if extras_key(name) in extras_key(to):
            return "shorter name"
    return "similar"


def variant_groups(names: Iterable[str]) -> list[list[str]]:
    # Names that differ only in case, spacing or punctuation, in groups of
    # more than one
    groups: dict[str, list[str]] = defaultdict(list)
    for name in sorted(set(names)):
        groups[name_key(name)].append(name)
    return [group for group in groups.values() if len(group) > 1]


def edit_distance(a: str, b: str) -> int:
    # Damerau-Levenshtein (optimal string alignment): an adjacent swap is one edit
    previous_previous: list[int] = []
    previous = list(range(len(b) + 1))

    for i, char_a in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            cost = char_a != char_b
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost
            )
            if i > 1 and j > 1 and char_a == b[j - 2] and a[i - 2] == char_b:
                current[j] = min(current[j], previous_previous[j - 2] + 1)
        previous_previous, previous = previous, current

    return previous[len(b)]


def max_edits(length: int) -> int:
    return 1 if length <= 7 else 2


def _fuzzy_candidate(key: str) -> bool:
    # Short names (rent and tent, bank and band) and names with digits (years,
    # invoice numbers) are too often different on purpose to match approximately
    return len(key) >= 5 and not any(char.isdigit() for char in key)


def looks_like_typo(a: str, b: str) -> bool:
    # Similar but not the same: a few edits apart once case, spacing and
    # punctuation are ignored
    key_a, key_b = name_key(a), name_key(b)
    if key_a == key_b or not (_fuzzy_candidate(key_a) and _fuzzy_candidate(key_b)):
        return False
    if abs(len(key_a) - len(key_b)) > max_edits(max(len(key_a), len(key_b))):
        return False
    return edit_distance(key_a, key_b) <= max_edits(max(len(key_a), len(key_b)))


def _deletions(key: str, depth: int) -> set[str]:
    variants = {key}
    for _ in range(depth):
        variants |= {v[:i] + v[i + 1 :] for v in variants for i in range(len(v))}
    return variants


def similar_key_pairs(keys: Iterable[str]) -> set[tuple[str, str]]:
    # Pairs of keys for which looks_like_typo holds, without comparing every
    # pair: keys within k edits share a variant made by deleting up to k
    # characters from each (the SymSpell technique), so only those are compared
    by_variant: dict[str, list[str]] = defaultdict(list)
    for key in {k for k in keys if _fuzzy_candidate(k)}:
        for variant in _deletions(key, max_edits(len(key))):
            by_variant[variant].append(key)

    pairs: set[tuple[str, str]] = set()
    for group in by_variant.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                pair = (a, b) if a < b else (b, a)
                if pair not in pairs and looks_like_typo(a, b):
                    pairs.add(pair)
    return pairs


# Shorter names are contained in too many others ("Bar" in "Barber")
MIN_CONTAINED_LENGTH = 4


def contained_key_pairs(keys: Iterable[str]) -> set[tuple[str, str]]:
    # (shorter, longer) pairs where one key is part of another, e.g. "uber"
    # and "ubereats". Each key's substrings of the lengths that occur are
    # looked up, rather than comparing every pair
    keys = set(keys)
    shorter = {key for key in keys if len(key) >= MIN_CONTAINED_LENGTH}
    lengths = sorted({len(key) for key in shorter})

    pairs: set[tuple[str, str]] = set()
    for key in keys:
        for length in lengths:
            if length >= len(key):
                break
            for start in range(len(key) - length + 1):
                part = key[start : start + length]
                if part in shorter:
                    pairs.add((part, key))
    return pairs


def similar_groups(counts: dict[str, int]) -> list[list[str]]:
    # Groups of names that are the same apart from case, spacing, punctuation
    # and the extras banks add, similar, or part of one another. Each group
    # forms around its most
    # used name and only takes names similar to that one, so a chain of
    # similar names (A ~ B ~ C) does not pull unrelated names together. The
    # first name of each group is the most used one
    by_key: dict[str, list[str]] = defaultdict(list)
    for name in counts:
        by_key[extras_key(name)].append(name)
    key_count = {key: sum(counts[n] for n in names) for key, names in by_key.items()}

    neighbours: dict[str, set[str]] = defaultdict(set)
    for a, b in similar_key_pairs(by_key) | contained_key_pairs(by_key):
        neighbours[a].add(b)
        neighbours[b].add(a)

    groups: list[list[str]] = []
    assigned: set[str] = set()
    for key in sorted(by_key, key=lambda k: (-key_count[k], k)):
        if key in assigned:
            continue
        members = [key] + sorted(neighbours[key] - assigned)
        assigned.update(members)
        names = [name for member in members for name in by_key[member]]
        if len(names) > 1:
            groups.append(sorted(names, key=lambda n: (-counts[n], n)))
    return groups
