"""Paging acceptance through Jira argv and inspectable responder requests."""

import json
from pathlib import Path

import pytest
import requests
from as_engine.index import ProductIndexes
from as_engine.responder import Responder
from as_engine.surface import Surface
from click.testing import CliRunner

from jira_as.cli.main import cli


class OriginResponder(Responder):
    base_url = "https://offline.invalid"


@pytest.fixture
def wire(monkeypatch):
    indexes = ProductIndexes(Path(__file__).parents[1] / "src/jira_as/_generated")
    responders = {name: OriginResponder(index) for name, index in indexes.primary()}
    surface = Surface(indexes, lambda name, _: responders[name])
    monkeypatch.setattr(
        "jira_as.cli.commands.api_cmds.create_surface", lambda **_: surface
    )
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **kw: pytest.fail("unexpected HTTP")
    )
    return surface, responders


def invoke(*args):
    return CliRunner().invoke(cli, ["api", "call", *args])


TOKEN_CASES = [
    (
        "platform",
        "searchAndReconsileIssuesUsingJql",
        ["--jql", "project = SBX"],
        "issues",
        False,
    ),
    (
        "platform",
        "searchAndReconsileIssuesUsingJqlPost",
        ["--field", "jql=project = SBX"],
        "issues",
        True,
    ),
    (
        "platform",
        "getBulkChangelogs",
        ["--field", 'issueIdsOrKeys=["SBX-1"]'],
        "issueChangeLogs",
        True,
    ),
    ("software", "getIssuesForBacklogJSIS", ["--boardId", "1"], "issues", False),
    (
        "software",
        "getIssuesWithoutEpicForBoardJSIS",
        ["--boardId", "1"],
        "issues",
        False,
    ),
    (
        "software",
        "getBoardIssuesForEpicJSIS",
        ["--boardId", "1", "--epicId", "2"],
        "issues",
        False,
    ),
    ("software", "getIssuesForBoardJSIS", ["--boardId", "1"], "issues", False),
    (
        "software",
        "getBoardIssuesForSprintJSIS",
        ["--boardId", "1", "--sprintId", "2"],
        "issues",
        False,
    ),
    ("software", "getIssuesWithoutEpicJSIS", [], "issues", False),
    ("software", "getIssuesForEpicJSIS", ["--epicIdOrKey", "SBX-1"], "issues", False),
    ("software", "getIssuesForSprintJSIS", ["--sprintId", "1"], "issues", False),
]


@pytest.mark.parametrize("document,operation,flags,items,body", TOKEN_CASES)
def test_all_eleven_token_operations_preserve_inputs_and_cap(
    wire, document, operation, flags, items, body
):
    responder = wire[1][document]
    responder.seed(
        operation,
        [
            {items: [1, 2], "nextPageToken": "next", "isLast": False},
            {items: [3, 4], "isLast": True},
        ],
    )
    page_size = ["--field", "maxResults=20"] if body else ["--maxResults", "20"]
    result = invoke(operation, *flags, *page_size, "--all", "--limit", "3")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2, 3]
    assert result.stderr.strip() == "count=3"
    first, second = responder.requests
    if body:
        assert first[1] == second[1] == {}
        assert second[2] == {**first[2], "nextPageToken": "next"}
        assert first[2]["maxResults"] == 20
    else:
        assert second[1] == {**first[1], "nextPageToken": "next"}
        assert first[1]["maxResults"] == 20
        assert first[2] == second[2] is None


def test_default_preserves_one_page_wrapper(wire):
    responder = wire[1]["platform"]
    page = {"issues": [1], "nextPageToken": "unused", "isLast": False}
    responder.seed("searchAndReconsileIssuesUsingJql", [page])
    result = invoke("searchAndReconsileIssuesUsingJql", "--maxResults", "20")
    assert result.exit_code == 0 and json.loads(result.stdout) == page, result.output
    assert len(responder.requests) == 1 and result.stderr == ""


def test_audit_offset_uses_actual_count(wire):
    responder = wire[1]["platform"]
    responder.seed(
        "getAuditRecords",
        [{"records": [1, 2], "total": 3}, {"records": [3], "total": 3}],
    )
    result = invoke(
        "getAuditRecords", "--all", "--parameter-limit", "20", "--filter", "project"
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2, 3]
    assert [r[1] for r in responder.requests] == [
        {"filter": "project", "limit": 20, "offset": 0},
        {"filter": "project", "limit": 20, "offset": 2},
    ]


