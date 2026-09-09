"""Register migration-only commands from compiled operation indexes."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import click


def records(indexes: Iterable[Any]) -> list[dict[str, Any]]:
    """Read validated rename records without creating a Surface or transport."""
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index in indexes:
        for operation in index.operations.values():
            entries = operation.extensions.get("x-as-legacy-verbs", [])
            if not isinstance(entries, list):
                raise ValueError("x-as-legacy-verbs must be an array")
            for entry in entries:
                if not isinstance(entry, dict) or not all(
                    isinstance(entry.get(key), str) and entry[key].strip()
                    for key in ("group", "verb", "invocation")
                ):
                    raise ValueError("invalid legacy verb record")
                key = (entry["group"], entry["verb"])
                if key in seen:
                    raise ValueError(f"duplicate legacy verb: {' '.join(key)}")
                seen.add(key)
                result.append(
                    {
                        **entry,
                        "operation": operation.operationId,
                        "note": entry.get(
                            "note", operation.extensions.get("x-as-note")
                        ),
                    }
                )
    return result


class MigrationGroup(click.Group):
    """A removed group still shows actionable replacement hints."""

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("invoke_without_command", True)
        kwargs.setdefault("no_args_is_help", False)
        kwargs.setdefault("callback", self.show_migrations)
        super().__init__(*args, **kwargs)

    @staticmethod
    @click.pass_context
    def show_migrations(ctx: click.Context) -> None:
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())


def _stub(entry: dict[str, Any]) -> click.Command:
    @click.pass_context
    def fail(ctx: click.Context, **_: Any) -> None:
        invocation = entry["invocation"]
        positional = next((arg for arg in ctx.args if not arg.startswith("-")), None)
        if invocation is not None and positional is not None:
            invocation = invocation.replace("ISSUE_KEY", positional)
        click.echo(
            json.dumps(
                {
                    "status": None,
                    "messages": [
                        f"Use {invocation}" if invocation is not None else entry["note"]
                    ],
                    "operation": entry["operation"],
                    "note": entry["note"],
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        raise click.exceptions.Exit(2)

    hint = (
        f"Use {entry['invocation']}"
        if entry["invocation"] is not None
        else entry["note"]
    )
    return click.Command(
        entry["verb"],
        callback=fail,
        help=f"Removed legacy verb. {hint}",
        short_help=hint,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )


def register(
    root: click.Group, entries: Iterable[dict[str, Any]], *, prefix: str = ""
) -> None:
    """Install stubs beneath root; prefix permits lazy loading one product group."""
    for entry in entries:
        path = entry["group"].split()
        if prefix:
            if path[0] != prefix:
                continue
            path = path[1:]
        parent = root
        for name in path:
            child = parent.commands.get(name)
            if child is None:
                child = MigrationGroup(name, help=f"Migration hints for {name}.")
                parent.add_command(child)
            if not isinstance(child, click.Group):
                raise ValueError(f"legacy group conflicts with command: {name}")
            parent = child
        if entry["verb"] in parent.commands:
            parent.commands.pop(entry["verb"])
        parent.add_command(_stub(entry))


def register_retired(root: click.Group, paths: Iterable[str], message: str) -> None:
    """Install migration stubs for verbs with no indexed replacement."""
    entries = []
    for path in paths:
        group, _, verb = path.rpartition(" ")
        entries.append(
            {
                "group": " ".join(part for part in (root.name, group) if part),
                "verb": verb,
                "invocation": None,
                "operation": None,
                "note": message,
            }
        )
    register(root, entries, prefix=root.name or "")
