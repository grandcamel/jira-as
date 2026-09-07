"""Public argv replay for every JAS-48 compatibility-contract variant.

Fixtures deliberately decorate the genuine responder transport.  They supply
the smallest useful response bodies because the engine's broad generated
schemas do not promise display-ready Jira issue, transition, or link values.
Production code never receives these fixture bodies.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import requests
from as_engine.responder import Responder
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager

from .test_contract import CONTRACT_PATH, validate_output


def _issue(key: str = "SBX-1") -> dict[str, Any]:
    issue = {
        "expand": "names",
        "id": "1",
        "self": f"https://example.test/rest/api/3/issue/{key}",
        "key": key,
        "fields": {
            "labels": ["compat-capture", "disposable"],
            "summary": "Compatibility fixture",
            "issuetype": {"name": "Task"},
            "status": {"name": "Backlog"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Fixture User"},
            "reporter": {"displayName": "Fixture User"},
        },
    }
    if key == "SBX-17":
        issue["fields"]["issuelinks"] = [
            {
                "id": "10001",
                "type": {
                    "name": "Blocks",
                    "outward": "blocks",
                    "inward": "is blocked by",
                },
                "inwardIssue": {"key": "SBX-1", "fields": {"summary": "Fixture"}},
            }
        ]
    return issue


def _response(operation_id: str, parameters: dict[str, Any], body: Any) -> Any:
    """Narrow, schema-valid-enough data for the old command formatters."""
    if operation_id == "getIssue":
        return _issue(str(parameters.get("issueIdOrKey", "SBX-1")))
    if operation_id == "createIssue":
        return {"id": "17", "key": "SBX-17", "self": "https://example.test/issue/17"}
    if operation_id == "getComments":
        if parameters.get("issueIdOrKey") == "SBX-17":
            return {
                "comments": [
                    {
                        "id": "123",
                        "author": {"displayName": "Fixture User"},
                        "created": "2026-01-01T00:00:00Z",
                        "body": "Fixture comment",
                    }
                ],
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        return {"comments": [], "total": 0, "startAt": 0, "maxResults": 50}
    if operation_id == "addComment":
        return {
            "id": "123",
            "body": body.get("body") if isinstance(body, dict) else None,
        }
    if operation_id == "getTransitions":
        return {
            "transitions": [
                {"id": "31", "name": "In Progress", "to": {"name": "In Progress"}},
                {"id": "41", "name": "Done", "to": {"name": "Done"}},
            ]
        }
    if operation_id == "getIssueLinkTypes":
        return {
            "issueLinkTypes": [
                {
                    "id": "10000",
                    "name": "Blocks",
                    "outward": "blocks",
                    "inward": "is blocked by",
                    "self": "https://example.test/link-type/10000",
                }
            ]
        }
    if operation_id == "searchAndReconsileIssuesUsingJql":
        return {"issues": [_issue()], "total": 1, "startAt": 0, "maxResults": 50}
    if operation_id == "getFields":
        return [{"id": "customfield_10016", "name": "Story points"}]
    if operation_id == "addWorklog":
        return {
            "id": "12183",
            "timeSpent": "2h 30m",
            "timeSpentSeconds": 9000,
            "started": "2026-01-01T00:00:00Z",
            "comment": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Fixture worklog"}],
                    }
                ],
            },
        }
    return {}


@pytest.fixture
def responder_wire(monkeypatch, tmp_path):
    """Use responder only; a legacy client or HTTP attempt fails this suite."""
    monkeypatch.delenv("JIRA_MOCK_MODE", raising=False)
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda _self: None)
    ConfigManager.reset_instance()
    monkeypatch.setattr(
        requests.Session,
        "send",
        lambda *_args, **_kwargs: pytest.fail("HTTP attempted"),
    )
    # The metadata fallback remains genuine.  Its isolated legacy cache is
    # pointed at pytest storage because this sandbox refuses chmod under HOME.
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    calls: list[tuple[str, dict[str, Any], Any]] = []

    original_call = Responder.call

    def call(self, operation, parameters, body, **kwargs):
        copied_parameters = deepcopy(dict(parameters))
        copied_body = deepcopy(body)
        self.seed(
            operation.operationId,
            [
                Response(
                    200,
                    _response(operation.operationId, copied_parameters, copied_body),
                )
            ],
        )
        response = original_call(self, operation, parameters, body, **kwargs)
        calls.append((operation.operationId, copied_parameters, copied_body))
        return response

    monkeypatch.setattr(Responder, "call", call)
    yield calls
    ConfigManager.reset_instance()


def _argv(tokens: list[str], tmp_path: Path) -> list[str]:
    comment = tmp_path / "comment.md"
    comment.write_text("# Compatibility fixture", encoding="utf-8")
    return [str(comment) if token == "@comment.md" else token for token in tokens]


def _contract_output(argv: tuple[str, ...]) -> dict[str, Any]:
    """Select the output rule from the product's machine-readable contract."""
    records = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["operations"]
    groups = {
        ("issue", "get"): (
            "read",
            3
            if "--fields" in argv
            else 2
            if "--output" in argv
            else 1
            if "--detailed" in argv
            else 0,
        ),
        ("issue", "create"): ("create", 0),
        ("issue", "update"): ("update", 1 if "--description" in argv else 0),
        ("collaborate", "comment", "list"): ("comments", 0),
        ("collaborate", "comment", "add"): (
            "comment",
            1 if "--body-file" in argv else 0,
        ),
        ("lifecycle", "transitions"): ("transitions", 0),
        ("lifecycle", "transition"): (
            "transition",
            0 if argv[-1] == "In Progress" else 1,
        ),
        ("relationships", "link"): ("link", 0),
        ("relationships", "unlink"): ("unlink", 0),
        ("relationships", "get-links"): ("get-links", 0),
        ("relationships", "link-types"): ("link-types", 0),
        ("search", "query"): ("search", 0),
        ("agile", "estimate"): ("enrich", 0),
    }
    key = argv[:3] if argv[:2] == ("collaborate", "comment") else argv[:2]
    host_op, variant = (
        ("enrich", 1 if argv[5] == "2h30m" else 2)
        if key == ("time", "log")
        else ("comments", 1 if argv[3] == "SBX-17" else 0)
        if key == ("collaborate", "comment", "list")
        else ("get-links", 1 if argv[2] == "SBX-17" else 0)
        if key == ("relationships", "get-links")
        else groups[key]
    )
    record = next(item for item in records if item["host_op"] == host_op)
    return record["variants"][variant]["output"]


