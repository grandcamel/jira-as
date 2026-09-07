"""Contract decisions exercised at the argv and real seeded responder seams."""

from copy import deepcopy

import pytest
from as_engine.responder import Responder
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as import engine
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def wire(monkeypatch, tmp_path):
    from pathlib import Path

    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX,OTHER")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    ConfigManager.reset_instance()
    surface = engine.create_surface(transport="responder")
    responder = Responder(surface.indexes.get("platform"))
    surface.transport_factory = lambda *_: responder
    from jira_as.cli.commands import api_cmds

    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)
    yield responder
    ConfigManager.reset_instance()


def test_compat_search_ordering_get(wire):
    wire.seed("searchAndReconsileIssuesUsingJql", [{"issues": [], "isLast": True}])
    query = "project = SBX AND statusCategory != Done ORDER BY key ASC"
    result = CliRunner().invoke(cli, ["search", "query", query])
    assert result.exit_code == 0, result.output
    assert wire.requests[-1][1]["jql"] == query


def test_compat_search_ordering_post(wire, tmp_path):
    wire.seed("searchAndReconsileIssuesUsingJqlPost", [{"issues": [], "isLast": True}])
    body = tmp_path / "query.json"
    body.write_text('{"jql":"project=SBX order by created desc"}')
    result = CliRunner().invoke(
        cli,
        [
            "api",
            "call",
            "searchAndReconsileIssuesUsingJqlPost",
            "--project",
            "SBX",
            "--body",
            "@" + str(body),
        ],
    )
    assert result.exit_code == 0, result.output
    assert wire.requests[-1][2]["jql"] == "project=SBX order by created desc"


def test_compat_cross_project_link_scope(wire):
    wire.seed(
        "getIssueLinkTypes",
        [
            {
                "issueLinkTypes": [
                    {
                        "id": "1",
                        "name": "Blocks",
                        "inward": "blocked by",
                        "outward": "blocks",
                    }
                ]
            }
        ],
    )
    wire.seed("linkIssues", [Response(201, {})])
    result = CliRunner().invoke(
        cli, ["relationships", "link", "SBX-1", "--type", "Blocks", "--to", "OTHER-2"]
    )
    assert result.exit_code == 0, result.output
    assert [r[0] for r in wire.requests] == ["getIssueLinkTypes", "linkIssues"]
    assert {
        wire.requests[-1][2][k]["key"] for k in ("inwardIssue", "outwardIssue")
    } == {"SBX-1", "OTHER-2"}


def test_compat_transition_comment_conversion(wire):
    wire.seed(
        "getIssue",
        [
            {
                "key": "SBX-1",
                "fields": {"status": {"name": "Open"}, "issuetype": {"name": "Task"}},
            }
        ],
    )
    wire.seed(
        "getTransitions",
        [{"transitions": [{"id": "31", "name": "Done", "to": {"name": "Done"}}]}],
    )
    wire.seed(
        "doTransition",
        [
            Response(
                400,
                {
                    "errors": {
                        "comment": "Field cannot be set. It is not on the appropriate screen."
                    }
                },
            ),
            Response(204, None),
        ],
    )
    wire.seed("addComment", [{"id": "10"}])
    result = CliRunner().invoke(
        cli,
        ["lifecycle", "transition", "SBX-1", "--to", "Done", "--comment", "**ready**"],
    )
    assert result.exit_code == 0, result.output
    assert "screen rejected --comment" in result.stderr
    assert [r[0] for r in wire.requests] == [
        "getIssue",
        "getTransitions",
        "doTransition",
        "doTransition",
        "addComment",
    ]
    first, second, fallback = wire.requests[-3:]
    assert first[2]["fields"]["comment"]["type"] == "doc"
    assert "comment" not in second[2].get("fields", {})
    assert fallback[2]["body"]["content"][0]["content"][0]["marks"] == [
        {"type": "strong"}
    ]


