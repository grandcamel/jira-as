"""Workflow survivors exercised through the stateful Jira Surface transport."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from as_engine.simulation import JiraSimulationStore
from click.testing import CliRunner

from jira_as import engine
from jira_as.cli.commands.bulk_cmds import WorkflowCheckpoint, workflow_call
from jira_as.cli.main import cli


@pytest.fixture
def workflow(monkeypatch):
    store = JiraSimulationStore()
    surface = engine.create_surface(transport="simulation", store=store)
    surface.scope_allowlist = ("SBX",)
    surface.scope_allow_site = False
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)

    def invoke(*args, expected=0):
        result = CliRunner().invoke(cli, [*args, "--transport", "simulation"])
        assert result.exit_code == expected, (result.output, result.exception)
        return result

    return store, surface, invoke


def operations(store, *names):
    return [call for call in store.calls if call[0] in names]


def test_bulk_transition_preview_apply_resume_changed_jql(workflow, tmp_path):
    store, _, invoke = workflow
    args = (
        "bulk",
        "transition",
        "--jql",
        "project = SBX AND status = Open",
        "--to",
        "Done",
        "--comment",
        "**Completed**",
        "--output",
        "json",
        "--checkpoint",
        str(tmp_path / "steps.json"),
    )
    before = store.snapshot()
    assert json.loads(invoke(*args, "--dry-run").output)["would_process"] == 2
    assert store.snapshot() == before
    assert not operations(store, "doTransition", "addComment")
    assert json.loads(invoke(*args).output)["success"] == 2
    assert all(i["fields"]["status"]["name"] == "Done" for i in store.issues)
    invoke(*args)
    assert len(operations(store, "doTransition", "addComment")) == 4
    assert len(operations(store, "searchAndReconsileIssuesUsingJql")) == 1
    assert store.issues[0]["fields"]["comment"]["comments"][0]["body"]["type"] == "doc"


@pytest.mark.parametrize(
    "changed",
    [
        ("--to", "Open"),
        ("--comment", "other"),
        ("--jql", "project = SBX"),
        ("--max-issues", "1"),
    ],
)
def test_checkpoint_binding(workflow, tmp_path, changed):
    store, _, invoke = workflow
    args = [
        "bulk",
        "transition",
        "--jql",
        "project = SBX AND status = Open",
        "--to",
        "Done",
        "--comment",
        "ok",
        "--checkpoint",
        str(tmp_path / "bound.json"),
    ]
    invoke(*args, "--dry-run")
    before = len(store.calls)
    if changed[0] in args:
        args[args.index(changed[0]) + 1] = changed[1]
    else:
        args.extend(changed)
    assert "mismatch" in invoke(*args, expected=1).output
    assert len(store.calls) == before


def test_checkpoint_other_operation(workflow, tmp_path):
    store, _, invoke = workflow
    path = str(tmp_path / "bound.json")
    invoke(
        "bulk",
        "assign",
        "--issues",
        "SBX-1",
        "--assignee",
        "user-1",
        "--checkpoint",
        path,
    )
    before = len(store.calls)
    invoke(
        "bulk",
        "delete",
        "--issues",
        "SBX-1",
        "--confirm",
        "--checkpoint",
        path,
        expected=1,
    )
    assert len(store.calls) == before


def test_ambiguous_transition_does_not_mutate(workflow):
    store, _, invoke = workflow
    store.transitions = {
        "*": [{"id": "1", "name": "Done one"}, {"id": "2", "name": "Done two"}]
    }
    assert (
        "Ambiguous"
        in invoke(
            "bulk",
            "transition",
            "--issues",
            "SBX-1",
            "--to",
            "Done",
            "--output",
            "json",
            expected=1,
        ).output
    )
    assert not operations(store, "doTransition")


def test_unscoped_search_sends_nothing(workflow):
    store, _, invoke = workflow
    invoke("bulk", "transition", "--jql", "status = Open", "--to", "Done", expected=1)
    assert store.calls == []


@pytest.mark.parametrize("flag", ["--yes", "--confirm"])
def test_delete_preview_confirm_resume(workflow, tmp_path, flag):
    store, _, invoke = workflow
    args = (
        "bulk",
        "delete",
        "--issues",
        "SBX-1,SBX-2",
        "--output",
        "json",
        "--checkpoint",
        str(tmp_path / "delete.json"),
    )
    assert json.loads(invoke(*args).output)["dry_run"]
    assert not operations(store, "deleteIssue")
    invoke(*args, flag)
    assert store.issues == []
    invoke(*args, flag)
    assert len(operations(store, "deleteIssue")) == 2


def test_assign_unassign_priority_and_resume(workflow, tmp_path):
    store, _, invoke = workflow
    args = (
        "bulk",
        "assign",
        "--issues",
        "SBX-1,SBX-2",
        "--assignee",
        "account-42",
        "--checkpoint",
        str(tmp_path / "assign.json"),
    )
    invoke(*args)
    invoke(*args)
    assert len(operations(store, "assignIssue")) == 2
    assert all(
        i["fields"]["assignee"]["accountId"] == "account-42" for i in store.issues
    )
    invoke("bulk", "assign", "--issues", "SBX-1", "--unassign")
    assert store.issues[0]["fields"]["assignee"] is None
    invoke("bulk", "set-priority", "--issues", "SBX-1,SBX-2", "--priority", "High")
    assert all(i["fields"]["priority"]["name"] == "High" for i in store.issues)


def test_email_assignment_scoped(workflow):
    store, _, invoke = workflow
    store.users = [{"accountId": "person", "emailAddress": "person@example.invalid"}]
    invoke(
        "bulk", "assign", "--issues", "SBX-1", "--assignee", "person@example.invalid"
    )
    assert store.issues[0]["fields"]["assignee"]["accountId"] == "person"
    assert operations(store, "findAssignableUsers")[0][1]["issueKey"] == "SBX-1"


def test_bulk_clone_children_links_resume(workflow, tmp_path):
    store, surface, invoke = workflow
    child = deepcopy(store.issues[1])
    child.update(id="3", key="SBX-3")
    child["fields"].update(
        issuetype={"name": "Sub-task", "subtask": True}, parent={"key": "SBX-1"}
    )
    store.issues.append(child)
    store.issues[0]["fields"]["subtasks"] = [{"key": "SBX-3"}]
    workflow_call(
        surface,
        "linkIssues",
        {},
        {
            "type": {"name": "Blocks"},
            "inwardIssue": {"key": "SBX-1"},
            "outwardIssue": {"key": "SBX-2"},
        },
        scope_argv_identity="SBX",
    )
    args = (
        "bulk",
        "clone",
        "--issues",
        "SBX-1",
        "--include-subtasks",
        "--include-links",
        "--prefix",
        "Copy",
        "--checkpoint",
        str(tmp_path / "clone.json"),
        "--output",
        "json",
    )
    before = store.snapshot()
    invoke(*args, "--dry-run")
    assert store.snapshot() == before
    result = json.loads(invoke(*args).output)
    cloned = next(
        i for i in store.issues if i["key"] == result["created_issues"][0]["key"]
    )
    assert cloned["fields"]["summary"] == "Copy First task"
    assert len(cloned["fields"]["subtasks"]) == 1
    assert cloned["fields"]["issuelinks"][0]["outwardIssue"]["key"] == "SBX-2"
    invoke(*args)
    assert len(operations(store, "createIssue")) == 2
    assert len(operations(store, "linkIssues")) == 2


def test_relationship_clone_resume_failed_link(workflow, tmp_path):
    store, _, invoke = workflow
    store.issues[0]["fields"]["issuelinks"] = [
        {"id": "99", "type": {"name": "Blocks"}, "outwardIssue": {"key": "SBX-99"}}
    ]
    args = (
        "relationships",
        "clone",
        "SBX-1",
        "--clone-links",
        "--no-link",
        "--checkpoint",
        str(tmp_path / "clone.json"),
        "--output",
        "json",
    )
    invoke(*args, expected=1)
    assert len(operations(store, "createIssue")) == 1
    missing = deepcopy(store.issues[1])
    missing.update(id="99", key="SBX-99")
    store.issues.append(missing)
    assert json.loads(invoke(*args).output)["links_copied"] == 1
    invoke(*args)
    assert len(operations(store, "createIssue")) == 1
    assert len(operations(store, "linkIssues")) == 2


@pytest.mark.parametrize("verb", ["resolve", "reopen"])
def test_lifecycle_steps_resume_independently(workflow, tmp_path, verb):
    store, surface, invoke = workflow
    path = str(tmp_path / "lifecycle.json")
    state = WorkflowCheckpoint(
        path,
        f"lifecycle {verb}",
        {"issue": "SBX-1"},
        {"resolution": "Done" if verb == "resolve" else None, "comment": "**note**"},
    )
    transition = store.transitions["*"][2 if verb == "resolve" else 0]
    state.step("choice", lambda: transition)
    state.step(
        "transition",
        lambda: workflow_call(
            surface,
            "doTransition",
            {"issueIdOrKey": "SBX-1"},
            {"transition": {"id": transition["id"]}},
        ),
    )
    store.transitions = {"*": []}
    args = ("lifecycle", verb, "SBX-1", "--comment", "**note**", "--checkpoint", path)
    invoke(*args)
    invoke(*args)
    assert len(operations(store, "doTransition")) == 1
    assert len(operations(store, "addComment")) == 1
    assert store.issues[0]["fields"]["comment"]["comments"][0]["body"]["type"] == "doc"


def test_lifecycle_resolution_and_reopen(workflow):
    store, _, invoke = workflow
    invoke("lifecycle", "resolve", "SBX-1", "--resolution", "Fixed")
    assert store.issues[0]["fields"]["status"]["name"] == "Done"
    assert store.issues[0]["fields"]["resolution"] == {"name": "Fixed"}
    invoke("lifecycle", "reopen", "SBX-1")
    assert store.issues[0]["fields"]["status"]["name"] == "Open"


def test_bulk_link_direction_skip_resume(workflow, tmp_path):
    store, _, invoke = workflow
    args = (
        "relationships",
        "bulk-link",
        "--issues",
        "SBX-1",
        "--is-blocked-by",
        "SBX-2",
        "--checkpoint",
        str(tmp_path / "links.json"),
        "--output",
        "json",
    )
    invoke(*args, "--dry-run")
    assert not operations(store, "linkIssues")
    invoke(*args)
    invoke(*args)
    assert len(operations(store, "linkIssues")) == 1
    body = operations(store, "linkIssues")[0][2]
    assert (
        body["inwardIssue"]["key"] == "SBX-2" and body["outwardIssue"]["key"] == "SBX-1"
    )
    result = json.loads(
        invoke(
            "relationships",
            "bulk-link",
            "--issues",
            "SBX-1",
            "--is-blocked-by",
            "SBX-2",
            "--skip-existing",
            "--output",
            "json",
        ).output
    )
    assert result["skipped"] == 1
    assert len(operations(store, "linkIssues")) == 1


def test_stats_reads_each_issue(workflow):
    store, _, invoke = workflow
    invoke("relationships", "bulk-link", "--issues", "SBX-1", "--blocks", "SBX-2")
    store.calls.clear()
    result = json.loads(
        invoke("relationships", "stats", "--project", "SBX", "--output", "json").output
    )
    assert result["issues_analyzed"] == 2 and result["total_links"] == 2
    assert result["by_type"] == {"Blocks": 2}
    assert len(operations(store, "searchAndReconsileIssuesUsingJql")) == 1
    assert len(operations(store, "getIssue")) == 2
