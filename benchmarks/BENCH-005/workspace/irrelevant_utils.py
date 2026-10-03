"""
irrelevant_utils.py - Unrelated string and formatting utility functions.
DO NOT MODIFY THIS FILE.
"""


def slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "-")
