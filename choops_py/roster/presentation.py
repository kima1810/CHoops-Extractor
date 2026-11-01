"""Readable roster values without changing their on-disc representation."""

import re


def height_text(inches):
    feet, remainder = divmod(int(inches), 12)
    return f"{feet} ft {remainder} in"


def height_inches(text):
    match = re.fullmatch(r"\s*(\d+)\s*(?:ft|')\s*(\d+)\s*(?:in|\")?\s*", str(text))
    if not match or not 0 <= int(match[2]) < 12:
        raise ValueError("Enter feet and inches, for example 6 ft 3 in")
    return int(match[1]) * 12 + int(match[2])