@pytest.mark.parametrize(
    ("argv", "specification", "expected_operations"),
    [
        (
            ("issue", "get", "SBX-1"),
            {"kind": "text", "lines": [r"^Key:\s+SBX-1$"]},
            ("getIssue",),
        ),
        (
            ("issue", "get", "SBX-1", "--detailed"),
            {"kind": "text", "lines": [r"^Key:\s+SBX-1$", r"^Reporter:.*$"]},
            ("getIssue",),
        ),
        (
            ("issue", "get", "SBX-1", "--output", "json"),
            {
                "kind": "json",
                "required": {
                    "key": "string",
                    "fields": {"type": "object", "required": {"labels": "array"}},
                },
            },
            ("getIssue",),
        ),
        (
            ("issue", "get", "SBX-1", "--fields", "labels", "--output", "json"),
            {
                "kind": "json",
                "required": {
                    "key": "string",
                    "fields": {"type": "object", "required": {"labels": "array"}},
                },
            },
            ("getIssue",),
        ),
        (
            ("collaborate", "comment", "list", "SBX-1"),
            {
                "kind": "text",
                "lines": [
                    r"^Comments on SBX-1 \(0 total\):$",
                    r"^No comments found\.$",
                ],
            },
            ("getComments",),
        ),
        (
            ("collaborate", "comment", "list", "SBX-17"),
            {"kind": "text", "lines": [r"^Comments on SBX-17 \(1 total\):$"]},
            ("getComments",),
        ),
        (
            (
                "collaborate",
                "comment",
                "add",
                "SBX-17",
                "--body",
                "**fixture**",
                "--format",
                "markdown",
            ),
            {"kind": "text", "lines": [r"^✓ Added comment to SBX-17 \(ID: [0-9]+\)$"]},
            ("addComment",),
        ),
        (
            (
                "collaborate",
                "comment",
                "add",
                "SBX-17",
                "--body-file",
                "@comment.md",
                "--format",
                "markdown",
            ),
            {"kind": "text", "lines": [r"^✓ Added comment to SBX-17 \(ID: [0-9]+\)$"]},
            ("addComment",),
        ),
        (
            (
                "issue",
                "create",
                "--project",
                "SBX",
                "--type",
                "Task",
                "--summary",
                "Fixture",
                "--description",
                "Fixture",
            ),
            {"kind": "text", "lines": [r"^✓ Created issue: SBX-17$"]},
            ("createIssue",),
        ),
        (
            ("issue", "update", "SBX-17", "--summary", "Fixture"),
            {"kind": "text", "lines": [r"^✓ Updated issue: SBX-17$"]},
            ("editIssue",),
        ),
        (
            ("issue", "update", "SBX-17", "--description", "**fixture**"),
            {"kind": "text", "lines": [r"^✓ Updated issue: SBX-17$"]},
            ("editIssue",),
        ),
        (
            ("lifecycle", "transitions", "SBX-1"),
            {"kind": "text", "lines": [r"^Available transitions for SBX-1:$"]},
            ("getTransitions",),
        ),
        (
            ("lifecycle", "transition", "SBX-17", "--to", "Done"),
            {"kind": "text", "lines": [r"^✓ Transitioned SBX-17 to Done$"]},
            ("getIssue", "getTransitions", "doTransition"),
        ),
        (
            ("lifecycle", "transition", "SBX-17", "--to", "In Progress"),
            {"kind": "text", "lines": [r"^✓ Transitioned SBX-17 to In Progress$"]},
            ("getIssue", "getTransitions", "doTransition"),
        ),
        (
            ("relationships", "link", "SBX-17", "--type", "Blocks", "--to", "SBX-1"),
            {"kind": "text", "lines": [r"^Linked SBX-17 to SBX-1$"]},
            ("getIssueLinkTypes", "linkIssues"),
        ),
        (
            ("relationships", "unlink", "SBX-17", "SBX-1"),
            {"kind": "text", "lines": [r"^Removed link between SBX-17 and SBX-1$"]},
            ("getIssue", "deleteIssueLink"),
        ),
        (
            ("relationships", "get-links", "SBX-1"),
            {"kind": "text", "lines": [r"^No links found for SBX-1$"]},
            ("getIssue",),
        ),
        (
            ("relationships", "get-links", "SBX-17"),
            {"kind": "text", "lines": [r"^Links for SBX-17:$"]},
            ("getIssue",),
        ),
        (
            ("relationships", "link-types"),
            {"kind": "text", "lines": [r"^Available Link Types:$"]},
            ("getIssueLinkTypes",),
        ),
        (
            (
                "search",
                "query",
                "project = SBX AND statusCategory != Done ORDER BY key ASC",
            ),
            {"kind": "text", "lines": [r"^Found 1 issue\(s\)$"]},
            ("searchAndReconsileIssuesUsingJql",),
        ),
        (
            ("agile", "estimate", "SBX-17", "--points", "5"),
            {
                "kind": "text",
                "lines": [r"^Updated 1 issue\(s\)$", r"^Story points: set to 5\.0$"],
            },
            ("getFields", "editIssue"),
        ),
        (
            ("time", "log", "SBX-17", "--time", "2h30m", "--comment", "fixture"),
            {
                "kind": "text",
                "lines": [
                    r"^Worklog added to SBX-17:$",
                    r"^\s*Time logged: 2h 30m \(9000 seconds\)$",
                ],
            },
            ("addWorklog",),
        ),
        (
            ("time", "log", "SBX-17", "--time", "2h 30m", "--comment", "fixture"),
            {
                "kind": "text",
                "lines": [
                    r"^Worklog added to SBX-17:$",
                    r"^\s*Time logged: 2h 30m \(9000 seconds\)$",
                ],
            },
            ("addWorklog",),
        ),
    ],
)
def test_contract_argv_reaches_responder_and_preserves_output(
    responder_wire, tmp_path, argv, specification, expected_operations
):
    result = CliRunner().invoke(cli, _argv(list(argv), tmp_path))
    assert result.exit_code == 0, result.output
    # The independently repeated grammar is retained as a readable fixture
    # seed; the assertion itself always comes from contract.json.
    assert specification["kind"] == _contract_output(argv)["kind"]
    validate_output(_contract_output(argv), result.stdout)
    assert tuple(operation for operation, _, _ in responder_wire) == expected_operations


