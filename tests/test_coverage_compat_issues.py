"""Issue contracts through root argv, local context files and indexed transport."""

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
from jira_as.cli.commands import issue_cmds
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


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
        "JIRA_EPIC_LINK_FIELD",
        "JIRA_SPRINT_FIELD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr("requests.sessions.Session.request", denied)
    monkeypatch.setattr("socket.socket.connect", denied)
    monkeypatch.setattr(project_context, "get_skills_root", lambda: tmp_path / "root")
    monkeypatch.setattr(project_context, "_context_cache", {})
    cache = SkillCache("coverage-issues", cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        autocomplete_cache, "_autocomplete_cache", AutocompleteCache(cache)
    )
    monkeypatch.setattr(
        issue_cmds, "__file__", str(tmp_path / "src/jira_as/cli/commands/issue_cmds.py")
    )
    monkeypatch.setattr(
        issue_cmds,
        "resources",
        SimpleNamespace(files=lambda _: tmp_path / "packaged-templates"),
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


def create(*args):
    return invoke(
        "issue",
        "create",
        "--project",
        "SBX",
        "--type",
        "Task",
        "--summary",
        "Explicit summary",
        *args,
    )


def settings(wire, project):
    (wire.root / "settings.local.json").write_text(
        json.dumps({"jira": {"projects": {"SBX": project}}}), encoding="utf-8"
    )


def document(text):
    return {
        "version": 1,
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


@pytest.mark.parametrize("mode", ["defaults", "explicit", "disabled"])
def test_create_merges_local_project_defaults_or_bypasses_them(wire, mode):
    settings(wire, {"agile_fields": {"story_points": "customfield_10016"}})
    skill = wire.root / "root/skills/jira-project-SBX"
    skill.mkdir(parents=True)
    (skill / "defaults.json").write_text(
        json.dumps(
            {
                "global": {
                    "priority": "Medium",
                    "assignee": "default-account",
                    "labels": ["global"],
                    "components": ["Core"],
                    "story_points": 3,
                },
                "by_issue_type": {
                    "Task": {
                        "priority": "High",
                        "labels": ["task"],
                        "components": ["UI"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    args = ["--dry-run", "--output", "json"]
    if mode == "explicit":
        args += [
            "--priority",
            "Low",
            "--assignee",
            "explicit-account",
            "--labels",
            "explicit",
            "--components",
            "API",
            "--story-points",
            "5",
        ]
    elif mode == "disabled":
        args += ["--no-defaults"]
    result = create(*args)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    fields = payload["fields"]
    assert fields["summary"] == "Explicit summary"
    assert wire.responder.requests == []
    if mode == "defaults":
        assert fields["priority"] == {"name": "High"}
        assert fields["assignee"] == {"accountId": "default-account"}
        assert set(fields["labels"]) == {"global", "task"}
        assert {row["name"] for row in fields["components"]} == {"Core", "UI"}
        assert fields["customfield_10016"] == 3
        assert set(payload["defaults_applied"]) == {
            "priority",
            "assignee",
            "labels",
            "components",
            "story_points",
        }
    elif mode == "explicit":
        assert fields["priority"] == {"name": "Low"}
        assert fields["assignee"] == {"accountId": "explicit-account"}
        assert fields["labels"] == ["explicit"]
        assert fields["components"] == [{"name": "API"}]
        assert fields["customfield_10016"] == 5
        assert "defaults_applied" not in payload
    else:
        assert fields == {
            "project": {"key": "SBX"},
            "issuetype": {"name": "Task"},
            "summary": "Explicit summary",
        }
        assert "defaults_applied" not in payload


@pytest.mark.parametrize("location", ["packaged", "primary", "fallback"])
def test_create_reads_template_and_explicit_values_win(wire, location):
    relative = {
        "packaged": "packaged-templates",
        "primary": "src/skills/jira-issue/assets/templates",
        "fallback": "plugins/jira-as/skills/jira-issue/assets/templates",
    }[location]
    path = wire.root / relative / "task_template.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "fields": {
                    "summary": "Template summary",
                    "labels": ["template"],
                    "environment": "Template environment",
                    "customfield_12345": 7,
                }
            }
        ),
        encoding="utf-8",
    )
    result = create("--template", "task", "--dry-run", "--output", "json")
    assert result.exit_code == 0, result.output
    fields = json.loads(result.stdout)["fields"]
    assert fields["summary"] == "Explicit summary"
    assert fields["labels"] == ["template"]
    assert fields["customfield_12345"] == 7
    assert fields["environment"] == document("Template environment")
    assert wire.responder.requests == []


def test_missing_template_refuses_without_creation(wire):
    result = create("--template", "bug")
    assert result.exit_code == 1, result.output
    assert "Template not found: bug" in result.output
    assert wire.responder.requests == []


@pytest.mark.parametrize(
    "assignee,expected",
    [
        ("fixture-account", {"accountId": "fixture-account"}),
        ("assignee@example.test", {"emailAddress": "assignee@example.test"}),
    ],
)
def test_create_sends_optional_fields_and_cached_textarea(wire, assignee, expected):
    settings(
        wire,
        {
            "agile_fields": {
                "story_points": "customfield_10016",
                "epic_link": "customfield_10014",
            }
        },
    )
    InstanceFieldsCache().write(
        [
            {
                "id": "customfield_12345",
                "name": "Investigation",
                "schema": {
                    "type": "string",
                    "custom": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
                },
            }
        ]
    )
    wire.responder.seed("createIssue", [{"key": "SBX-9", "id": "9"}])
    result = create(
        "--assignee",
        assignee,
        "--description",
        "**Description**",
        "--priority",
        "High",
        "--labels",
        "one, two",
        "--components",
        "Core, UI",
        "--story-points",
        "3",
        "--epic",
        "SBX-2",
        "--parent",
        "SBX-3",
        "--estimate",
        "2h",
        "--custom-fields",
        json.dumps({"customfield_12345": "**Investigate**", "environment": "Plain"}),
        "--output",
        "json",
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["key"] == "SBX-9"
    assert [r[0] for r in wire.responder.requests] == ["createIssue"]
    fields = wire.responder.requests[0][2]["fields"]
    assert fields["assignee"] == expected
    assert fields["priority"] == {"name": "High"}
    assert fields["labels"] == ["one", "two"]
    assert fields["components"] == [{"name": "Core"}, {"name": "UI"}]
    assert fields["parent"] == {"key": "SBX-3"}
    assert fields["customfield_10014"] == "SBX-2"
    assert fields["customfield_10016"] == 3
    assert fields["timetracking"] == {"originalEstimate": "2h"}
    assert fields["environment"] == document("Plain")
    for name in ("description", "customfield_12345"):
        assert fields[name]["content"][0]["content"][0]["marks"] == [{"type": "strong"}]


def test_create_orders_deferred_parent_and_native_links(wire):
    wire.responder.seed(
        "createIssue",
        [
            {
                "key": "SBX-9",
                "id": "9",
                "self": "https://example.test/rest/api/3/issue/9",
            }
        ],
    )
    wire.responder.seed("editIssue", [Response(204, None)])
    wire.responder.seed("linkIssues", [Response(201, {}), Response(201, {})])
    result = create(
        "--parent",
        "SBX-2",
        "--parent-via-update",
        "--blocks",
        "SBX-3",
        "--relates-to",
        "OTHER-4",
    )
    assert result.exit_code == 0, result.output
    calls = wire.responder.requests
    assert [r[0] for r in calls] == [
        "createIssue",
        "editIssue",
        "linkIssues",
        "linkIssues",
    ]
    assert "parent" not in calls[0][2]["fields"]
    assert calls[1][1]["issueIdOrKey"] == "SBX-9"
    assert calls[1][2] == {"fields": {"parent": {"key": "SBX-2"}}}
    for call, kind, target in zip(
        calls[2:], ["Blocks", "Relates"], ["SBX-3", "OTHER-4"]
    ):
        assert call[2] == {
            "type": {"name": kind},
            "inwardIssue": {"key": "SBX-9"},
            "outwardIssue": {"key": target},
        }
    assert "Parent set via update: SBX-2" in result.output
    assert "blocks SBX-3, relates to OTHER-4" in result.output
    assert "https://example.test/browse/SBX-9" in result.output


@pytest.mark.parametrize("output", ["text", "json"])
def test_create_deferred_parent_preview_has_no_mutations(wire, output):
    result = create(
        "--parent",
        "SBX-2",
        "--parent-via-update",
        "--sprint",
        "42",
        "--blocks",
        "SBX-3",
        "--dry-run",
        "--output",
        output,
    )
    assert result.exit_code == 0, result.output
    assert wire.responder.requests == []
    if output == "json":
        payload = json.loads(result.stdout)
        assert payload["deferred_parent"] == {"key": "SBX-2"}
        assert "parent" not in payload["fields"]
    else:
        assert "Dry run - no issue was created." in result.output
        assert "Parent SBX-2 would be set in a follow-up update." in result.output


@pytest.mark.parametrize(
    "assignee,expected",
    [
        ("none", None),
        ("unassigned", None),
        ("fixture-account", {"accountId": "fixture-account"}),
        ("assignee@example.test", {"emailAddress": "assignee@example.test"}),
    ],
)
def test_update_assignee_and_parent_clear_keep_empty_collections(
    wire, assignee, expected
):
    wire.responder.seed("editIssue", [Response(204, None)])
    result = invoke(
        "issue",
        "update",
        "SBX-1",
        "--assignee",
        assignee,
        "--parent",
        "none",
        "--custom-fields",
        '{"labels": [], "components": []}',
        "--no-notify",
    )
    assert result.exit_code == 0, result.output
    assert "Updated issue: SBX-1" in result.output
    assert len(wire.responder.requests) == 1
    operation, parameters, body = wire.responder.requests[0]
    assert operation == "editIssue"
    assert parameters["notifyUsers"] is False
    assert body == {
        "fields": {
            "assignee": expected,
            "parent": None,
            "labels": [],
            "components": [],
        }
    }


@pytest.mark.parametrize(
    "body_format,text,expected",
    [
        (
            "text",
            "**literal**\n",
            {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "**literal**"}],
                    },
                    {"type": "paragraph", "content": []},
                ],
            },
        ),
        ("adf", json.dumps(document("Existing")), document("Existing")),
        (None, "{not-json", document("{not-json")),
        (None, json.dumps(document("Detected")), document("Detected")),
    ],
)
def test_update_description_formats_and_regular_fields(
    wire, body_format, text, expected
):
    wire.responder.seed("editIssue", [Response(204, None)])
    args = [
        "issue",
        "update",
        "SBX-1",
        "--summary",
        "Revised",
        "--description",
        text,
        "--priority",
        "Low",
        "--labels",
        "new",
        "--components",
        "API",
        "--parent",
        "SBX-2",
    ]
    if body_format:
        args += ["--format", body_format]
    result = invoke(*args)
    assert result.exit_code == 0, result.output
    assert len(wire.responder.requests) == 1
    _, parameters, body = wire.responder.requests[0]
    assert parameters["notifyUsers"] is True
    assert body["fields"] == {
        "summary": "Revised",
        "description": expected,
        "priority": {"name": "Low"},
        "labels": ["new"],
        "components": [{"name": "API"}],
        "parent": {"key": "SBX-2"},
    }


def test_update_empty_request_refuses_without_transport(wire):
    result = invoke("issue", "update", "SBX-1")
    assert result.exit_code == 1, result.output
    assert "No fields specified for update" in result.output
    assert wire.responder.requests == []


@pytest.mark.parametrize(
    "tracking",
    [{}, {"originalEstimate": "4h", "remainingEstimate": "2h", "timeSpent": "2h"}],
)
def test_get_augments_requested_fields_and_renders_time(wire, tracking):
    wire.responder.seed(
        "getIssue",
        [{"key": "SBX-1", "fields": {"summary": "Timing", "timetracking": tracking}}],
    )
    result = invoke(
        "issue",
        "get",
        "SBX-1",
        "--fields",
        "summary",
        "--show-links",
        "--show-time",
    )
    assert result.exit_code == 0, result.output
    assert len(wire.responder.requests) == 1
    assert wire.responder.requests[0][1]["fields"] == [
        "summary",
        "issuelinks",
        "timetracking",
    ]
    if tracking:
        for label in ("Original Estimate:", "Remaining Estimate:", "Time Spent:"):
            assert label in result.output
    else:
        assert "Time Tracking: Not configured or no data" in result.output


def test_get_json_preserves_adf_and_null_values(wire):
    issue = {
        "key": "SBX-1",
        "fields": {
            "description": document("Raw"),
            "assignee": None,
            "priority": None,
        },
    }
    wire.responder.seed("getIssue", [issue])
    result = invoke("issue", "get", "SBX-1", "--output", "json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == issue
    assert [r[0] for r in wire.responder.requests] == ["getIssue"]
