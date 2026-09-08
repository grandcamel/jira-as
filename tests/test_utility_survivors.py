"""Utility survivors exercise the real indexed Jira simulation seam."""

from __future__ import annotations

import csv
import json
from copy import deepcopy

import pytest
from as_engine.simulation import JiraSimulationStore
from assistant_skills_lib.cache import SkillCache
from click.testing import CliRunner

from jira_as import engine
from jira_as.autocomplete_cache import AutocompleteCache, InstanceFieldsCache
from jira_as.cli.commands import dev_cmds, ops_cmds, search_cmds, time_cmds


@pytest.fixture
def utility_simulation(monkeypatch, tmp_path):
    store = JiraSimulationStore()
    original_surface = engine.create_surface
    original_fields_cache = InstanceFieldsCache
    original_jira_cache = ops_cmds.JiraCache
    cache = AutocompleteCache(
        SkillCache("utility", cache_dir=str(tmp_path / "autocomplete"))
    )

    def surface_factory(**kwargs):
        surface = original_surface(transport="simulation", store=store)
        surface.scope_allowlist = ("SBX", "PROJ")
        surface.scope_allow_site = True
        surface._scope_loaded = True
        return surface

    def no_legacy(*args, **kwargs):
        raise AssertionError("A utility survivor reached the legacy client")

    monkeypatch.setattr(engine, "create_surface", surface_factory)
    monkeypatch.setattr(
        "jira_as.autocomplete_cache.InstanceFieldsCache",
        lambda: original_fields_cache(tmp_path / "fields"),
    )
    monkeypatch.setattr(search_cmds, "get_autocomplete_cache", lambda: cache)
    monkeypatch.setattr(
        ops_cmds,
        "JiraCache",
        lambda cache_dir=None: original_jira_cache(
            cache_dir=cache_dir or str(tmp_path / "ops")
        ),
    )
    for module in (search_cmds, time_cmds, dev_cmds):
        monkeypatch.setattr(module, "get_client_from_context", no_legacy)
    return store


def invoke(group, *args):
    result = CliRunner().invoke(group, [*args, "--transport", "simulation"])
    assert result.exit_code == 0, (result.output, result.exception)
    return result


def test_search_export_pages_and_preserves_json_values(utility_simulation, tmp_path):
    template = utility_simulation.issues[0]
    utility_simulation.issues = [
        {**deepcopy(template), "id": str(i), "key": f"SBX-{i}"} for i in range(1, 104)
    ]
    destination = tmp_path / "issues.json"
    invoke(
        search_cmds.search,
        "export",
        "project = SBX",
        "--format",
        "json",
        "--output",
        str(destination),
        "--fields",
        "summary,priority",
        "--max-results",
        "102",
    )
    data = json.loads(destination.read_text())
    assert data["total"] == 102
    assert data["issues"][0]["priority"] == {"name": "Medium"}
    assert len(utility_simulation.calls) == 2


def test_search_empty_export_writes_csv_header(utility_simulation, tmp_path):
    utility_simulation.issues = []
    destination = tmp_path / "empty.csv"
    invoke(
        search_cmds.search,
        "export",
        "project = SBX",
        "--output",
        str(destination),
        "--fields",
        "key,summary",
    )
    assert list(csv.reader(destination.open())) == [["key", "summary"]]


def test_autocomplete_cache_hits_and_refresh(utility_simulation):
    invoke(search_cmds.search, "fields", "--output", "json")
    invoke(search_cmds.search, "functions", "--output", "json")
    assert [call[0] for call in utility_simulation.calls] == ["getAutoComplete"]
    invoke(search_cmds.search, "fields", "--refresh")
    invoke(search_cmds.search, "suggest", "--field", "project", "--prefix", "Sand")
    invoke(search_cmds.search, "suggest", "--field", "project", "--prefix", "Sand")
    assert [call[0] for call in utility_simulation.calls] == [
        "getAutoComplete",
        "getAutoComplete",
        "getFieldAutoCompleteForQueryString",
    ]


