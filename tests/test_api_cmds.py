"""Generic Jira argv contracts at the responder and intercepted HTTP seams."""

import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
import requests
import responses
from as_engine.errors import SurfaceError
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.engine import create_surface

ORIGINAL_SEND = requests.Session.send


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    for name in ("JIRA_AS_CASSETTE", "JIRA_AS_RECORD", "JIRA_AS_SIMULATION_SEED"):
        monkeypatch.delenv(name, raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("HTTP attempted by responder test")

    monkeypatch.setattr(requests.Session, "send", forbidden)


def invoke(*args, input=None):
    return CliRunner().invoke(cli, ["api", *args], input=input)


@pytest.mark.parametrize("name", ["getIssue", "get-issue"])
@pytest.mark.parametrize("flag", ["--issueIdOrKey", "--issue-id-or-key"])
def test_issue_operation_and_parameter_aliases(name, flag):
    result = invoke("--transport", "responder", "call", name, flag, "SBX-1")
    assert result.exit_code == 0, result.output
    assert isinstance(json.loads(result.stdout), dict)
    assert result.stderr == ""


@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--bogus", "x"],
        ["--issueIdOrKey"],
        ["--issueIdOrKey", "SBX-1", "--issue-id-or-key", "SBX-2"],
        ["--issueIdOrKey", "SBX-1", "--format", "bad"],
    ],
)
def test_bad_flags_refuse_before_send(monkeypatch, flags):
    send = Mock(side_effect=AssertionError("invalid call sent"))
    monkeypatch.setattr(Responder, "call", send)
    result = invoke("call", "getIssue", *flags)
    assert result.exit_code == 2 and result.stdout == "", result.output
    error = json.loads(result.stderr)
    assert set(error) == {"status", "messages", "operation", "note"}
    assert error["status"] is None and error["operation"] == "getIssue"
    send.assert_not_called()


def test_array_boolean_types_and_body_inputs(monkeypatch, tmp_path):
    calls = []
    original = Responder.call

    def record(self, operation, parameters, body):
        calls.append((operation.operationId, parameters, body))
        return original(self, operation, parameters, body)

    monkeypatch.setattr(Responder, "call", record)
    result = invoke(
        "call",
        "getIssue",
        "--issueIdOrKey",
        "SBX-1",
        "--fields",
        "summary,status",
        "--fields",
        "description",
        "--updateHistory",
        "false",
    )
    assert result.exit_code == 0, result.output
    assert calls[-1][1] == {
        "issueIdOrKey": "SBX-1",
        "fields": ["summary", "status", "description"],
        "updateHistory": False,
    }
    body = {"jql": "project = SBX", "maxResults": 2}
    source = tmp_path / "body.json"
    source.write_text(json.dumps(body))
    for flag, stdin in (("@" + str(source), None), ("-", json.dumps(body))):
        result = invoke(
            "call",
            "searchAndReconsileIssuesUsingJqlPost",
            "--project",
            "SBX",
            "--body",
            flag,
            input=stdin,
        )
        assert result.exit_code == 0, result.output
        assert calls[-1][2] == body
    result = invoke(
        "call",
        "searchAndReconsileIssuesUsingJqlPost",
        "--project",
        "SBX",
        "--field",
        "jql=project = SBX",
        "--field",
        "maxResults=2",
        "--validate-body",
    )
    assert result.exit_code == 0, result.output
    assert calls[-1][2] == body
    result = invoke(
        "call",
        "searchAndReconsileIssuesUsingJqlPost",
        "--project",
        "SBX",
        "--body",
        "-",
        "--validate-body",
        input='{"jql":"project = SBX","maxResults":"bad"}',
    )
    assert result.exit_code == 2


@pytest.mark.parametrize(
    "status,code",
    [(400, 2), (401, 3), (403, 4), (404, 5), (409, 7), (429, 6), (500, 6)],
)
def test_json_error_contract(status, code):
    result = invoke(
        "--respond-with", str(status), "call", "getIssue", "--issueIdOrKey", "SBX-1"
    )
    assert result.exit_code == code and result.stdout == "", result.output
    assert json.loads(result.stderr) == {
        "status": status,
        "messages": [f"Responder forced HTTP {status}"],
        "operation": "getIssue",
        "note": None,
    }


@pytest.mark.parametrize(
    "args,code",
    [
        (["describe", "missing"], 5),
        (["search"], 2),
        (["describe"], 2),
        (["bad-command"], 2),
        (["--bad-option"], 2),
    ],
)
def test_usage_failures_are_json(args, code):
    result = invoke(*args)
    assert result.exit_code == code and result.stdout == "", result.output
    assert json.loads(result.stderr)["messages"]


