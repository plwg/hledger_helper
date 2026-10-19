import pytest

from hhelper.helpers.similarity import (
    edit_distance,
    looks_like_typo,
    name_key,
    similar_groups,
    similar_key_pairs,
    variant_groups,
)


def test_name_key_ignores_case_spacing_and_punctuation() -> None:
    assert name_key("Whole-Foods Market") == name_key("wholefoods  market")


def test_variant_groups() -> None:
    assert variant_groups(["Whole Foods", "WholeFoods", "whole-foods", "Rent"]) == [
        ["Whole Foods", "WholeFoods", "whole-foods"]
    ]


def test_edit_distance_counts_a_swap_as_one_edit() -> None:
    assert edit_distance("salary", "slaary") == 1
    assert edit_distance("grocerys", "groceries") == 2


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("grocerys", "groceries", True),
        ("expenes", "expenses", True),
        ("salary", "slaary", True),
        ("Whole Food", "Whole Foods", True),
        ("Amazon Marketplace", "Amazon Marketplac", True),
        ("Credit-Card", "credit card", False),  # the same, not a typo
        ("Invoice 1001", "Invoice 1002", False),
        ("food2023", "food2024", False),
        ("Rent", "Tent", False),
        ("bank", "band", False),
        ("Uber", "Uber Eats", False),
        ("rent", "food", False),
    ],
)
def test_looks_like_typo(a: str, b: str, expected: bool) -> None:
    assert looks_like_typo(a, b) is expected


def test_similar_key_pairs_matches_comparing_every_pair() -> None:
    keys = [
        name_key(name)
        for name in [
            "Whole Foods",
            "Whole Food",
            "Hole Foods",
            "Starbucks",
            "Starbuck",
            "Groceries",
            "Grocerys",
            "Amazon",
            "Amazom",
            "Rental",
            "Dental",
            "Salary",
            "Slaary",
            "Netflix",
            "Spotify",
        ]
    ]
    every_pair = {
        (a, b) if a < b else (b, a)
        for i, a in enumerate(keys)
        for b in keys[i + 1 :]
        if looks_like_typo(a, b)
    }

    assert similar_key_pairs(keys) == every_pair
    assert len(every_pair) >= 6


def test_similar_groups_form_around_the_most_used_name() -> None:
    counts = {
        "Whole Foods": 10,
        "WHOLE FOODS": 3,
        "Whole Food": 2,
        "Starbucks": 5,
        "Starbuck": 1,
        "payee 1": 1,
        "payee 2": 1,
    }

    assert similar_groups(counts) == [
        ["Whole Foods", "WHOLE FOODS", "Whole Food"],
        ["Starbucks", "Starbuck"],
    ]


def test_similar_groups_do_not_chain() -> None:
    # Each is one edit from the next, but the last is three from the first
    counts = {"abcdefgh": 5, "abcdefgx": 3, "abcdefxx": 2, "abcdexxx": 1}

    assert similar_groups(counts) == [["abcdefgh", "abcdefgx", "abcdefxx"]]
