"""Service workflows and sprint decisions exercise stateful transport."""

import json

import pytest
from as_engine.simulation import JiraSimulationStore
from click.testing import CliRunner

from jira_as import engine
from jira_as.autocomplete_cache import InstanceFieldsCache
from jira_as.cli.main import cli


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    seed = JiraSimulationStore().snapshot()
    seed["sprints"] = [
        {"id": 1, "name": "One", "state": "active", "originBoardId": 1},
        {"id": 2, "name": "Two", "state": "closed", "originBoardId": 1},
    ]
    seed["issues"][0]["fields"].update({"sprint": 1, "customfield_10016": 3})
    seed["issues"][1]["fields"].update(
        {
            "sprint": 2,
            "status": {"name": "Done", "statusCategory": {"key": "done"}},
            "customfield_10016": 5,
        }
    )
    seed["slas"] = {
        "SBX-1": [{"id": "1", "name": "Resolution", "ongoingCycle": {"breached": True}}]
    }
    seed["approvals"] = {
        "SBX-1": [
            {"id": "1", "finalDecision": "pending"},
            {"id": "2", "finalDecision": "approved"},
        ]
    }
    seed["articles"] = {"1": [{"title": "First task troubleshooting", "id": "1"}]}
    store = JiraSimulationStore(seed)
    surface = engine.create_surface(transport="simulation", store=store)
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    InstanceFieldsCache(tmp_path).write(store.fields)
    return CliRunner(), store


def run(workflow, *args):
    result = workflow[0].invoke(cli, [*args, "--transport", "simulation"])
    assert result.exit_code == 0, (result.output, result.exception)
    return json.loads(result.output)


def test_jsm_transition_preview_then_apply(workflow):
    before = workflow[1].snapshot()
    assert run(
        workflow, "jsm", "request", "transition", "SBX-1", "--to", "Done", "--dry-run"
    )["dry_run"]
    assert workflow[1].snapshot() == before
    run(workflow, "jsm", "request", "transition", "SBX-1", "--to", "Done")
    assert workflow[1].snapshot()["issues"][0]["fields"]["status"]["name"] == "Done"


def test_jsm_customer_create_then_add(workflow):
    result = run(workflow, "jsm", "customer", "create", "1", "a@example.test")
    assert workflow[1].snapshot()["desk_customers"] == {"1": [result["accountId"]]}
    assert [c[0] for c in workflow[1].calls] == ["createCustomer", "addCustomers"]


def test_jsm_reports_pending_filter_and_kb_keywords(workflow):
    result = run(
        workflow, "jsm", "sla", "report", "--project", "SBX", "--breached-only"
    )
    assert result["slas"] == [
        {"issue": "SBX-1", "name": "Resolution", "breached": True}
    ]
    assert len(run(workflow, "jsm", "approval", "pending", "--project", "SBX")) == 1
    assert (
        run(
            workflow,
            "jsm",
            "approval",
            "pending",
            "--project",
            "SBX",
            "--service-desk-id",
            "99",
        )
        == []
    )
    assert run(workflow, "jsm", "kb", "suggest", "SBX-1")[0]["id"] == "1"


def test_jsm_service_desk_id_alone_does_not_infer_project(workflow):
    result = workflow[0].invoke(
        cli, ["jsm", "approval", "pending", "--service-desk-id", "1"]
    )
    assert result.exit_code == 1 and "project" in result.output
    assert workflow[1].calls == []


def test_sprint_close_previews_then_moves_before_close(workflow):
    before = workflow[1].snapshot()
    args = (
        "agile",
        "sprint",
        "manage",
        "--sprint",
        "1",
        "--close",
        "--move-incomplete-to",
        "2",
        "--project",
        "SBX",
    )
    assert run(workflow, *args)["dry_run"]
    assert workflow[1].snapshot() == before
    run(workflow, *args, "--confirm")
    assert workflow[1].snapshot()["sprints"][0]["state"] == "closed"
    assert workflow[1].snapshot()["issues"][0]["fields"]["sprint"] == 2
    assert [c[0] for c in workflow[1].calls][-2:] == [
        "moveIssuesToSprintAndRank",
        "partiallyUpdateSprint",
    ]


