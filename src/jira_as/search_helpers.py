"""
Generic search and matching helpers.

Provides reusable fuzzy matching functions for finding items by name.
"""

from __future__ import annotations

from typing import Any, Callable

from .error_handler import ValidationError


def fuzzy_find_by_name(
    items: list[dict[str, Any]],
    name: str,
    name_getter: Callable[[dict[str, Any]], str] = lambda x: x.get("name", ""),
    item_type: str = "item",
    fuzzy: bool = True,
) -> dict[str, Any]:
    """
    Find an item by name with case-insensitive exact and partial matching.

    The search uses a two-phase approach:
    1. First, look for an exact match (case-insensitive)
    2. If fuzzy=True and no exact match, look for partial matches

    Args:
        items: List of item dictionaries
        name: Name to search for
        name_getter: Function to extract name from item (default: x["name"])
        item_type: Type name for error messages (e.g., "transition", "scheme")
        fuzzy: If True, allow partial matching after exact match fails

    Returns:
        Matching item dictionary

    Raises:
        ValidationError: If no items, not found, or ambiguous match

    Examples:
        >>> transitions = [{"name": "Done"}, {"name": "In Progress"}]
        >>> fuzzy_find_by_name(transitions, "done", item_type="transition")
        {"name": "Done"}

        >>> fuzzy_find_by_name(transitions, "progress", item_type="transition")
        {"name": "In Progress"}
    """
    if not items:
        raise ValidationError(f"No {item_type}s available to match '{name}'")

    name_lower = name.lower()

    # Phase 1: Exact match (case-insensitive)
    exact_matches = [i for i in items if name_getter(i).lower() == name_lower]
    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        match_names = [name_getter(i) for i in exact_matches]
        raise ValidationError(
            f"Multiple exact matches for {item_type} '{name}': "
            + ", ".join(match_names)
        )

    if not fuzzy:
        # No fuzzy matching, report not found
        available = [name_getter(i) for i in items]
        raise ValidationError(
            f"{item_type.capitalize()} '{name}' not found. "
            f"Available: {', '.join(available)}"
        )

    # Phase 2: Partial match (case-insensitive)
    partial_matches = [i for i in items if name_lower in name_getter(i).lower()]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        match_names = [name_getter(i) for i in partial_matches]
        raise ValidationError(
            f"Ambiguous {item_type} name '{name}'. Matches: " + ", ".join(match_names)
        )

    # No matches found
    available = [name_getter(i) for i in items]
    raise ValidationError(
        f"{item_type.capitalize()} '{name}' not found. "
        f"Available: {', '.join(available)}"
    )


def fuzzy_find_by_name_optional(
    items: list[dict[str, Any]],
    name: str,
    name_getter: Callable[[dict[str, Any]], str] = lambda x: x.get("name", ""),
    fuzzy: bool = True,
) -> dict[str, Any] | None:
    """
    Find an item by name, returning None instead of raising on not found.

    Same as fuzzy_find_by_name but returns None for no match instead of raising.
    Still raises ValidationError for ambiguous matches.

    Args:
        items: List of item dictionaries
        name: Name to search for
        name_getter: Function to extract name from item
        fuzzy: If True, allow partial matching

    Returns:
        Matching item or None if not found

    Raises:
        ValidationError: If ambiguous match
    """
    if not items:
        return None

    name_lower = name.lower()

    # Phase 1: Exact match
    exact_matches = [i for i in items if name_getter(i).lower() == name_lower]
    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        match_names = [name_getter(i) for i in exact_matches]
        raise ValidationError(
            f"Multiple exact matches for '{name}': " + ", ".join(match_names)
        )

    if not fuzzy:
        return None

    # Phase 2: Partial match
    partial_matches = [i for i in items if name_lower in name_getter(i).lower()]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        match_names = [name_getter(i) for i in partial_matches]
        raise ValidationError(
            f"Ambiguous name '{name}' matches multiple items: "
            + ", ".join(match_names)
            + ". Please be more specific."
        )

    return None
