"""ProcureFlow – snake_case / camelCase conversion utilities.

Recursive helpers for transforming dict keys between naming conventions.
Used at API boundaries when explicit conversion is needed.
Values are never modified — only string dict keys are transformed.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Single-string converters
# ---------------------------------------------------------------------------

def to_camel(snake_str: str) -> str:
    """Convert a snake_case string to camelCase.

    >>> to_camel("unit_price_cents")
    'unitPriceCents'
    >>> to_camel("id")
    'id'
    >>> to_camel("")
    ''
    """
    if not snake_str:
        return snake_str
    parts = snake_str.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


# Pattern: insert _ before an uppercase letter that follows a lowercase letter
# or before an uppercase letter followed by a lowercase letter (handles acronyms).
_SNAKE_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def to_snake(camel_str: str) -> str:
    """Convert a camelCase string to snake_case.

    >>> to_snake("unitPriceCents")
    'unit_price_cents'
    >>> to_snake("poID")
    'po_id'
    >>> to_snake("id")
    'id'
    >>> to_snake("")
    ''
    """
    if not camel_str:
        return camel_str
    return _SNAKE_RE.sub("_", camel_str).lower()


# ---------------------------------------------------------------------------
# Recursive key converters
# ---------------------------------------------------------------------------

def camelize_keys(obj: object) -> object:
    """Recursively convert all dict keys from snake_case to camelCase.

    Handles dicts, lists, and nested structures.
    Non-dict/list values pass through unchanged.
    """
    if isinstance(obj, dict):
        return {to_camel(k): camelize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [camelize_keys(item) for item in obj]
    return obj


def snakeify_keys(obj: object) -> object:
    """Recursively convert all dict keys from camelCase to snake_case.

    Handles dicts, lists, and nested structures.
    Non-dict/list values pass through unchanged.
    """
    if isinstance(obj, dict):
        return {to_snake(k): snakeify_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [snakeify_keys(item) for item in obj]
    return obj