def test_all_three_documents_are_discoverable_and_renames_remain_searchable():
    surface = create_surface(transport="responder")
    assert surface.resolve("getIssue")[0] == "platform"
    assert surface.resolve("getSoftwareIssue")[0] == "software"
    assert surface.resolve("getServiceDeskArticles")[0] == "servicedesk"
    results = json.loads(invoke("search", "sprint", "--format", "json").stdout)
    assert any(row["path"].startswith("/rest/agile/") for row in results)
    assert "getSoftwareIssue" in {
        row["operationId"] for row in surface.search(["getIssue"])
    }
    assert "getServiceDeskArticles" in {
        row["operationId"] for row in surface.search(["getArticles"])
    }
    for format in ("table", "markdown"):
        assert (
            invoke(
                "call", "getIssue", "--issueIdOrKey", "SBX-1", "--format", format
            ).exit_code
            == 0
        )
    result = invoke("call", "getIssue", "--help")
    assert result.exit_code == 0 and "--issue-id-or-key" in result.stdout
    assert {"paging", "search", "agile"} <= set(invoke("topics").stdout.splitlines())


def test_deprecation_warning_and_opt_in_search():
    surface = create_surface(transport="responder")
    assert surface.resolve("searchForIssuesUsingJql")[2].deprecated
    assert (
        invoke("search", "searchForIssuesUsingJql", "--format", "json").stdout.strip()
        == "[]"
    )
    assert (
        "searchForIssuesUsingJql"
        in invoke("search", "searchForIssuesUsingJql", "--include-deprecated").stdout
    )
    result = invoke("call", "searchForIssuesUsingJql", "--jql", "project = SBX")
    assert result.exit_code == 0 and "deprecated" in result.stderr


def test_http_factory_uses_existing_tuple_config_and_correct_base_for_each_document(
    monkeypatch,
):
    from jira_as.config_manager import ConfigManager

    config = Mock()
    config.get_credentials.return_value = (
        "https://offline.invalid/",
        "user@example.invalid",
        "test-only",
    )
    config.get_api_config.return_value = {"timeout": 9, "max_retries": 0}
    config.get_allowed_projects.return_value = ["SBX"]
    config.get_allow_site_operations.return_value = True
    monkeypatch.setattr(ConfigManager, "get_instance", lambda: config)
    surface = create_surface(transport="http")
    surface.search(["sprint"])
    config.get_credentials.assert_not_called()
    with responses.RequestsMock() as wire:
        monkeypatch.setattr(requests.Session, "send", ORIGINAL_SEND)
        for operation, params, path in (
            ("getIssue", {"issueIdOrKey": "SBX-1"}, "/rest/api/3/issue/SBX-1"),
            (
                "getSoftwareIssue",
                {"issueIdOrKey": "SBX-1"},
                "/rest/agile/1.0/issue/SBX-1",
            ),
            ("getServiceDesks", {}, "/rest/servicedeskapi/servicedesk"),
        ):
            wire.get("https://offline.invalid" + path, json={"from": operation})
            assert surface.call(operation, params).body == {"from": operation}
        wire.get(
            "https://offline.invalid/rest/api/3/issue/SBX-2",
            status=403,
            json={"errorMessages": ["No permission"]},
        )
        with pytest.raises(SurfaceError) as caught:
            surface.call("getIssue", {"issueIdOrKey": "SBX-2"})
        assert caught.value.code == 4


def test_risk_preview_and_confirmation_at_transport_seam(monkeypatch):
    from jira_as.cli.commands import api_cmds

    surface = create_surface(transport="responder")
    index = surface.indexes.get("platform")
    original = index.operations["deleteIssue"]
    index.operations["deleteIssue"] = replace(
        original, extensions={**original.extensions, "x-as-risk": "irreversible"}
    )
    responder = Responder(index)
    surface.transport_factory = lambda *_: responder
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)
    args = ["call", "deleteIssue", "--issueIdOrKey", "SBX-1"]
    preview = invoke(*args)
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["dry_run"] is True
    assert responder.requests == []
    confirmed = invoke(*args, "--confirm")
    assert confirmed.exit_code == 0, confirmed.output
    assert responder.requests == [("deleteIssue", {"issueIdOrKey": "SBX-1"}, None)]


def test_configuration_modes_are_wired_without_reading_credentials(
    monkeypatch, tmp_path
):
    from jira_as.config_manager import ConfigManager

    monkeypatch.setattr(
        ConfigManager, "get_instance", lambda: pytest.fail("configuration accessed")
    )
    assert (
        create_surface(transport="responder").describe("getIssue")["operationId"]
        == "getIssue"
    )
    assert (
        create_surface(transport="simulation").describe("getIssue")["operationId"]
        == "getIssue"
    )
    monkeypatch.setenv("JIRA_AS_CASSETTE", str(tmp_path / "future.json"))
    assert (
        create_surface(transport="cassette").describe("getIssue")["operationId"]
        == "getIssue"
    )
    with pytest.raises(ValueError, match="requires cassette"):
        create_surface(transport="responder")