def test_compat_link_comment_conversion(wire):
    wire.seed("getIssueLinkTypes", [{"issueLinkTypes": [{"name": "Blocks"}]}])
    wire.seed("linkIssues", [Response(201, {})])
    result = CliRunner().invoke(
        cli,
        [
            "relationships",
            "link",
            "SBX-1",
            "--type",
            "Blocks",
            "--to",
            "OTHER-2",
            "--comment",
            "**ready**",
        ],
    )
    assert result.exit_code == 0, result.output
    assert wire.requests[-1][2]["comment"]["body"]["content"][0]["content"][0][
        "marks"
    ] == [{"type": "strong"}]


@pytest.mark.parametrize(
    "links",
    [
        [],
        [{"id": "8", "outwardIssue": {"key": "OTHER-99"}, "type": {"name": "Blocks"}}],
        [
            {
                "id": "8",
                "outwardIssue": {"key": "OTHER-2"},
                "inwardIssue": {"key": "THIRD-3"},
                "type": {"name": "Blocks"},
            }
        ],
        [{"id": "8", "outwardIssue": {"key": "OTHER-2"}, "type": {"name": "Blocks"}}]
        * 2,
    ],
)
def test_unlink_requires_unambiguous_matching_link_before_numeric_delete(wire, links):
    wire.seed("getIssue", [{"key": "SBX-1", "fields": {"issuelinks": deepcopy(links)}}])
    result = CliRunner().invoke(cli, ["relationships", "unlink", "SBX-1", "OTHER-2"])
    assert result.exit_code == 1, result.output
    assert [r[0] for r in wire.requests] == ["getIssue"]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 500])
def test_contract_http_errors_keep_legacy_exit_one(wire, status):
    wire.seed("getIssue", [Response(status, {"errorMessages": ["Fixture refusal"]})])
    result = CliRunner().invoke(cli, ["issue", "get", "SBX-1"])
    assert result.exit_code == 1
    assert "Fixture refusal" in result.output


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("body_format", ["text", "adf", "markdown"])
def test_comment_sources_preserve_explicit_format_and_newlines(
    wire, tmp_path, source, body_format
):
    import json

    adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Already ADF"}]}
        ],
    }
    if body_format == "adf":
        text = json.dumps(adf)
    elif body_format == "text":
        text = "**literal**\\n stays literal\r\nsecond line"
    else:
        text = "## Resolution\n\nDone with **care**.\n\n1. Checked [dashboard](https://example.test)\n"
    args = ["collaborate", "comment", "add", "SBX-1", "--format", body_format]
    if source == "file":
        path = tmp_path / "comment.txt"
        path.write_bytes(text.encode())
        args += ["--body-file", str(path)]
    else:
        args += ["--body-stdin"]
    wire.seed("addComment", [{"id": "123"}])
    result = CliRunner().invoke(cli, args, input=text if source == "stdin" else None)
    assert result.exit_code == 0, result.output
    sent = wire.requests[-1][2]["body"]
    if body_format == "adf":
        assert sent == adf
    elif body_format == "text":
        assert [row["content"][0]["text"] for row in sent["content"]] == [
            "**literal**\\n stays literal\r",
            "second line",
        ]
        assert "marks" not in sent["content"][0]["content"][0]
    else:
        assert [row["type"] for row in sent["content"]] == [
            "heading",
            "paragraph",
            "orderedList",
        ]
        assert any(
            node.get("marks") == [{"type": "strong"}]
            for node in sent["content"][1]["content"]
        )
        link = sent["content"][2]["content"][0]["content"][0]["content"][1]
        assert link["marks"] == [
            {"type": "link", "attrs": {"href": "https://example.test"}}
        ]


