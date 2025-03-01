import re
from functools import cache


@cache
def get_separator_length(line):
    matches = re.findall(r" {2,}", line.lstrip())
    if matches:
        return len(matches[0])
    return -1


@cache
def expand_separator(line, new_length):
    left_most_white_space = re.match(r"^\s*", line).group()

    before_separator, after_separator = re.split(r" {2,}", line.lstrip(), maxsplit=1)

    new_separator = " " * new_length
    return "".join(
        [left_most_white_space, f"{before_separator}{new_separator}{after_separator}"]
    )


def align_amounts(text):
    lines = text.split("\n")
    anchor_locations = []

    for line in lines:
        if re.search(r"\d\.\d", line):
            anchor_locations.append(re.search(r"\d\.\d", line).span()[0])

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
