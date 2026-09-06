"""Defence-in-depth checks for projects named in CLI parameters.

This is a literal-reference check, not a JQL scope evaluator or an HTTP
authorization boundary. The organization's boundary remains its wrappers.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from .error_handler import ValidationError

ISSUE_KEY = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*)-[0-9]+\b")
QUOTED = r'"(?:\\.|[^"\\])*"' r"|'(?:\\.|[^'\\])*'"
VALUE = rf"(?:{QUOTED}|[^\s,()]+)"
PROJECT_CLAUSE = re.compile(
    r"""(?<![A-Za-z0-9_])(?:"project"|'project'|project)\s*"""
    r"(?:!=|!~|=|~|\bnot\s+in\b|\bin\b|\bwas\s+not\s+in\b|"
    r"\bwas\s+in\b|\bwas\s+not\b|\bwas\b)\s*"
    rf"(?P<value>\((?:{QUOTED}|[^)'\"])*\)|{VALUE})",
    re.IGNORECASE,
)
PROJECT_PARAMETERS = {
    "project",
    "projects",
    "project_key",
    "project_keys",
    "project_id",
    "project_ids",
    "project_key_or_id",
    "to_project",
    "target_project",
    "source_project",
    "share_project",
    "project_filter",
    "project_key_filter",
}


def _values(value: Any) -> Iterator[str]:
    """Flatten parameter collections without opening files or resolving IDs."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _values(item)
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _values(item)


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = re.sub(r"\\(.)", r"\1", value[1:-1])
    return value


def check_project_access(
    params: Mapping[str, Any], allowed_projects: list[str] | None
) -> None:
    """Refuse literal projects outside the configured list before client access.

    All string values are scanned for issue keys and JQL project operands.
    Project parameters also accept comma-separated keys. None disables the
    check entirely; an empty list refuses every detected project reference.
    """
    if allowed_projects is None:
        return
    allowed = {project.upper() for project in allowed_projects}

    def check(project: str) -> None:
        project = _unquote(project).upper()
        if project not in allowed:
            raise ValidationError(
                f"Project {project!r} is not permitted by jira.allowed_projects"
            )

    for name, value in params.items():
        is_project = name in PROJECT_PARAMETERS or (
            name == "key" and "project_type" in params
        )
        if is_project and isinstance(value, int):
            check(str(value))
        for text in _values(value):
            if is_project:
                for project in text.split(","):
                    check(project)
            elif name == "key_or_project" and not ISSUE_KEY.fullmatch(text):
                check(text)
            for match in ISSUE_KEY.finditer(text):
                check(match.group(1))
            for match in PROJECT_CLAUSE.finditer(text):
                raw = match.group("value")
                if raw.startswith("("):
                    for project in re.findall(VALUE, raw[1:-1]):
                        check(project)
                else:
                    check(raw)
