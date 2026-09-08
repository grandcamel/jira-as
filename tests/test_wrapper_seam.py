"""Migration stubs are complete, index-backed, and transport-free."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import textwrap
from pathlib import Path

import click
import pytest
from as_engine.index import ProductIndexes
from as_engine.surface import Surface
from click.testing import CliRunner

from jira_as.cli.legacy import records
from jira_as.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]
ROWS = json.loads((ROOT / "tests/wrapper_verbs.json").read_text())
DROPPED = [row for row in ROWS if row["decision"] == "dropped"]
NOTED = {
    "collaborate attachment upload",
    "collaborate attachment download",
    "issue transition",
    "jsm kb get",
    "time estimate",
}
ALIASES = {
    "collaborate comments add": "collaborate comment add",
    "collaborate comments delete": "collaborate comment delete",
    "collaborate comments list": "collaborate comment list",
    "collaborate comments update": "collaborate comment update",
    "search jql": "search query",
}
NON_LEGACY_COMMANDS = {"api call", "api describe", "api search", "api topics", "help"}
NEW_COMMANDS = {"fields get", "fields cache warm"}
LOCAL_SURVIVORS = {
    "dev parse-commits",
    "fields list",
    "ops cache-clear",
    "ops cache-status",
}
FORBIDDEN_CALLS = {
    "GenericClient",
    "JiraClient",
    "get_client_from_context",
    "get_jira_client",
    "requests",
}
LEGACY_RECEIVERS = {"c", "client", "jira_client"}


def _replacement(row: dict[str, object], positional: str | None = None) -> str:
    replacement = row["replacement"]
    assert isinstance(replacement, str)
    return replacement.replace("ISSUE_KEY", positional) if positional else replacement


def _compiled_by_path() -> dict[str, dict[str, object]]:
    indexes = ProductIndexes(ROOT / "src/jira_as/_generated")
    return {
        f"{entry['group']} {entry['verb']}": entry
        for entry in records(index for _, index in indexes.primary())
    }


def _command_paths(command: click.Command, prefix: tuple[str, ...] = ()) -> set[str]:
    if not isinstance(command, click.Group):
        return {" ".join(prefix)}
    context = click.Context(command)
    paths = set()
    for name in command.list_commands(context):
        child = command.get_command(context, name)
        if child is not None:
            paths.update(_command_paths(child, (*prefix, name)))
    return paths


def _command_for_path(path: str) -> click.Command:
    command: click.Command = cli
    for name in path.split():
        assert isinstance(command, click.Group), path
        child = command.get_command(click.Context(command), name)
        assert child is not None, path
        command = child
    return command


def _called_names(tree: ast.AST) -> set[str]:
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Lambda):
            names.update(
                child.id for child in ast.walk(node.body) if isinstance(child, ast.Name)
            )
    return names


def _local_imports(
    tree: ast.AST, function: object, names: set[str]
) -> dict[str, object]:
    package = function.__module__.rpartition(".")[0]
    resolved = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module_name = "." * node.level + (node.module or "")
        try:
            module = importlib.import_module(module_name, package=package)
        except ImportError:
            continue
        for alias in node.names:
            local_name = alias.asname or alias.name
            if local_name in names:
                resolved[local_name] = getattr(module, alias.name)
    return resolved


def _walk_reachable(callback: object) -> tuple[set[str], bool]:
    queue = [inspect.unwrap(callback)]
    seen = set()
    reached = set()
    surface_call = False
    while queue:
        function = queue.pop()
        if not inspect.isfunction(function):
            continue
        identity = (function.__module__, function.__qualname__)
        if identity in seen:
            continue
        seen.add(identity)
        reached.add(function.__name__)
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        names = _called_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                pytest.fail(f"legacy client call reached: {node.func.id}")
            if isinstance(node.func, ast.Attribute):
                receiver = node.func.value
                if isinstance(receiver, ast.Name) and (
                    receiver.id == "requests" or receiver.id in LEGACY_RECEIVERS
                ):
                    pytest.fail(
                        f"legacy transport call reached: {receiver.id}.{node.func.attr}"
                    )
                if isinstance(receiver, ast.Name) and (
                    receiver.id == "surface" and node.func.attr == "call"
                ):
                    surface_call = True
        bindings = {**function.__globals__, **_local_imports(tree, function, names)}
        for name in names:
            value = bindings.get(name)
            if inspect.isfunction(value) and value.__module__.startswith("jira_as"):
                queue.append(value)
            elif inspect.isclass(value) and value.__name__ == "WorkflowCheckpoint":
                queue.extend(
                    member
                    for _, member in inspect.getmembers(value, inspect.isfunction)
                )
    return reached, surface_call


def test_frozen_table_counts_compiled_records_and_command_paths_agree():
    counts = {
        decision: sum(row["decision"] == decision for row in ROWS)
        for decision in {row["decision"] for row in ROWS}
    }
    assert counts == {"survivor": 35, "dropped": 143, "contract": 14, "deferred": 16}
    assert len(ROWS) == len({row["verb"] for row in ROWS}) == 208

    compiled = _compiled_by_path()
    assert set(compiled) == {row["verb"] for row in DROPPED}
    for row in DROPPED:
        path = row["verb"]
        assert isinstance(path, str)
        assert compiled[path]["invocation"] == _replacement(row)
        if path in NOTED:
            assert compiled[path]["note"] == row["reason"]

    runner = CliRunner()
    for row in ROWS:
        path = row["verb"]
        assert isinstance(path, str)
        result = runner.invoke(cli, [*path.split(), "--help"])
        assert result.exit_code == 0, (path, result.output, result.exception)


def test_command_tree_has_no_unaccounted_legacy_ghosts():
    expected = {row["verb"] for row in ROWS}
    actual = _command_paths(cli)
    normalized = {ALIASES.get(path, path) for path in actual}
    assert expected <= normalized
    unexpected = {
        path
        for path in actual
        if ALIASES.get(path, path) not in expected
        and path not in NON_LEGACY_COMMANDS
        and path not in NEW_COMMANDS
    }
    assert unexpected == set()


def test_migration_topic_is_index_backed_and_transport_free():
    result = CliRunner().invoke(cli, ["help", "migration"])
    assert result.exit_code == 0, result.output
    assert (
        "Legacy verbs now report an indexed replacement with exit 2." in result.output
    )


def test_survivor_callbacks_reach_only_the_generic_transport_path():
    survivors = {row["verb"] for row in ROWS if row["decision"] == "survivor"}
    assert len(survivors) == 35
    for path in survivors:
        command = _command_for_path(path)
        assert command.callback is not None, path
        reached, surface_call = _walk_reachable(command.callback)
        assert reached, path
        if path not in LOCAL_SURVIVORS:
            assert surface_call, path


@pytest.mark.parametrize("row", DROPPED, ids=lambda row: row["verb"])
def test_every_dropped_verb_is_a_zero_transport_migration_hint(row, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("migration stub attempted a transport call")

    monkeypatch.setattr(Surface, "call", forbidden)
    path = row["verb"]
    assert isinstance(path, str)
    record = _compiled_by_path()[path]
    runner = CliRunner()
    result = runner.invoke(cli, [*path.split(), "SBX-1"])
    assert result.exit_code == 2, (path, result.output, result.exception)
    assert json.loads(result.output) == {
        "status": None,
        "messages": [f"Use {_replacement(row, 'SBX-1')}"],
        "operation": record["operation"],
        "note": record["note"],
    }
    help_result = runner.invoke(cli, [*path.split(), "--help"])
    assert help_result.exit_code == 0, (path, help_result.output, help_result.exception)


def test_issue_delete_does_not_treat_an_option_as_its_positional_key():
    result = CliRunner().invoke(cli, ["issue", "delete", "--legacy-flag"])
    assert result.exit_code == 2
    assert json.loads(result.output)["messages"] == [
        "Use api call deleteIssue --issueIdOrKey ISSUE_KEY"
    ]
