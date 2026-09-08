"""JAS-65 risk coverage and product CLI confirmation policy."""

import json
from unittest.mock import Mock

import pytest
import requests
from as_engine.help import CAPS, render_help, token_estimate
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as.cli.commands import api_cmds
from jira_as.cli.main import cli
from jira_as.engine import create_surface

NON_DELETE_RISKS = {
    "submitBulkDelete": "irreversible",
    "submitBulkMove": "destructive",
    "removeIssueTypesFromContext": "destructive",
    "removeCustomFieldContextFromProjects": "destructive",
    "trashCustomField": "destructive",
    "removeIssueTypesFromGlobalFieldConfigurationScheme": "destructive",
    "archiveIssuesAsync": "destructive",
    "archiveIssues": "destructive",
    "bulkMoveWorklogs": "destructive",
    "removeMappingsFromIssueTypeScreenScheme": "destructive",
    "archivePlan": "destructive",
    "trashPlan": "destructive",
    "archiveProject": "destructive",
    "deleteProjectAsynchronously": "destructive",
    "mergeVersions": "irreversible",
    "deleteAndReplaceVersion": "irreversible",
    "deleteWorkflowTransitionRuleConfigurations": "irreversible",
    "revokePortalOnlyAccessForUser": "destructive",
    "moveIssuesToBacklog": "destructive",
    "moveIssuesToBacklogForBoard": "destructive",
    "moveIssuesToBoard": "destructive",
    "removeIssuesFromEpic": "destructive",
    "moveIssuesToEpic": "destructive",
    "moveIssuesToSprintAndRank": "destructive",
}


@pytest.fixture
def risk_surface(monkeypatch):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **kw: pytest.fail("unexpected HTTP")
    )
    surface = create_surface(transport="responder")
    surface.scope_allowlist = ("SBX",)
    surface.scope_allow_site = False
    responders = []

    def factory(document, index):
        responder = Responder(index)
        responders.append(responder)
        return responder

    surface.transport_factory = factory
    surface.call = Mock(wraps=surface.call)
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)
    return surface, responders


def invoke(*args):
    return CliRunner().invoke(cli, ["api", "--transport", "responder", *args])


def test_every_delete_operation_has_risk():
    counts = {}
    for document, index in create_surface(transport="responder").indexes.primary():
        deletes = [op for op in index.operations.values() if op.method == "DELETE"]
        counts[document] = len(deletes)
        for operation in deletes:
            assert operation.extensions.get("x-as-risk") in (
                "destructive",
                "irreversible",
            ), operation.operationId
            if operation.extensions["x-as-risk"] == "irreversible":
                assert "risk" in operation.extensions["x-as-topic"], (
                    operation.operationId
                )
    assert counts == {"platform": 89, "software": 24, "servicedesk": 10}


@pytest.mark.parametrize("operation,level", NON_DELETE_RISKS.items())
def test_destructive_non_delete_operations_are_classified(operation, level):
    _, _, op = create_surface(transport="responder").resolve(operation)
    assert op.method != "DELETE"
    assert op.extensions["x-as-risk"] == level
    if level == "irreversible":
        assert "risk" in op.extensions["x-as-topic"]


def test_delete_previews_without_surface_then_confirm_sends_once(
    risk_surface, tmp_path
):
    surface, responders = risk_surface
    destination = tmp_path / "preview-must-not-write.bin"
    result = invoke(
        "call", "deleteIssue", "--issueIdOrKey", "SBX-1", "--output", str(destination)
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "dry_run": True,
        "operationId": "deleteIssue",
        "risk": "irreversible",
        "method": "DELETE",
        "path": "/rest/api/3/issue/SBX-1",
        "parameters": {"issueIdOrKey": "SBX-1"},
        "body": None,
    }
    surface.call.assert_not_called()
    assert responders == [] and not destination.exists()
    result = invoke("call", "deleteIssue", "--issueIdOrKey", "SBX-1", "--confirm")
    assert result.exit_code == 0, result.output
    assert surface.call.call_count == 1
    assert responders[0].requests == [("deleteIssue", {"issueIdOrKey": "SBX-1"}, None)]


def test_destructive_post_defaults_to_json_preview(risk_surface):
    result = invoke(
        "call", "archiveProject", "--projectIdOrKey", "SBX", "--format", "table"
    )
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["risk"] == "destructive" and value["method"] == "POST"
    assert value["path"] == "/rest/api/3/project/SBX/archive"
    assert risk_surface[1] == []
    risk_surface[0].call.assert_not_called()


def test_confirm_retains_scope_guard(risk_surface):
    result = invoke("call", "deleteIssue", "--issueIdOrKey", "OTHER-1", "--confirm")
    assert result.exit_code == 4, result.output
    assert risk_surface[1] == []


@pytest.mark.parametrize(
    "flags",
    [[], ["--unknown"], ["--issueIdOrKey", "SBX-1", "--deleteSubtasks", "invalid"]],
)
def test_invalid_preview_inputs_send_nothing(risk_surface, flags):
    result = invoke("call", "deleteIssue", *flags)
    assert result.exit_code == 2, result.output
    assert risk_surface[1] == []
    risk_surface[0].call.assert_not_called()


def test_describe_risk_and_topic_pagination_caps(risk_surface):
    result = invoke("describe", "deleteIssue", "--format", "json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["risk"] == "irreversible"
    expected = {
        op.operationId
        for _, index in risk_surface[0].indexes.primary()
        for op in index.operations.values()
        if "risk" in op.extensions.get("x-as-topic", [])
    }
    found = set()
    while True:
        result = CliRunner().invoke(
            cli, ["help", "risk", "--offset", str(len(found)), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        value = json.loads(result.output)
        titles = {
            section["title"] for section in value["sections"] if "title" in section
        }
        assert titles and not titles.intersection(found)
        found.update(titles)
        assert token_estimate(render_help(value) + "\n") <= CAPS["topic"]
        if not any(
            "Continue:" in section.get("text", "") for section in value["sections"]
        ):
            break
    assert found == expected
    assert risk_surface[1] == []
