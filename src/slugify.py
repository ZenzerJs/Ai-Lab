import re
import unicodedata


def slugify(value: str, allow_unicode: bool = False, separator: str = "-") -> str:
    """
    Convert a string into a URL-friendly slug.

    Args:
        value: The string to slugify.
        allow_unicode: If True, keep Unicode characters instead of transliterating to ASCII.
        separator: The character separating slug words (default: '-').

    Returns:
        A lowercase slug string with disallowed characters removed and whitespace/repeats normalized.
    """
    if not isinstance(value, str):
        value = str(value)

    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )

    value = value.lower()
    # Replace non-alphanumeric (or non-word) characters with the separator
    if allow_unicode:
        value = re.sub(r"[^\w\s-]", "", value)
    else:
        value = re.sub(r"[^a-z0-9\s-]", "", value)

    # Replace whitespace and repeated separators with a single separator
    escaped_sep = re.escape(separator)
    value = re.sub(r"[-\s]+", separator, value)
    value = re.sub(rf"{escaped_sep}+", separator, value)

    return value.strip(separator)