def test_failed_webhooks_extracts_only_after_and_keeps_original_page_size(wire):
    responder = wire[1]["platform"]
    responder.seed(
        "getFailedWebhooks",
        [
            {
                "values": [1],
                "next": "https://offline.invalid/rest/api/3/webhook/failed?after=42&maxResults=999",
            },
            {"values": [2]},
        ],
    )
    result = invoke("getFailedWebhooks", "--all", "--maxResults", "20")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2]
    assert [r[1] for r in responder.requests] == [
        {"maxResults": 20},
        {"maxResults": 20, "after": 42},
    ]


@pytest.mark.parametrize(
    "link",
    [
        "https://outside.invalid/items?after=42",
        "/items?after=1&after=2",
        "/items?after=bad",
        "/items?cursor=1",
    ],
)
def test_failed_webhook_bad_links_refuse_without_second_request(wire, link):
    responder = wire[1]["platform"]
    responder.seed("getFailedWebhooks", [{"values": [1], "next": link}])
    result = invoke("getFailedWebhooks", "--all")
    assert result.exit_code == 2 and result.stdout == "", result.output
    assert len(responder.requests) == 1


def test_jsm_continues_short_nonfinal_page(wire):
    responder = wire[1]["servicedesk"]
    responder.seed(
        "getServiceDesks",
        [{"values": [1], "isLastPage": False}, {"values": [2], "isLastPage": True}],
    )
    result = invoke("getServiceDesks", "--all", "--parameter-limit", "50")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2]
    assert [r[1] for r in responder.requests] == [
        {"limit": 50, "start": 0},
        {"limit": 50, "start": 1},
    ]


def test_string_typed_offset_preserves_declared_wire_type(wire):
    responder = wire[1]["platform"]
    responder.seed(
        "getNotificationSchemes",
        [{"values": [1], "total": 2}, {"values": [2], "total": 2}],
    )
    result = invoke("getNotificationSchemes", "--all", "--maxResults", "20")
    assert result.exit_code == 0, result.output
    assert [r[1]["startAt"] for r in responder.requests] == ["0", "1"]


@pytest.mark.parametrize(
    "operation,flags",
    [
        ("searchForIssuesUsingJqlPost", ["--field", "jql=project = SBX"]),
        ("suggestedPrioritiesForMappings", []),
    ],
)
def test_body_offset_controls_follow_pages_without_becoming_query_flags(
    wire, operation, flags
):
    responder = wire[1]["platform"]
    field = "issues" if operation == "searchForIssuesUsingJqlPost" else "values"
    responder.seed(operation, [{field: [1], "total": 2}, {field: [2], "total": 2}])
    result = invoke(operation, *flags, "--field", "maxResults=20", "--all")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2]
    first, second = responder.requests
    assert first[1] == second[1] == {}
    assert first[2]["startAt"] == 0
    assert second[2] == {**first[2], "startAt": 1}


@pytest.mark.parametrize(
    "operation,default_size",
    [
        ("bulkGetUsersMigration", 10),
        ("findUsers", 50),
        ("getAllUsersDefault", 50),
        ("getAllUsers", 50),
    ],
)
def test_bare_user_pages_continue_short_pages_and_stop_empty(
    wire, operation, default_size
):
    responder = wire[1]["platform"]
    responder.seed(operation, [[1, 2], [3], []])
    result = invoke(operation, "--all", "--maxResults", "2")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [1, 2, 3]
    assert [r[1] for r in responder.requests] == [
        {"maxResults": 2, "startAt": n} for n in (0, 2, 4)
    ]
    responder.seed(operation, [[]])
    result = invoke(operation, "--all")
    assert result.exit_code == 0, result.output
    assert responder.requests[-1][1] == {"maxResults": default_size, "startAt": 0}


@pytest.mark.parametrize(
    "operation,flags",
    [
        ("findBulkAssignableUsers", ["--projectKeys", "SBX"]),
        ("findAssignableUsers", []),
        ("findUsersWithAllPermissions", ["--permissions", "BROWSE_PROJECTS"]),
        ("findUsersWithBrowsePermission", []),
    ],
)
def test_post_slice_user_filter_refuses_automatic_paging(wire, operation, flags):
    result = invoke(operation, *flags, "--all")
    assert result.exit_code == 2, result.output
    assert "no declared paging contract" in result.stderr
    assert "empty page does not prove exhaustion" in json.loads(result.stderr)["note"]
    assert wire[1]["platform"].requests == []


@pytest.mark.parametrize("operation", ["getAllUsers", "getAllUsersDefault"])
def test_documented_server_cap_refuses_before_transport(wire, operation):
    result = invoke(operation, "--all", "--maxResults", "1001")
    assert result.exit_code == 2, result.output
    assert wire[1]["platform"].requests == []