def test_markdown_file_and_stdin_have_identical_wire_bodies(wire, tmp_path):
    text = "## Resolution\n\nDone with **care**.\n"
    path = tmp_path / "comment.md"
    path.write_bytes(text.encode())
    wire.seed("addComment", [{"id": "1"}, {"id": "2"}])
    prefix = ["collaborate", "comment", "add", "SBX-1", "--format", "markdown"]
    first = CliRunner().invoke(cli, prefix + ["--body-file", str(path)])
    second = CliRunner().invoke(cli, prefix + ["--body-stdin"], input=text)
    assert first.exit_code == second.exit_code == 0
    assert wire.requests[0][2] == wire.requests[1][2]


@pytest.mark.parametrize(
    "argv,operation,response",
    [
        (
            ["lifecycle", "transitions", "SBX-1", "--output", "json"],
            "getTransitions",
            {"transitions": [{"id": "1", "name": "Done", "to": {"name": "Done"}}]},
        ),
        (
            ["search", "query", "project=SBX", "--output", "json"],
            "searchAndReconsileIssuesUsingJql",
            {"issues": [], "total": 0},
        ),
        (
            ["time", "log", "SBX-1", "--time", "2h", "--output", "json"],
            "addWorklog",
            {"id": "12345", "timeSpentSeconds": 7200},
        ),
    ],
)
def test_legacy_json_options_preserve_response_data(wire, argv, operation, response):
    import json

    wire.seed(operation, [response])
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == response.get("transitions", response)


def test_create_self_uses_bounded_identity_lookup(wire):
    wire.seed("getCurrentUser", [{"accountId": "fixture-user"}])
    wire.seed(
        "createIssue",
        [
            {
                "id": "1",
                "key": "SBX-1",
                "self": "https://example.test/rest/api/3/issue/1",
            }
        ],
    )
    result = CliRunner().invoke(
        cli,
        [
            "issue",
            "create",
            "--project",
            "SBX",
            "--type",
            "Task",
            "--summary",
            "Fixture",
            "--assignee",
            "self",
        ],
    )
    assert result.exit_code == 0, result.output
    assert [request[0] for request in wire.requests] == [
        "getCurrentUser",
        "createIssue",
    ]
    assert wire.requests[-1][2]["fields"]["assignee"] == {"accountId": "fixture-user"}
    refused = CliRunner().invoke(cli, ["api", "call", "getCurrentUser"])
    assert refused.exit_code == 4, refused.output
    assert len(wire.requests) == 2


@pytest.mark.parametrize("source,target", [("SBX-1", "OTHER-2"), ("sbx-1", "other-2")])
def test_unlink_normalizes_both_explicit_keys_before_matching_proof(
    wire, source, target
):
    wire.seed(
        "getIssue",
        [
            {
                "key": "SBX-1",
                "fields": {
                    "issuelinks": [
                        {
                            "id": "123",
                            "type": {"name": "Blocks"},
                            "outwardIssue": {"key": "OTHER-2"},
                        }
                    ]
                },
            }
        ],
    )
    wire.seed("deleteIssueLink", [Response(204, None)])
    result = CliRunner().invoke(cli, ["relationships", "unlink", source, target])
    assert result.exit_code == 0, result.output
    assert [request[0] for request in wire.requests] == ["getIssue", "deleteIssueLink"]


def test_allowed_legacy_mock_setting_uses_responder_for_contract_get(wire, monkeypatch):
    monkeypatch.delenv("JIRA_AS_TRANSPORT")
    monkeypatch.setenv("JIRA_MOCK_MODE", "true")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "DEMO")
    ConfigManager.reset_instance()
    factory = engine.create_surface

    def create_surface(**options):
        assert options == {"transport": "responder"}
        return factory(**options)

    monkeypatch.setattr(engine, "create_surface", create_surface)
    wire.seed("getIssue", [{"key": "DEMO-85", "fields": {"summary": "Fixture"}}])
    result = CliRunner().invoke(cli, ["issue", "get", "DEMO-85"])
    assert result.exit_code == 0, result.output
    assert "DEMO-85" in result.output
    assert wire.requests[0][0] == "getIssue"
    assert wire.requests[0][1]["issueIdOrKey"] == "DEMO-85"
