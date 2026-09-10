"""Cache persistence and discovery reports through current root CLI callbacks."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from as_engine.responder import Responder
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as import engine
from jira_as.cache import JiraCache
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def wire(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network and credential access are forbidden")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr("requests.sessions.Session.request", denied)
    monkeypatch.setattr("socket.socket.connect", denied)
    monkeypatch.setenv("JIRA_STORY_POINTS_FIELD", "customfield_10016")
    for name in ("JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET", "JIRA_AS_CASSETTE"):
        monkeypatch.delenv(name, raising=False)
    ConfigManager.reset_instance()
    factory = engine.create_surface
    responder = Responder(factory(transport="responder").indexes.get("platform"))

    def surface(**kwargs):
        result = factory(transport="responder")
        result.scope_allowlist = ("SBX",)
        result.scope_allow_site = True
        result.transport_factory = lambda *_: responder
        return result

    monkeypatch.setattr(engine, "create_surface", surface)
    yield SimpleNamespace(responder=responder, root=tmp_path, cache=JiraCache())
    ConfigManager.reset_instance()


def invoke(*args, expected=0, input=None):
    result = CliRunner().invoke(cli, ["ops", *args], input=input)
    assert result.exit_code == expected, (result.output, result.exception)
    return result


def entries(wire):
    for category, key in [
        ("issue", "drop-one"),
        ("issue", "keep"),
        ("project", "drop-two"),
    ]:
        wire.cache.set(key, {"key": key}, category=category)


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("output", ["text", "json"])
def test_cache_status_reads_real_persisted_categories(wire, populated, output):
    if populated:
        entries(wire)
    result = invoke(
        "cache-status", *(["--json"] if output == "json" else ["--verbose"])
    )
    if output == "json":
        data = json.loads(result.output)
        assert data["entry_count"] == (3 if populated else 0)
        assert set(data["by_category"]) == (
            {"issue", "project"} if populated else set()
        )
    else:
        assert f"Entries: {3 if populated else 0}" in result.output
        assert (
            "issue: 2 entries" if populated else "No cached entries."
        ) in result.output
    assert wire.responder.requests == []


@pytest.mark.parametrize(
    "selection,remaining",
    [
        (["--category", "issue", "--key", "drop-one"], 2),
        (["--category", "issue", "--pattern", "drop-*"], 2),
        (["--pattern", "drop-*"], 1),
        (["--category", "issue"], 1),
        ([], 0),
    ],
)
def test_cache_clear_preview_cancel_and_confirm_preserve_selection(
    wire, selection, remaining
):
    entries(wire)
    preview = invoke("cache-clear", *selection, "--dry-run", "--json")
    assert json.loads(preview.output)["dry_run"]
    assert wire.cache.get_stats().entry_count == 3
    assert "Cancelled." in invoke("cache-clear", *selection, input="n\n").output
    assert wire.cache.get_stats().entry_count == 3
    applied = invoke("cache-clear", *selection, input="y\n")
    assert f"Cleared {3 - remaining} cache entries." in applied.output
    assert wire.cache.get_stats().entry_count == remaining
    if remaining == 2:
        assert wire.cache.get("keep", category="issue") == {"key": "keep"}
        assert wire.cache.get("drop-two", category="project") == {"key": "drop-two"}
    assert wire.responder.requests == []


def test_cache_clear_key_requires_category_and_force_json_reports_counts(wire):
    entries(wire)
    assert (
        "--key requires --category"
        in invoke("cache-clear", "--key", "keep", expected=1).output
    )
    assert wire.cache.get_stats().entry_count == 3
    result = invoke("cache-clear", "--category", "issue", "--force", "--json")
    assert json.loads(result.output)["cleared_count"] == 2
    preview = invoke("cache-clear", "--dry-run")
    assert "DRY RUN: Would clear all cache entries" in preview.output


@pytest.mark.parametrize(
    "args,message",
    [
        ([], "At least one warming option"),
        (["--users"], "requires --project and --issue-key"),
        (["--users", "--project", "SBX", "--issue-key", "OTHER-1"], "must belong"),
    ],
)
def test_cache_warm_invalid_scope_refuses_without_requests(wire, args, message):
    assert message in invoke("cache-warm", *args, expected=1).output
    assert wire.responder.requests == []


@pytest.mark.parametrize("output", ["text", "json"])
def test_cache_warm_fields_and_users_persist_canonical_keys(wire, output):
    wire.responder.seed("getFields", [[{"id": "summary", "name": "Summary"}]])
    wire.responder.seed("getIssueAllTypes", [[{"id": "100", "name": "Task"}]])
    wire.responder.seed("getPriorities", [[{"id": "1", "name": "High"}]])
    wire.responder.seed(
        "findAssignableUsers", [[{"accountId": "reviewer", "displayName": "Reviewer"}]]
    )
    result = invoke(
        "cache-warm",
        "--fields",
        "--users",
        "--project",
        "SBX",
        "--issue-key",
        "SBX-1",
        *(["--json"] if output == "json" else []),
    )
    if output == "json":
        data = json.loads(result.output)
        assert data["total_cached"] == 4
        assert data["warmed"] == ["fields", "issue_types", "priorities", "SBX-1"]
    else:
        assert "Cached 4 items" in result.output
    assert (
        wire.cache.get(wire.cache.generate_key("field", "summary"), category="field")[
            "name"
        ]
        == "Summary"
    )
    assert (
        wire.cache.get(
            wire.cache.generate_key("user", "SBX-1", "reviewer"), category="user"
        )["accountId"]
        == "reviewer"
    )
    assert [r[0] for r in wire.responder.requests] == [
        "getFields",
        "getIssueAllTypes",
        "getPriorities",
        "findAssignableUsers",
    ]


def test_cache_warm_transport_refusal_leaves_no_field_rows(wire):
    wire.responder.seed(
        "getFields", [Response(403, {"errorMessages": ["Metadata denied"]})]
    )
    result = invoke("cache-warm", "--fields", expected=1)
    assert "Metadata denied" in result.output
    assert wire.cache.get_stats().entry_count == 0
    assert [r[0] for r in wire.responder.requests] == ["getFields"]


def discovery(wire, rows):
    wire.responder.seed(
        "getProject", [{"key": "SBX", "name": "Local project", "simplified": True}]
    )
    wire.responder.seed(
        "getAllStatuses",
        [[{"id": "100", "name": "Task", "statuses": [{"name": "Open"}]}]],
    )
    wire.responder.seed("getProjectComponents", [[{"name": "Core"}]])
    wire.responder.seed("getProjectVersions", [[]])
    wire.responder.seed(
        "searchAndReconsileIssuesUsingJql", [{"issues": rows, "isLast": True}]
    )


@pytest.mark.parametrize("parents", [0, 1, 2])
@pytest.mark.parametrize("output", ["text", "json"])
def test_discover_project_reports_real_sample_distributions_and_hierarchy(
    wire, parents, output
):
    rows = [
        {
            "key": "SBX-1",
            "fields": {
                "issuetype": {"name": "Task"},
                "assignee": {"accountId": "reviewer", "displayName": "Reviewer"},
                "labels": ["triaged"],
                "components": [{"name": "Core"}],
                "priority": {"name": "High"},
                "customfield_10016": 0,
                "status": {"name": "Open"},
            },
        },
        {
            "key": "SBX-2",
            "fields": {
                "issuetype": {"name": "Task"},
                "assignee": None,
                "labels": [],
                "components": [],
                "customfield_10016": 4,
            },
        },
    ]
    for row in rows[:parents]:
        row["fields"]["parent"] = {
            "key": "SBX-9",
            "fields": {"issuetype": {"name": "Epic"}},
        }
    discovery(wire, rows)
    result = invoke(
        "discover-project",
        "SBX",
        "--sample-size",
        "2",
        "--days",
        "7",
        "--output",
        output,
        *(["--verbose"] if output == "text" else []),
    )
    if output == "json":
        patterns = json.loads(result.output)["patterns"]
        assert patterns["sample_size"] == 2
        assert patterns["by_issue_type"]["Task"]["story_points"] == {"avg": 2.0}
        assert patterns["field_fill_rates"]["assignee"] == {
            "filled": 1,
            "total": 2,
            "percentage": 50.0,
        }
        assert patterns["parent_hierarchy"]["issues_with_parent"] == parents
        assert patterns["value_distributions"]["priority"]["High"]["count"] == 1
        assert patterns["common_labels"] == ["triaged"]
    else:
        for text in (
            "Project: SBX",
            "Sampled Issues: 2",
            "Top Assignees: Reviewer",
            "Common Labels: triaged",
            "Field Fill Rates:",
            "Value Distributions:",
            f"Issues with a parent: {parents}/2",
            "Found 1 issue types with patterns",
        ):
            assert text in result.output
        hint = ["appears to be flat", "--parent is optional", "set --parent"][parents]
        assert hint in result.output
    call = wire.responder.requests[-1]
    assert call[0] == "searchAndReconsileIssuesUsingJql"
    assert 'project = "SBX"' in call[1]["jql"]
    assert "customfield_10016" in call[1]["fields"]
    assert len(wire.responder.requests) == 5


def test_discover_empty_sample_and_invalid_bounds(wire):
    for option in ("--sample-size", "--days"):
        assert (
            "must be positive"
            in invoke("discover-project", "SBX", option, "0", expected=2).output
        )
    assert wire.responder.requests == []
    discovery(wire, [])
    result = invoke("discover-project", "SBX")
    assert "Sampled Issues: 0" in result.output
    assert "Field Fill Rates:" not in result.output
    assert "Parent Hierarchy:" not in result.output
