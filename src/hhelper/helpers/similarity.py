from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def name_key(name: str) -> str:
    # Names with the same key differ only in case, spacing or punctuation
    return "".join(char for char in name.casefold() if char.isalnum())


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


def similar_groups(counts: dict[str, int]) -> list[list[str]]:
    # Groups of names that are the same apart from case, spacing and
    # punctuation, or similar. Each group forms around its most used name and
    # only takes names similar to that one, so a chain of similar names
    # (A ~ B ~ C) does not pull unrelated names together
    by_key: dict[str, list[str]] = defaultdict(list)
    for name in counts:
        by_key[name_key(name)].append(name)
    key_count = {key: sum(counts[n] for n in names) for key, names in by_key.items()}

    neighbours: dict[str, set[str]] = defaultdict(set)
    for a, b in similar_key_pairs(by_key):
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
            groups.append(names)
    return groups