def test_build_local_and_indexed_validation(utility_simulation):
    invoke(search_cmds.search, "build", "--clause", "project = SBX", "--output", "json")
    assert utility_simulation.calls == []
    invoke(
        search_cmds.search,
        "build",
        "--clause",
        "project = SBX",
        "--validate",
        "--output",
        "json",
    )
    assert utility_simulation.calls[0][0] == "parseJqlQueries"


def test_search_bulk_preview_apply_resume_and_binding(utility_simulation, tmp_path):
    checkpoint = tmp_path / "update.json"
    argv = [
        "bulk-update",
        "project = SBX",
        "--add-labels",
        "reviewed",
        "--checkpoint",
        str(checkpoint),
        "--output",
        "json",
    ]
    before = utility_simulation.snapshot()
    invoke(search_cmds.search, *argv)
    assert utility_simulation.snapshot() == before
    assert not checkpoint.exists()
    invoke(search_cmds.search, *argv, "--confirm")
    assert all(i["fields"]["labels"] == ["reviewed"] for i in utility_simulation.issues)
    count = len(utility_simulation.calls)
    invoke(search_cmds.search, *argv, "--confirm")
    assert len(utility_simulation.calls) == count
    result = CliRunner().invoke(
        search_cmds.search,
        [*argv, "--confirm", "--priority", "High", "--transport", "simulation"],
    )
    assert result.exit_code != 0
    assert "mismatch" in result.output


def test_bulk_time_preview_apply_resume(utility_simulation, tmp_path):
    checkpoint = tmp_path / "worklogs.json"
    argv = [
        "bulk-log",
        "--issues",
        "SBX-1,SBX-2",
        "--time",
        "30m",
        "--comment",
        "**Meeting**",
        "--started",
        "2026-09-07T09:00:00+00:00",
        "--checkpoint",
        str(checkpoint),
        "--output",
        "json",
    ]
    before = utility_simulation.snapshot()
    invoke(time_cmds.time, *argv, "--dry-run")
    assert utility_simulation.snapshot() == before
    invoke(time_cmds.time, *argv)
    logs = [i["fields"]["worklog"]["worklogs"] for i in utility_simulation.issues]
    assert all(len(rows) == 1 and rows[0]["timeSpentSeconds"] == 1800 for rows in logs)
    assert logs[0][0]["comment"]["type"] == "doc"
    count = len(utility_simulation.calls)
    invoke(time_cmds.time, *argv)
    assert len(utility_simulation.calls) == count


def test_report_and_timesheet_collect_all_worklogs(utility_simulation, tmp_path):
    utility_simulation.issues[0]["fields"]["timespent"] = 101 * 60
    utility_simulation.issues[0]["fields"]["worklog"]["worklogs"] = [
        {
            "id": str(i),
            "started": "2026-09-07T09:00:00+0000",
            "timeSpentSeconds": 60,
            "timeSpent": "1m",
            "author": {"accountId": "alice", "displayName": "Alice, A"},
            "comment": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Worked"}],
                    }
                ],
            },
        }
        for i in range(101)
    ]
    report = invoke(
        time_cmds.time,
        "report",
        "--project",
        "SBX",
        "--since",
        "2026-09-07",
        "--group-by",
        "user",
        "--format",
        "json",
    )
    assert json.loads(report.output)["total_seconds"] == 6060
    destination = tmp_path / "time.csv"
    invoke(time_cmds.time, "export", "--project", "SBX", "--output", str(destination))
    rows = list(csv.DictReader(destination.open()))
    assert len(rows) == 101
    assert rows[0]["Comment"] == "Worked"
    assert rows[0]["Author"] == "Alice, A"


def test_time_report_requires_explicit_project(utility_simulation):
    result = CliRunner().invoke(time_cmds.time, ["report", "--transport", "simulation"])
    assert result.exit_code != 0
    assert utility_simulation.calls == []