def test_labels_pair_reaches_responder_in_order(responder_wire):
    runner = CliRunner()
    read = runner.invoke(
        cli, ["issue", "get", "SBX-17", "--fields", "labels", "--output", "json"]
    )
    update = runner.invoke(
        cli, ["issue", "update", "SBX-17", "--labels", "compat-capture,disposable"]
    )
    assert read.exit_code == update.exit_code == 0, (read.output, update.output)
    record = next(
        item
        for item in json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["operations"]
        if item["host_op"] == "labels"
    )
    output = record["variants"][0]["output"]
    validate_output(output["first"], read.stdout)
    validate_output(output["second"], update.stdout)
    assert tuple(operation for operation, _, _ in responder_wire) == (
        "getIssue",
        "editIssue",
    )


def test_hidden_link_types_preflight_json_reaches_responder(responder_wire):
    result = CliRunner().invoke(
        cli, ["relationships", "link-types", "--output", "json"]
    )
    assert result.exit_code == 0, result.output
    record = next(
        item
        for item in json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["operations"]
        if item["host_op"] == "link"
    )
    validate_output(record["variants"][0]["preflight"]["output"], result.stdout)
    assert tuple(operation for operation, _, _ in responder_wire) == (
        "getIssueLinkTypes",
    )


@pytest.mark.parametrize("duration", ["2h30m", "2h 30m"])
def test_worklog_duration_forms_send_9000_seconds(responder_wire, duration):
    result = CliRunner().invoke(
        cli, ["time", "log", "SBX-17", "--time", duration, "--comment", "fixture"]
    )
    assert result.exit_code == 0, result.output
    assert responder_wire[-1][0] == "addWorklog"
    assert responder_wire[-1][2]["timeSpentSeconds"] == 9000


