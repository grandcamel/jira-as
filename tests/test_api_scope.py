"""Project scope verified at argv and recorded transport boundaries."""

import json

import pytest
import requests
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def scoped(monkeypatch):
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda _: None)
    ConfigManager.reset_instance()
    monkeypatch.setattr(
        requests.Session, "send", lambda *_a, **_kw: pytest.fail("HTTP attempted")
    )
    calls = []
    original = Responder.call

    def record(self, operation, parameters, body):
        calls.append((operation.operationId, parameters, body))
        return original(self, operation, parameters, body)

    monkeypatch.setattr(Responder, "call", record)
    yield calls
    ConfigManager.reset_instance()


def invoke(*args, input=None):
    return CliRunner().invoke(cli, ["api", "call", *args], input=input)


def refusal(result, calls):
    assert result.exit_code == 4, (result.output, result.exception)
    assert not result.stdout
    error = json.loads(result.stderr)
    assert set(error) == {"status", "messages", "operation", "note"}
    assert error["status"] is None and error["operation"]
    assert "allowlist=" in error["messages"][0]
    assert calls == []
    return error


@pytest.mark.parametrize(
    "operation,flags",
    [
        ("getIssue", ["--issueIdOrKey", "SBX-1"]),
        ("getSoftwareIssue", ["--issueIdOrKey", "SBX-1"]),
        ("getCustomerRequestByIdOrKey", ["--issueIdOrKey", "SBX-1"]),
        ("getProject", ["--projectIdOrKey", "SBX"]),
        ("getAllBoards", ["--projectKeyOrId", "SBX"]),
    ],
)
def test_matching_named_identity_sends_once(scoped, operation, flags):
    result = invoke(operation, *flags, "--project", "SBX")
    assert result.exit_code == 0, result.output
    assert len(scoped) == 1
    assert scoped[0][0] == operation
    assert "project" not in scoped[0][1]


@pytest.mark.parametrize("value", ["GC-1", "123", "SBX-x"])
def test_disallowed_or_numeric_issue_refuses_before_send(scoped, value):
    refusal(invoke("getIssue", "--issueIdOrKey", value), scoped)


@pytest.mark.parametrize(
    "operation,flags",
    [
        ("getIssue", ["--issueIdOrKey", "SBX-1"]),
        ("getProject", ["--projectIdOrKey", "SBX"]),
        ("getAllBoards", ["--projectKeyOrId", "SBX"]),
    ],
)
def test_conflicting_project_flag_never_sends(scoped, operation, flags):
    refusal(invoke(operation, *flags, "--project", "GC"), scoped)


def create(*flags):
    return (
        "createIssue",
        "--field",
        "fields.project.key=SBX",
        "--field",
        "fields.summary=x",
        "--field",
        "fields.issuetype.name=Task",
        *flags,
    )


def test_body_only_scope_names_missing_project_flag(scoped):
    error = refusal(invoke(*create()), scoped)
    assert "--project" in " ".join(error["messages"])


def test_matching_project_body_and_flag_send_original_payload(scoped):
    result = invoke(*create("--project", "SBX"))
    assert result.exit_code == 0, result.output
    assert scoped == [
        (
            "createIssue",
            {},
            {
                "fields": {
                    "project": {"key": "SBX"},
                    "summary": "x",
                    "issuetype": {"name": "Task"},
                }
            },
        )
    ]


@pytest.mark.parametrize(
    "body",
    [
        {"fields": {"project": {"key": "GC"}}},
        {"fields": {"project": {"id": 10000}}},
        {"fields": {"project": {"key": "SBX", "id": "10000"}}},
        {"fields": {"project": None}},
    ],
)
def test_body_mismatch_numeric_and_malformed_refuse(scoped, body, tmp_path):
    source = tmp_path / "payload.json"
    source.write_text(json.dumps(body))
    refusal(
        invoke("createIssue", "--project", "SBX", "--body", "@" + str(source)), scoped
    )


@pytest.mark.parametrize("operation", ["editIssue", "doTransition"])
def test_keyed_free_map_update_checks_hidden_body_project(scoped, operation, tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps({"fields": {"project": {"key": "GC"}}}))
    refusal(
        invoke(operation, "--issueIdOrKey", "SBX-1", "--body", "@" + str(source)),
        scoped,
    )
    source.write_text(
        json.dumps({"fields": {"project": {"key": "SBX"}, "summary": "x"}})
    )
    result = invoke(operation, "--issueIdOrKey", "SBX-1", "--body", "@" + str(source))
    assert result.exit_code == 0, result.output
    assert len(scoped) == 1


