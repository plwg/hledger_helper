from hhelper.helpers.align_posting import align_amounts


def decimal_columns(text: str) -> set[int]:
    return {line.index(".") for line in text.splitlines() if "USD" in line}


def test_aligns_amounts_on_the_decimal_point() -> None:
    text = (
        "2024-01-01 shop\n    expenses:food  1.50 USD\n    assets:bank  -1234.50 USD\n"
    )

    assert len(decimal_columns(align_amounts(text))) == 1


def test_aligns_across_transactions() -> None:
    text = (
        "2024-01-01 a\n"
        "    expenses:food  1.50 USD\n"
        "    assets:bank\n"
        "\n"
        "2024-01-02 b\n"
        "    expenses:rent:long:account:name  1000.00 USD\n"
        "    assets:bank\n"
    )

    assert len(decimal_columns(align_amounts(text))) == 1


def test_comment_lines_with_numbers_are_left_alone() -> None:
    text = (
        "2024-01-01 Payee v1.2  ; note 1.5\n"
        "    ; rate 1.5\n"
        "    ; n  2.5\n"
        "    expenses:food  1.50 USD  ; tip 0.5\n"
        "    assets:bank\n"
    )

    lines = align_amounts(text).splitlines()

    assert lines[0] == "2024-01-01 Payee v1.2  ; note 1.5"
    assert lines[1] == "    ; rate 1.5"
    assert lines[2] == "    ; n  2.5"


def test_lines_without_amounts_are_unchanged() -> None:
    text = "2024-01-01 a\n    expenses:food\n    assets:bank\n"

    assert align_amounts(text) == text
