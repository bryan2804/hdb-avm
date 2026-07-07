"""Parsers for raw HDB dataset fields.

These must remain byte-for-byte compatible with the logic the deployed model
was trained on; changing them silently changes what the model sees.
"""

import re


def remaining_lease_to_years(text: str) -> float:
    """Convert ``'61 years 04 months'`` -> ``61.33``."""
    years, months = 0, 0
    parts = str(text).split()
    for i, part in enumerate(parts):
        if part.startswith("year"):
            years = int(parts[i - 1])
        elif part.startswith("month"):
            months = int(parts[i - 1])
    return round(years + months / 12, 2)


def storey_range_to_mid(storey_range: str) -> int:
    """Convert ``'10 TO 12'`` -> ``11``."""
    nums = re.findall(r"\d+", str(storey_range))
    if len(nums) >= 2:
        return (int(nums[0]) + int(nums[1])) // 2
    return int(nums[0]) if nums else 0
