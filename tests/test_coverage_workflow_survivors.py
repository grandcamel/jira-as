"""Public relationship reports and refusals on the local indexed simulation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from as_engine.simulation import JiraSimulationStore
from click.testing import CliRunner

from jira_as import engine
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def workflow(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network and credential access are forbidden")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr("requests.sessions.Session.request", denied)
    monkeypatch.setattr("socket.socket.connect", denied)
    for name in ("JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET", "JIRA_AS_CASSETTE"):
        monkeypatch.delenv(name, raising=False)
    ConfigManager.reset_instance()
    store = JiraSimulationStore()
    factory = engine.create_surface

    def surface(**kwargs):
        result = factory(transport="simulation", store=store)
        result.scope_allowlist = ("SBX",)
        result.scope_allow_site = False
        return result

    monkeypatch.setattr(engine, "create_surface", surface)

    def invoke(*args, expected=0):
        result = CliRunner().invoke(cli, [*args, "--transport", "simulation"])
        assert result.exit_code == expected, (result.output, result.exception)
        return result

    yield store, invoke
    ConfigManager.reset_instance()


def populate(store, count):
    template = deepcopy(store.issues[0])
    store.issues.clear()
    for number in range(1, count + 1):
        issue = deepcopy(template)
        issue.update(id=str(number), key=f"SBX-{number}")
        issue["fields"].update(summary=f"Report row {number}", issuelinks=[])
        store.issues.append(issue)


def linked_graph(store):
    populate(store, 8)
    store.issues[0]["fields"]["issuelinks"] = [
        {
            "type": {"name": "Blocks"},
            "outwardIssue": {
                "key": "SBX-2",
                "fields": {"status": {"name": "Done"}},
            },
        },
        {"type": {"name": "Relates"}, "inwardIssue": {"key": "SBX-3"}},
    ]
    store.issues[1]["fields"]["issuelinks"] = [
        {
            "type": {"name": "Blocks"},
            "inwardIssue": {
                "key": "SBX-1",
                "fields": {"status": {"name": "Open"}},
            },
        }
    ]


@pytest.mark.parametrize("linked", [False, True])
def test_single_issue_statistics_text_handles_links_and_empty_graph(workflow, linked):
    store, invoke = workflow
    linked_graph(store)
    if not linked:
        store.issues[0]["fields"]["issuelinks"] = []
    result = invoke("relationships", "stats", "SBX-1")
    assert "Link Statistics for SBX-1" in result.output
    assert f"Total Links: {2 if linked else 0}" in result.output
    if linked:
        assert "SBX-2 [Done] (Blocks)" in result.output
        assert "SBX-3 [Unknown] (Relates)" in result.output
        assert "Outward (this issue links to): 1" in result.output
        assert "Inward (linked to this issue): 1" in result.output
    else:
        assert "By Link Type:" not in result.output
        assert "Linked Issues:" not in result.output
    assert [call[0] for call in store.calls] == ["getIssue", "getIssue"]


@pytest.mark.parametrize(
    "selection", [["SBX"], ["--project", "SBX"], ["--jql", "project = SBX"]]
)
def test_project_statistics_text_limits_ranked_and_orphan_rows(workflow, selection):
    store, invoke = workflow
    linked_graph(store)
    result = invoke("relationships", "stats", *selection, "--top", "1")
    for text in (
        "Issues Analyzed: 8 of 8",
        "Total Links: 3",
        "Blocks: 2",
        "Relates: 1",
        "Orphaned Issues (no links): 6",
        "... and 1 more",
        "Most Connected Issues (top 1):",
        "SBX-1 (2 links): Report row 1",
        "Unknown: 1",
        "Done: 1",
    ):
        assert text in result.output
    assert "SBX-2 (1 links)" not in result.output
    assert "SBX-8: Report row 8" not in result.output
    assert [call[0] for call in store.calls].count("getIssue") == 8
    assert len(store.calls) == 9


@pytest.mark.parametrize("count", [0, 2])
def test_project_without_links_omits_connection_and_status_sections(workflow, count):
    store, invoke = workflow
    populate(store, count)
    result = invoke("relationships", "stats", "--project", "SBX")
    assert f"Issues Analyzed: {count} of {count}" in result.output
    assert f"Orphaned Issues (no links): {count}" in result.output
    assert "Most Connected Issues" not in result.output
    assert "Linked Issues by Status:" not in result.output
    assert "Links by Type:" not in result.output


@pytest.mark.parametrize(
    "args,message",
    [
        ([], "Specify only one"),
        (["SBX-1", "--project", "SBX"], "Specify only one"),
        (["--project", "SBX", "--top", "0"], "must be positive"),
        (["--project", "SBX", "--max-results", "0"], "must be positive"),
    ],
)
def test_invalid_statistics_selection_sends_no_requests(workflow, args, message):
    store, invoke = workflow
    assert message in invoke("relationships", "stats", *args, expected=1).output
    assert store.calls == []


@pytest.mark.parametrize(
    "args,message",
    [
        (["--type", "Blocks"], "supplied together"),
        (["--to", "SBX-2"], "supplied together"),
        ([], "exactly one"),
        (["--blocks", "SBX-2", "--relates-to", "SBX-3"], "exactly one"),
    ],
)
def test_bulk_link_invalid_target_choice_sends_no_requests(workflow, args, message):
    store, invoke = workflow
    result = invoke(
        "relationships", "bulk-link", "--issues", "SBX-1", *args, expected=1
    )
    assert message in result.output
    assert store.calls == []


def test_bulk_link_errors_are_reported_and_successful_resume_is_idempotent(
    workflow, tmp_path
):
    store, invoke = workflow
    populate(store, 3)
    args = (
        "relationships",
        "bulk-link",
        "--issues",
        "SBX-1,SBX-2",
        "--type",
        "Blocks",
        "--to",
        "SBX-99",
        "--checkpoint",
        str(tmp_path / "links.json"),
    )
    result = invoke(*args, expected=1)
    assert "Failed:  2" in result.output
    assert "Errors:" in result.output
    assert "SBX-1:" in result.output and "SBX-2:" in result.output
    state = json.loads((tmp_path / "links.json").read_text())
    assert not any(name.endswith(":link") for name in state["steps"])
    target = deepcopy(store.issues[2])
    target.update(id="99", key="SBX-99")
    store.issues.append(target)
    assert "Created: 2" in invoke(*args).output
    mutations = [call for call in store.calls if call[0] == "linkIssues"]
    invoke(*args)
    assert [call for call in store.calls if call[0] == "linkIssues"] == mutations


def test_clone_preview_reads_source_without_mutation(workflow, tmp_path):
    store, invoke = workflow
    before = store.snapshot()
    result = invoke(
        "relationships",
        "clone",
        "SBX-1",
        "--summary",
        "Review copy",
        "--clone-links",
        "--clone-subtasks",
        "--no-link",
        "--dry-run",
        "--checkpoint",
        str(tmp_path / "preview.json"),
    )
    assert json.loads(result.output) == {
        "dry_run": True,
        "source": "SBX-1",
        "target_project": None,
        "summary": "Review copy",
        "include_links": True,
        "include_subtasks": True,
        "create_clone_link": False,
    }
    assert store.snapshot() == before
    assert [call[0] for call in store.calls] == ["getIssue"]
