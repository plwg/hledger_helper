import re
from functools import cache


@cache
def get_separator_length(line: str) -> int:
    matches = re.findall(r" {2,}", line.lstrip())
    if matches:
        return len(matches[0])
    return -1


@cache
def expand_separator(line: str, new_length: int) -> str:
    left_most_white_space_match = re.match(r"^\s*", line)

    if left_most_white_space_match is None:
        raise ValueError("Match not found.")

    left_most_white_space = left_most_white_space_match.group()

    before_separator, after_separator = re.split(r" {2,}", line.lstrip(), maxsplit=1)

    if not isinstance(before_separator, str) or not isinstance(after_separator, str):
        msg = "Before_seperator or after_seperator is not string."
        raise TypeError(msg)

    new_separator = " " * new_length
    return "".join(
        [left_most_white_space, f"{before_separator}{new_separator}{after_separator}"]
    )


def align_amounts(text: str) -> str:
    lines = text.split("\n")
    anchor_locations = []

    for line in lines:
        res = re.search(r"\d\.\d", line)

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
