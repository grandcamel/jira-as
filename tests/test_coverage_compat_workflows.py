"""Workflow contracts exercised only through registered argv and real Surface."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from as_engine.responder import Responder
from as_engine.transport import Response
from assistant_skills_lib.cache import SkillCache
from click.testing import CliRunner

from jira_as import autocomplete_cache, engine, project_context
from jira_as.autocomplete_cache import AutocompleteCache, InstanceFieldsCache
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager

LINK_TYPE = {
    "id": "1",
    "name": "Blocks",
    "inward": "is blocked by",
    "outward": "blocks",
}
TRANSITION = {"id": "31", "name": "Finish", "to": {"name": "Done"}}


@pytest.fixture
def wire(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network and credential access are forbidden")

    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX,OTHER")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path / "fields"))
    for name in ("JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET"):
        monkeypatch.delenv(name, raising=False)
    for name in (
        "JIRA_AS_CASSETTE",
        "JIRA_AS_RECORD",
        "JIRA_AS_SIMULATION_SEED",
        "JIRA_STORY_POINTS_FIELD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr("requests.sessions.Session.request", denied)
    monkeypatch.setattr("socket.socket.connect", denied)
    monkeypatch.setattr(project_context, "get_skills_root", lambda: tmp_path / "root")
    monkeypatch.setattr(project_context, "_context_cache", {})
    cache = SkillCache("coverage-workflows", cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        autocomplete_cache, "_autocomplete_cache", AutocompleteCache(cache)
    )
    ConfigManager.reset_instance()
    factory = engine.create_surface
    responder = Responder(factory(transport="responder").indexes.get("platform"))

    def surface(**kwargs):
        result = factory(transport="responder")
        result.transport_factory = lambda *_: responder
        return result

    monkeypatch.setattr(engine, "create_surface", surface)
    yield SimpleNamespace(responder=responder, root=tmp_path)
    cache.close()
    ConfigManager.reset_instance()


def invoke(*args):
    return CliRunner().invoke(cli, list(args))


def seed_transition(wire, transitions):
    wire.responder.seed(
        "getIssue",
        [
            {
                "key": "SBX-1",
                "fields": {
                    "status": {"name": "Open"},
                    "issuetype": {"name": "Task"},
                    "project": {"key": "SBX"},
                },
            }
        ],
    )
    wire.responder.seed("getTransitions", [{"transitions": transitions}])


def workflow_context(wire):
    context = wire.root / "root/skills/jira-project-SBX/context"
    context.mkdir(parents=True)
    (context / "workflows.json").write_text(
        json.dumps(
            {
                "by_issue_type": {
                    "Task": {
                        "transitions": {
                            "Open": [{"name": "Begin", "to_status": "In Progress"}],
                            "Done": [{"name": "Reopen", "to_status": "Open"}],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "transitions,choice,message",
    [
        ([], ["--to", "Finish"], "No transitions available"),
        ([TRANSITION], ["--id", "99"], "Transition ID '99' not available"),
    ],
)
def test_unavailable_transition_includes_local_workflow_hint(
    wire, transitions, choice, message
):
    workflow_context(wire)
    seed_transition(wire, transitions)
    result = invoke("lifecycle", "transition", "SBX-1", *choice)
    assert result.exit_code == 1, result.output
    assert message in result.output
    assert "Expected transitions from project context:" in result.output
    assert "Begin" in result.output
    assert "In Progress" in result.output
    assert [r[0] for r in wire.responder.requests] == ["getIssue", "getTransitions"]


def test_transition_preview_includes_options_and_target_context_without_writes(
    wire,
):
    workflow_context(wire)
    seed_transition(wire, [TRANSITION])
    result = invoke(
        "lifecycle",
        "transition",
        "SBX-1",
        "--id",
        "31",
        "--resolution",
        "Fixed",
        "--comment",
        "Ready",
        "--sprint",
        "42",
        "--dry-run",
    )
    assert result.exit_code == 0, result.output
    for text in (
        "Current status: Open",
        "Target status: Done",
        "Resolution: Fixed",
        "Comment: (would add comment)",
        "Sprint: Would move to sprint 42",
        "Reopen",
    ):
        assert text in result.output
    assert [r[0] for r in wire.responder.requests] == ["getIssue", "getTransitions"]


def test_transition_id_sends_custom_fields(wire):
    seed_transition(wire, [TRANSITION])
    wire.responder.seed("doTransition", [Response(204, None)])
    result = invoke(
        "lifecycle",
        "transition",
        "SBX-1",
        "--id",
        "31",
        "--fields",
        '{"customfield_12345": "reviewed"}',
    )
    assert result.exit_code == 0, result.output
    calls = wire.responder.requests
    assert [r[0] for r in calls] == [
        "getIssue",
        "getTransitions",
        "doTransition",
    ]
    assert calls[2][2] == {
        "transition": {"id": "31"},
        "fields": {"customfield_12345": "reviewed"},
    }
    assert "Transitioned SBX-1 to transition 31" in result.output


def test_transition_retries_only_rejected_options_and_preserves_other_fields(wire):
    seed_transition(wire, [TRANSITION])
    rejection = "Field cannot be set. It is not on the appropriate screen."
    wire.responder.seed(
        "doTransition",
        [
            Response(400, {"errors": {"resolution": rejection}}),
            Response(400, {"errors": {"comment": rejection}}),
            Response(204, None),
        ],
    )
    wire.responder.seed("addComment", [{"id": "8"}])
    result = invoke(
        "lifecycle",
        "transition",
        "SBX-1",
        "--to",
        "Finish",
        "--resolution",
        "Fixed",
        "--comment",
        "**Ready**",
        "--fields",
        '{"customfield_12345": "reviewed"}',
    )
    assert result.exit_code == 0, result.output
    calls = wire.responder.requests
    assert [r[0] for r in calls] == [
        "getIssue",
        "getTransitions",
        "doTransition",
        "doTransition",
        "doTransition",
        "addComment",
    ]
    first, second, third = [r[2]["fields"] for r in calls[2:5]]
    assert first["resolution"] == {"name": "Fixed"}
    assert first["comment"]["type"] == "doc"
    assert set(second) == {"comment", "customfield_12345"}
    assert third == {"customfield_12345": "reviewed"}
    assert calls[-1][2]["body"] == first["comment"]
    assert "screen rejected --resolution" in result.stderr
    assert "screen rejected --comment" in result.stderr


@pytest.mark.parametrize("status", [400, 403])
def test_unrelated_transition_failure_never_retries_or_adds_comment(wire, status):
    seed_transition(wire, [TRANSITION])
    wire.responder.seed(
        "doTransition",
        [Response(status, {"errorMessages": ["Workflow policy refusal"]})],
    )
    result = invoke(
        "lifecycle",
        "transition",
        "SBX-1",
        "--to",
        "Finish",
        "--resolution",
        "Fixed",
        "--comment",
        "Ready",
        "--sprint",
        "42",
    )
    assert result.exit_code == 1, result.output
    assert "Workflow policy refusal" in result.output
    assert "screen rejected" not in result.output
    assert [r[0] for r in wire.responder.requests] == [
        "getIssue",
        "getTransitions",
        "doTransition",
    ]


@pytest.mark.parametrize("transitions", [[], [TRANSITION]])
def test_transitions_text_handles_empty_and_available_lists(wire, transitions):
    wire.responder.seed("getTransitions", [{"transitions": transitions}])
    result = invoke("lifecycle", "transitions", "SBX-1")
    assert result.exit_code == 0, result.output
    assert [r[0] for r in wire.responder.requests] == ["getTransitions"]
    if transitions:
        assert "Finish" in result.output
        assert "Done" in result.output
    else:
        assert "No transitions available for SBX-1" in result.output


@pytest.mark.parametrize("kind", ["role", "group"])
def test_comment_visibility_reaches_request_and_confirmation(wire, kind):
    visibility = {"type": kind, "value": "Reviewers"}
    wire.responder.seed("addComment", [{"id": "8", "visibility": visibility}])
    result = invoke(
        "collaborate",
        "comment",
        "add",
        "SBX-1",
        "--body",
        "Internal note",
        "--visibility-" + kind,
        "Reviewers",
    )
    assert result.exit_code == 0, result.output
    assert [r[0] for r in wire.responder.requests] == ["addComment"]
    assert wire.responder.requests[0][2]["visibility"] == visibility
    assert wire.responder.requests[0][2]["body"]["content"][0]["content"] == [
        {"type": "text", "text": "Internal note"}
    ]
    assert f"Visibility: Reviewers ({kind})" in result.output


@pytest.mark.parametrize("visibility", [None, {"type": "role", "value": "Reviewers"}])
@pytest.mark.parametrize("output", ["text", "json"])
def test_comment_by_id_preserves_body_and_visibility(wire, visibility, output):
    comment = {
        "id": "8",
        "body": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Saved note"}],
                }
            ],
        },
    }
    if visibility:
        comment["visibility"] = visibility
    wire.responder.seed("getComment", [comment])
    result = invoke(
        "collaborate",
        "comment",
        "list",
        "SBX-1",
        "--id",
        "8",
        "--output",
        output,
    )
    assert result.exit_code == 0, result.output
    assert [r[0] for r in wire.responder.requests] == ["getComment"]
    assert wire.responder.requests[0][1]["id"] == "8"
    if output == "json":
        assert json.loads(result.stdout) == comment
    else:
        assert "Saved note" in result.output
        assert "Author: Unknown" in result.output
        expected = "role - Reviewers" if visibility else "Visibility: Public"
        assert expected in result.output


@pytest.mark.parametrize("empty", [True, False])
def test_comment_list_paging_and_empty_text(wire, empty):
    comments = [] if empty else [{"id": "8", "body": "Saved note"}]
    wire.responder.seed(
        "getComments", [{"comments": comments, "total": 0 if empty else 3}]
    )
    result = invoke(
        "collaborate",
        "comment",
        "list",
        "SBX-1",
        "--limit",
        "1",
        "--offset",
        "2",
        "--order",
        "asc",
    )
    assert result.exit_code == 0, result.output
    assert len(wire.responder.requests) == 1
    _, params, _ = wire.responder.requests[0]
    assert params["maxResults"] == 1
    assert params["startAt"] == 2
    assert params["orderBy"] == "+created"
    assert ("No comments found." if empty else "Showing 1 of 3.") in result.output


@pytest.mark.parametrize(
    "args,message",
    [
        (["--time", " "], "Time spent cannot be empty"),
        (["--time", "bad"], "Invalid time format"),
        (["--time", "1h", "--started", "not-a-date"], "not-a-date"),
        (
            ["--time", "1h", "--visibility-type", "role"],
            "--visibility-value is required",
        ),
        (
            ["--time", "1h", "--visibility-value", "Reviewers"],
            "--visibility-type is required",
        ),
    ],
)
def test_worklog_invalid_inputs_refuse_before_transport(wire, args, message):
    result = invoke("time", "log", "SBX-1", *args)
    assert result.exit_code == 1, result.output
    assert message in result.output
    assert wire.responder.requests == []


@pytest.mark.parametrize(
    "adjust,option,parameter,kind",
    [
        ("new", "--new-estimate", "newEstimate", "role"),
        ("manual", "--reduce-by", "reduceBy", "group"),
    ],
)
def test_worklog_date_visibility_and_estimate_parameters(
    wire, adjust, option, parameter, kind
):
    response = {
        "id": "8",
        "timeSpent": "1h 30m",
        "timeSpentSeconds": 5400,
        "started": "2026-09-01T00:00:00.000+0000",
        "comment": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Review"}],
                }
            ],
        },
        "visibility": {"type": kind, "value": "Reviewers"},
    }
    wire.responder.seed("addWorklog", [response])
    result = invoke(
        "time",
        "log",
        "SBX-1",
        "--time",
        "1h 30m",
        "--started",
        "2026-09-01",
        "--comment",
        "**Review**",
        "--adjust-estimate",
        adjust,
        option,
        "2h",
        "--visibility-type",
        kind,
        "--visibility-value",
        "Reviewers",
    )
    assert result.exit_code == 0, result.output
    assert len(wire.responder.requests) == 1
    operation, params, body = wire.responder.requests[0]
    assert operation == "addWorklog"
    assert params["adjustEstimate"] == adjust
    assert params[parameter] == "2h"
    assert ({"newEstimate", "reduceBy"} - {parameter}).isdisjoint(params)
    assert body["timeSpentSeconds"] == 5400
    assert body["started"].startswith("2026-09-01T00:00:00")
    assert body["visibility"] == {
        "type": kind,
        "value": "Reviewers",
        "identifier": "Reviewers",
    }
    assert body["comment"]["content"][0]["content"][0]["marks"] == [{"type": "strong"}]
    assert "5400 seconds" in result.output
    assert f"Visibility: {kind} = Reviewers" in result.output


@pytest.mark.parametrize("points,output", [(0, "text"), (2.5, "json")])
def test_estimate_uses_cached_instance_field_and_zero_clears(wire, points, output):
    InstanceFieldsCache().write(
        [
            {
                "id": "customfield_12345",
                "name": "Story Points",
                "schema": {"type": "number"},
            }
        ]
    )
    wire.responder.seed("editIssue", [Response(204, None)])
    result = invoke(
        "agile",
        "estimate",
        "SBX-1",
        "--points",
        str(points),
        "--output",
        output,
    )
    assert result.exit_code == 0, result.output
    assert [r[0] for r in wire.responder.requests] == ["editIssue"]
    assert wire.responder.requests[0][2] == {
        "fields": {"customfield_12345": None if points == 0 else points}
    }
    if output == "json":
        assert json.loads(result.stdout) == {
            "updated": 1,
            "issues": ["SBX-1"],
            "points": points,
        }
    else:
        assert "Story points: cleared" in result.output


@pytest.mark.parametrize("status,hint", [(400, False), (403, True), (404, True)])
def test_explicit_native_link_failure_preserves_error_and_hint(wire, status, hint):
    wire.responder.seed("getIssueLinkTypes", [{"issueLinkTypes": [LINK_TYPE]}])
    wire.responder.seed(
        "linkIssues", [Response(status, {"errorMessages": ["Link refused"]})]
    )
    result = invoke(
        "relationships",
        "link",
        "SBX-1",
        "--type",
        "blocks",
        "--to",
        "OTHER-2",
    )
    assert result.exit_code == 1, result.output
    assert "Link refused" in result.output
    assert ("Hint: a native link" in result.stderr) is hint
    assert [r[0] for r in wire.responder.requests] == [
        "getIssueLinkTypes",
        "linkIssues",
    ]


def test_explicit_native_link_preview_uses_metadata_direction(wire):
    wire.responder.seed("getIssueLinkTypes", [{"issueLinkTypes": [LINK_TYPE]}])
    result = invoke(
        "relationships",
        "link",
        "SBX-1",
        "--type",
        "blocks",
        "--to",
        "OTHER-2",
        "--dry-run",
    )
    assert result.exit_code == 0, result.output
    assert "Would create link: SBX-1 blocks OTHER-2" in result.output
    assert [r[0] for r in wire.responder.requests] == ["getIssueLinkTypes"]


@pytest.mark.parametrize("endpoint", ["inwardIssue", "outwardIssue"])
def test_unlink_preview_reports_matching_target_without_delete(wire, endpoint):
    link = {"id": "8", "type": LINK_TYPE, endpoint: {"key": "OTHER-2"}}
    wire.responder.seed(
        "getIssue", [{"key": "SBX-1", "fields": {"issuelinks": [link]}}]
    )
    result = invoke("relationships", "unlink", "SBX-1", "OTHER-2", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "Would remove 1 link(s)" in result.output
    assert "OTHER-2 (Blocks)" in result.output
    assert [r[0] for r in wire.responder.requests] == ["getIssue"]


@pytest.mark.parametrize("output", ["text", "json"])
def test_link_types_filter_matches_direction_and_handles_no_matches(wire, output):
    wire.responder.seed("getIssueLinkTypes", [{"issueLinkTypes": [LINK_TYPE]}] * 2)
    first = invoke(
        "relationships", "link-types", "--filter", "blocked", "--output", output
    )
    second = invoke(
        "relationships", "link-types", "--filter", "absent", "--output", output
    )
    assert first.exit_code == second.exit_code == 0
    assert [r[0] for r in wire.responder.requests] == ["getIssueLinkTypes"] * 2
    if output == "json":
        assert json.loads(first.stdout) == [LINK_TYPE]
        assert json.loads(second.stdout) == []
    else:
        assert "Blocks" in first.output
        assert "Total: 1 link type(s)" in first.output
        assert "No link types found." in second.output


@pytest.mark.parametrize("output", ["text", "json"])
def test_get_links_empty_response(wire, output):
    wire.responder.seed("getIssue", [{"key": "SBX-1", "fields": {}}])
    result = invoke("relationships", "get-links", "SBX-1", "--output", output)
    assert result.exit_code == 0, result.output
    assert wire.responder.requests[0][1]["fields"] == ["issuelinks"]
    if output == "json":
        assert json.loads(result.stdout) == []
    else:
        assert "No links found for SBX-1" in result.output
