import re
from functools import cache

_SEPARATOR_PAT = re.compile(r" {2,}")
_LEADING_WHITESPACE_PAT = re.compile(r"^\s*")
_ANCHOR_PAT = re.compile(r"\d\.\d")


@cache
def get_separator_length(line: str) -> int:
    match = _SEPARATOR_PAT.search(line.lstrip())
    if match:
        return len(match.group())
    return -1


@cache
def expand_separator(line: str, new_length: int) -> str:
    left_most_white_space_match = _LEADING_WHITESPACE_PAT.match(line)

    if left_most_white_space_match is None:
        raise ValueError("Match not found.")

    left_most_white_space = left_most_white_space_match.group()

    before_separator, after_separator = _SEPARATOR_PAT.split(line.lstrip(), maxsplit=1)

    if not isinstance(before_separator, str) or not isinstance(after_separator, str):
        msg = "Before_seperator or after_seperator is not string."
        raise TypeError(msg)

    new_separator = " " * new_length
    return "".join(
        [left_most_white_space, f"{before_separator}{new_separator}{after_separator}"]
    )


def is_posting(line: str) -> bool:
    # Only postings are aligned; headers and comment lines can also contain
    # numbers, and comments have no separator to expand
    return (
        line[:1].isspace()
        and not line.lstrip().startswith(";")
        and get_separator_length(line) != -1
    )


def align_amounts(text: str) -> str:
    lines = text.split("\n")
    anchor_locations = []

    for line in lines:
        res = _ANCHOR_PAT.search(line) if is_posting(line) else None

        if res is not None:
            anchor_locations.append(res.span()[0])

        else:
            anchor_locations.append(-1)

    max_anchor_location = max(anchor_locations)

    for index, line in enumerate(lines):
        anchor_loc = anchor_locations[index]

        if anchor_loc != -1:
            diff = max_anchor_location - anchor_loc

            lines[index] = expand_separator(line, get_separator_length(line) + diff)

        else:
            pass

    return "\n".join(lines)
