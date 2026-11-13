"""Name and text normalisation.

Display names keep their original case and diacritics: they are what a user reads.
A separate ``normalized_name`` is derived only for exact-match identity lookup. It is
never used to decide that two entities are the same by similarity — an exact normalised
match is evidence, a fuzzy match is not (data rule D8).
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_UNSAFE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Characters that carry meaning for downstream text or SQL-like contexts.
_STRIP_TOKENS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def clean_display_name(value: str, *, max_length: int = 160) -> str:
    """Trim, collapse internal whitespace, and reject control characters.

    Raises ``ValueError`` for an empty result or one that exceeds the column length.
    Control characters are rejected rather than stripped, because silently altering a
    name would make the stored value no longer the provider's value.
    """

    if not isinstance(value, str):
        raise ValueError("name must be a string")
    if _UNSAFE_CONTROL.search(value):
        raise ValueError("name contains control characters")
    cleaned = _WHITESPACE.sub(" ", value.translate(_STRIP_TOKENS)).strip()
    if not cleaned:
        raise ValueError("name must not be empty")
    if len(cleaned) > max_length:
        raise ValueError(f"name exceeds {max_length} characters")
    return cleaned


def normalize_name(value: str) -> str:
    """Produce a comparison key: casefolded, accent-free, punctuation-collapsed.

    The output is deliberately lossy and used only for exact equality. It is stable for
    the same input across processes and platforms.
    """

    cleaned = clean_display_name(value, max_length=400)
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    folded = without_marks.casefold()
    # Keep letters, digits, and spaces; anything else becomes a space.
    kept = "".join(
        character if character.isalnum() or character.isspace() else " "
        for character in folded
    )
    return _WHITESPACE.sub(" ", kept).strip()


def normalize_code(value: str | None) -> str | None:
    """Normalise a short code (TLA / competition code) to upper case without spaces."""

    if value is None:
        return None
    candidate = _WHITESPACE.sub("", value).strip().upper()
    if not candidate:
        return None
    if len(candidate) > 32:
        raise ValueError("code exceeds 32 characters")
    return candidate