@pytest.mark.parametrize("source", ["project", "cache"])
def test_story_point_cached_or_configured_field_skips_metadata(
    responder_wire, monkeypatch, source
):
    if source == "project":
        monkeypatch.setattr(
            "jira_as.project_context.get_project_agile_fields",
            lambda _project: {"story_points": "customfield_10016"},
        )
    else:

        class Cache:
            @staticmethod
            def get_fields():
                return [{"id": "customfield_10016", "name": "Story Points"}]

        monkeypatch.setattr(
            "jira_as.project_context.get_project_agile_fields", lambda _project: {}
        )
        monkeypatch.setattr(
            "jira_as.autocomplete_cache.get_autocomplete_cache", lambda: Cache()
        )
    result = CliRunner().invoke(cli, ["agile", "estimate", "SBX-17", "--points", "5"])
    assert result.exit_code == 0, result.output
    assert tuple(operation for operation, _, _ in responder_wire) == ("editIssue",)


def test_markdown_description_uses_the_generic_rich_text_path(responder_wire):
    result = CliRunner().invoke(
        cli,
        [
            "issue",
            "update",
            "SBX-17",
            "--description",
            "**markdown**",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0, result.output
    description = responder_wire[-1][2]["fields"]["description"]
    assert description["type"] == "doc"


def test_disallowed_issue_key_refuses_before_responder(responder_wire):
    result = CliRunner().invoke(cli, ["issue", "get", "GC-1"])
    assert result.exit_code == 1, result.output
    assert responder_wire == []


@pytest.mark.parametrize(
    ("operation", "arguments"),
    [
        ("getFields", ()),
        ("getIssueLinkTypes", ()),
        ("deleteIssueLink", ("--linkId", "10001")),
    ],
)
def test_public_api_metadata_and_delete_remain_site_refused(
    responder_wire, monkeypatch, operation, arguments
):
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    result = CliRunner().invoke(
        cli, ["api", "--transport", "responder", "call", operation, *arguments]
    )
    assert result.exit_code == 4, result.output
    assert responder_wire == []


def test_link_with_a_disallowed_target_refuses_before_responder(responder_wire):
    result = CliRunner().invoke(
        cli, ["relationships", "link", "SBX-17", "--type", "Blocks", "--to", "GC-1"]
    )
    assert result.exit_code == 1, result.output
    assert responder_wire == []