def test_dev_branch_and_pr_use_generic_richtext(utility_simulation):
    issue = utility_simulation.issues[0]
    issue["self"] = "https://example.invalid/rest/api/3/issue/1"
    issue["fields"]["description"] = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Fix the issue"}],
            }
        ],
    }
    result = invoke(
        dev_cmds.dev, "branch-name", "SBX-1", "--auto-prefix", "--output", "json"
    )
    assert json.loads(result.output)["branch_name"].endswith("sbx-1-first-task")
    result = invoke(dev_cmds.dev, "pr-description", "SBX-1", "--include-checklist")
    assert "Fix the issue" in result.output
    assert "https://example.invalid/browse/SBX-1" in result.output
    assert "Testing Checklist" in result.output
    assert [c[0] for c in utility_simulation.calls] == ["getIssue", "getIssue"]


def test_ops_warm_persists_and_discovery_aggregates(utility_simulation, tmp_path):
    invoke(ops_cmds.ops, "cache-warm", "--all", "--json")
    assert [c[0] for c in utility_simulation.calls] == [
        "searchProjects",
        "getFields",
        "getIssueAllTypes",
        "getPriorities",
    ]
    status = CliRunner().invoke(ops_cmds.ops, ["cache-status", "--json"])
    assert status.exit_code == 0
    assert json.loads(status.output)["entry_count"] > 0
    utility_simulation.issues[0]["fields"]["created"] = "2026-09-07T00:00:00Z"
    result = invoke(
        ops_cmds.ops, "discover-project", "SBX", "--days", "10000", "--output", "json"
    )
    assert json.loads(result.output)["metadata"]["project_key"] == "SBX"
    assert json.loads(result.output)["patterns"]["sample_size"] >= 1


def test_ops_users_use_explicit_issue_scope(utility_simulation):
    invoke(
        ops_cmds.ops,
        "cache-warm",
        "--users",
        "--project",
        "SBX",
        "--issue-key",
        "SBX-1",
        "--json",
    )
    assert utility_simulation.calls[0][0] == "findAssignableUsers"
    assert utility_simulation.calls[0][1]["issueKey"] == "SBX-1"


@pytest.mark.parametrize(
    ("group", "argv", "operation"),
    [
        (
            search_cmds.search,
            ["bulk-update", "project = SBX", "--add-labels", "done", "--confirm"],
            "editIssue",
        ),
        (
            time_cmds.time,
            ["bulk-log", "--issues", "SBX-1,SBX-2", "--time", "30m"],
            "addWorklog",
        ),
    ],
)
def test_partial_failure_checkpoint_retries_only_failed_step(
    utility_simulation, tmp_path, monkeypatch, group, argv, operation
):
    from as_engine.simulation import JiraSimulation
    from as_engine.transport import Response

    original = JiraSimulation._call
    failed = False

    def fail_once(self, name, parameters, body):
        nonlocal failed
        if (
            name == operation
            and parameters.get("issueIdOrKey") == "SBX-2"
            and not failed
        ):
            failed = True
            return Response(503, {"errorMessages": ["simulated temporary failure"]})
        return original(self, name, parameters, body)

    monkeypatch.setattr(JiraSimulation, "_call", fail_once)
    args = [
        *argv,
        "--checkpoint",
        str(tmp_path / "partial.json"),
        "--output",
        "json",
        "--transport",
        "simulation",
    ]
    first = CliRunner().invoke(group, args)
    assert first.exit_code != 0
    assert "simulated temporary failure" in first.output
    count = len(utility_simulation.calls)
    second = CliRunner().invoke(group, args)
    assert second.exit_code == 0, second.output
    assert [call[:2] for call in utility_simulation.calls[count:]] == [
        (
            operation,
            {
                "issueIdOrKey": "SBX-2",
                **({"notifyUsers": False} if operation == "editIssue" else {}),
            },
        )
    ]


def test_site_metadata_refusal_has_no_transport_call(utility_simulation, monkeypatch):
    original = engine.create_surface

    def restricted_surface(**kwargs):
        surface = original(**kwargs)
        surface.scope_allow_site = False
        return surface

    monkeypatch.setattr(engine, "create_surface", restricted_surface)
    result = CliRunner().invoke(
        search_cmds.search, ["fields", "--no-cache", "--transport", "simulation"]
    )
    assert result.exit_code != 0
    assert utility_simulation.calls == []