def test_sprint_move_checkpoint_and_velocity(workflow, tmp_path):
    args = (
        "agile",
        "sprint",
        "move-issues",
        "--issues",
        "SBX-1",
        "--sprint",
        "2",
        "--checkpoint",
        str(tmp_path / "move.json"),
    )
    run(workflow, *args)
    count = len(workflow[1].calls)
    run(workflow, *args)
    assert len(workflow[1].calls) == count
    result = run(workflow, "agile", "velocity", "--board", "1", "--project", "SBX")
    assert result["average_velocity"] == 5


def test_sprint_close_missing_project_refuses_before_transport(workflow):
    result = workflow[0].invoke(
        cli,
        [
            "agile",
            "sprint",
            "manage",
            "--sprint",
            "1",
            "--close",
            "--move-incomplete-to",
            "2",
            "--confirm",
        ],
    )
    assert result.exit_code == 1
    assert workflow[1].calls == []


def test_partial_sprint_update_preserves_existing_fields(workflow):
    sprint = workflow[1].sprints[0]
    sprint.update(goal="Keep goal", startDate="2026-09-01", endDate="2026-09-14")
    original = {key: sprint[key] for key in ("name", "goal", "startDate", "endDate")}
    run(workflow, "agile", "sprint", "manage", "--sprint", "1", "--close", "--confirm")
    assert {key: sprint[key] for key in original} == original
    run(workflow, "agile", "sprint", "manage", "--sprint", "1", "--goal", "New goal")
    assert sprint["goal"] == "New goal"
    assert all(sprint[key] == original[key] for key in ("name", "startDate", "endDate"))
    assert [call[0] for call in workflow[1].calls] == [
        "partiallyUpdateSprint",
        "partiallyUpdateSprint",
    ]


def test_sprint_keeps_closed_category_issues_in_original_sprint(workflow):
    closed, incomplete = workflow[1].issues
    closed["fields"].update(
        sprint=1, status={"name": "Closed", "statusCategory": {"key": "done"}}
    )
    incomplete["fields"].update(
        sprint=1, status={"name": "Working", "statusCategory": {"key": "indeterminate"}}
    )
    run(
        workflow,
        "agile",
        "sprint",
        "manage",
        "--sprint",
        "1",
        "--close",
        "--confirm",
        "--move-incomplete-to",
        "2",
        "--project",
        "SBX",
    )
    assert closed["fields"]["sprint"] == 1
    assert incomplete["fields"]["sprint"] == 2


def test_customer_transition_explicit_id_and_internal_comment(workflow):
    run(
        workflow,
        "jsm",
        "request",
        "transition",
        "SBX-1",
        "--transition-id",
        "31",
        "--comment",
        "Internal note",
        "--internal",
    )
    fields = workflow[1].issues[0]["fields"]
    assert fields["status"]["name"] == "Done"
    assert fields["comment"]["comments"][-1] == {
        "id": "1",
        "body": "Internal note",
        "public": False,
    }


def test_customer_add_failure_reports_the_created_account(workflow):
    from as_engine.simulation import JiraSimulation
    from as_engine.transport import Response

    class FailedDeskAssignment(JiraSimulation):
        def call(self, operation, parameters, body, **options):
            if operation.operationId == "addCustomers":
                self.calls.append((operation.operationId, dict(parameters), body))
                return Response(503, {"errorMessages": ["Desk unavailable"]})
            return super().call(operation, parameters, body, **options)

    surface = engine.create_surface(transport="simulation")
    surface.transport_factory = lambda *_: FailedDeskAssignment(workflow[1])
    result = workflow[0].invoke(
        cli,
        [
            "jsm",
            "customer",
            "create",
            "1",
            "partial@example.test",
            "--transport",
            "simulation",
        ],
    )
    assert result.exit_code == 1
    account = workflow[1].customers[0]["accountId"]
    assert (
        account in result.output
        and "was created" in result.output
        and "failed" in result.output
    )
    assert workflow[1].desk_customers == {}
