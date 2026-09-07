"""Compatibility input formats, validated by the engine's pinned ADF schema."""

from __future__ import annotations

import json
from typing import Any

from as_engine.converters import check_document


def richtext(value: Any, body_format: str | None = None) -> Any:
    """Keep auto-detection; Markdown strings reach the tagged engine transform."""
    if isinstance(value, dict):
        check_document(value)
        return value
    if not isinstance(value, str):
        return value
    if body_format is None:
        if value.strip().startswith("{"):
            try:
                parsed = json.loads(value)
            except ValueError:
                body_format = "text"
            else:
                if isinstance(parsed, dict):
                    check_document(parsed)
                    return parsed
                body_format = "text"
        else:
            body_format = (
                "markdown"
                if "\n" in value
                or any(marker in value for marker in ("**", "*", "#", "`", "["))
                else "text"
            )
    if body_format == "markdown":
        return value
    if body_format == "adf":
        result = json.loads(value)
    elif body_format == "text":
        # Literal text has no Markdown parser semantics. In particular, blank
        # lines produce empty paragraphs, never an invalid empty text node.
        result = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}] if line else [],
                }
                for line in value.split("\n")
            ],
        }
    else:
        raise ValueError("format must be markdown, text or adf")
    check_document(result)
    return result


def prepare_fields(fields: dict[str, Any]) -> None:
    """Convert only system rich text; instance textarea metadata remains tagged."""
    for name in ("description", "environment"):
        if name in fields:
            fields[name] = richtext(fields[name])
