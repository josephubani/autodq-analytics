from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

import pandas as pd


_IDENTIFIER_SEPARATORS = re.compile(r"[\s_-]+")


def identifier_key(value: object) -> str:
    """Return the comparison key used by ADQL's friendly identifier lookup."""
    return _IDENTIFIER_SEPARATORS.sub("", str(value).strip().casefold())


def display_identifier(value: object) -> str:
    """Render a stored snake-case identifier without changing its identity."""
    return re.sub(r"_+", " ", str(value)).strip()


def resolve_identifier(
    value: object,
    available: Iterable[object],
    *,
    label: str = "column",
) -> object:
    """Resolve exact, case-insensitive, or separator-equivalent identifiers.

    Exact spelling always wins. Friendly matching lets a quoted ADQL identifier
    such as ``"Customer Age"`` address a stored ``Customer_Age`` column. A
    non-unique friendly match is rejected instead of guessed.
    """
    requested = str(value).strip()
    candidates = list(available)

    for candidate in candidates:
        if str(candidate) == requested:
            return candidate

    case_matches = [
        candidate
        for candidate in candidates
        if str(candidate).casefold() == requested.casefold()
    ]
    if len(case_matches) == 1:
        return case_matches[0]

    key = identifier_key(requested)
    friendly_matches = [
        candidate
        for candidate in candidates
        if identifier_key(candidate) == key
    ]
    if len(friendly_matches) == 1:
        return friendly_matches[0]
    if len(friendly_matches) > 1:
        rendered = ", ".join(f'"{item}"' for item in friendly_matches)
        raise ValueError(
            f'ADQL {label} "{requested}" is ambiguous. '
            f"Use the exact stored name: {rendered}."
        )

    return value


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display-only copy with readable, collision-safe headings."""
    labels = [display_identifier(column) for column in frame.columns]
    duplicates = Counter(labels)
    safe_labels = [
        str(column) if duplicates[label] > 1 else label
        for column, label in zip(frame.columns, labels)
    ]
    displayed = frame.copy()
    displayed.columns = safe_labels
    return displayed