@pytest.mark.parametrize(
    "operation,flags",
    [
        ("getServerInfo", []),
        ("getBoard", ["--boardId", "1"]),
        ("getSprint", ["--sprintId", "1"]),
        ("getServiceDeskById", ["--serviceDeskId", "1"]),
        ("getOrganization", ["--organizationId", "1"]),
    ],
)
def test_site_gate_is_independent(scoped, monkeypatch, operation, flags):
    refusal(invoke(operation, *flags), scoped)
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    assert invoke(operation, *flags, "--project", "SBX").exit_code == 0
    assert len(scoped) == 1


@pytest.mark.parametrize(
    "jql",
    [
        "project = SBX",
        "project = SBX AND status = Open",
        "status = Open and project IN (SBX)",
    ],
)
def test_query_and_body_jql_are_bounded(scoped, jql):
    assert invoke("searchAndReconsileIssuesUsingJql", "--jql", jql).exit_code == 0
    result = invoke(
        "searchAndReconsileIssuesUsingJqlPost",
        "--project",
        "SBX",
        "--field",
        "jql=" + jql,
    )
    assert result.exit_code == 0, result.output
    assert len(scoped) == 2
    assert scoped[-1][2] == {"jql": jql}


@pytest.mark.parametrize(
    "jql",
    [
        "status = Open",
        "project = SBX OR status = Open",
        "project = GC",
        "project = SBX AND filter = 42",
        "project = SBX AND assignee = currentUser()",
        "project = SBX AND",
        "project NOT IN (GC)",
    ],
)
def test_unproved_jql_refuses_before_send(scoped, jql):
    refusal(invoke("searchAndReconsileIssuesUsingJql", "--jql", jql), scoped)


def test_body_jql_requires_real_argv_project(scoped):
    error = refusal(
        invoke("searchAndReconsileIssuesUsingJqlPost", "--field", "jql=project = SBX"),
        scoped,
    )
    assert "--project" in " ".join(error["messages"])


def test_absent_and_empty_allowlists_are_distinct(scoped, monkeypatch):
    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS")
    assert invoke("getIssue", "--issueIdOrKey", "GC-1").exit_code == 0
    scoped.clear()
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "")
    refusal(invoke("getIssue", "--issueIdOrKey", "SBX-1"), scoped)
    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS")
    refusal(invoke("getServerInfo"), scoped)


@pytest.mark.parametrize("issues", [["SBX-1", "GC-2"], ["SBX-1", "10"], []])
def test_bulk_body_keys_check_every_element(scoped, issues):
    refusal(
        invoke(
            "getBulkChangelogs",
            "--project",
            "SBX",
            "--field",
            "issueIdsOrKeys=" + json.dumps(issues),
        ),
        scoped,
    )


def test_settings_and_environment_precedence(scoped, monkeypatch):
    config = ConfigManager.get_instance()
    config.config["jira"].update(
        {"allowed_projects": ["SBX", "GC"], "allow_site_operations": True}
    )
    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS")
    monkeypatch.delenv("JIRA_ALLOW_SITE_OPERATIONS")
    assert config.get_allowed_projects() == ["SBX", "GC"]
    assert config.get_allow_site_operations() is True
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", " sbx,sbx ")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    assert config.get_allowed_projects() == ["SBX"]
    assert config.get_allow_site_operations() is False
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "maybe")
    result = invoke("getServerInfo")
    assert result.exit_code == 2 and scoped == []
    assert json.loads(result.stderr)["messages"] == [
        "JIRA_ALLOW_SITE_OPERATIONS must be true or false"
    ]


@pytest.mark.parametrize("value", [None, "true", 1, []])
def test_invalid_site_setting_is_a_usage_error(scoped, monkeypatch, value):
    monkeypatch.delenv("JIRA_ALLOW_SITE_OPERATIONS")
    ConfigManager.get_instance().config["jira"]["allow_site_operations"] = value
    result = invoke("getServerInfo")
    assert result.exit_code == 2 and scoped == []
    assert json.loads(result.stderr)["messages"] == [
        "jira.allow_site_operations must be a boolean"
    ]
