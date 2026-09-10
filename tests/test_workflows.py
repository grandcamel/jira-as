"""Public workflow argv over real Jira configuration, index, Surface and guards.

Only transport and local configuration sources are controlled. Installed wheel/
sdist and unmodified old-engine pairing are separate supervisor acceptance gates.
"""

import hashlib
import importlib.abc
import json
import os
import shlex
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from importlib import metadata, resources
from pathlib import Path
from textwrap import dedent

import pytest
import requests
from as_engine.help import render_help
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as import config_manager, engine
from jira_as.cli.main import cli


def forbidden(*args, **kwargs):
    pytest.fail("unexpected configuration, transport, or HTTP access")


@pytest.fixture(autouse=True)
def isolated_operator(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("JIRA_") or name in {"SITE_URL", "EMAIL", "API_TOKEN"}:
            monkeypatch.delenv(name)
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "http")
    monkeypatch.setenv("JIRA_SITE_URL", "https://fixture.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "fixture@example.test")
    monkeypatch.setenv("JIRA_API_TOKEN", "fixture-only")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "AAA")
    monkeypatch.setattr(config_manager.ConfigManager, "_instances", {})
    monkeypatch.setattr(
        config_manager.ConfigManager, "_find_claude_dir", lambda self: None
    )
    monkeypatch.setattr(config_manager, "is_keychain_available", lambda: False)
    monkeypatch.setattr(requests.Session, "send", forbidden)
    monkeypatch.setattr(engine, "HTTPTransport", forbidden)


def project(number, key, name):
    return {
        "id": str(number),
        "key": key,
        "name": name,
        "self": f"https://fixture.atlassian.net/rest/api/3/project/{number}",
    }


PROJECTS = [
    project(10001, "AAA", "Alpha"),
    project(10002, "BBB", "Shared"),
    project(10003, "CCC", "Shared"),
]


def page(values=None, *, offset=0, limit=25, total=3, last=True):
    return {
        "values": deepcopy(PROJECTS if values is None else values),
        "startAt": offset,
        "maxResults": limit,
        "total": total,
        "isLast": last,
    }


@pytest.fixture
def transport(monkeypatch):
    state = {"responses": [], "calls": [], "constructed": [], "closed": 0}

    class ControlledTransport:
        def __init__(self, base_url, **settings):
            state["constructed"].append((base_url, settings))

        def call(self, operation, parameters, body):
            state["calls"].append(
                (
                    operation.operationId,
                    operation.method,
                    operation.path,
                    dict(parameters),
                    body,
                )
            )
            assert operation.method == "GET", "workflow attempted a write"
            assert state["responses"], "unexpected additional task call"
            response = state["responses"].pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        def close(self):
            state["closed"] += 1

    monkeypatch.setattr(engine, "HTTPTransport", ControlledTransport)
    return state


def invoke(*argv, code=0, format="json", root=()):
    result = CliRunner().invoke(cli, [*root, "workflows", *argv, "--format", format])
    assert result.exit_code == code, (result.output, result.exception)
    output = result.stderr if code else result.stdout
    assert (result.stdout if code else result.stderr) == ""
    if format == "markdown":
        assert output.count("```json") == 1 and output.count("```") == 2
        value = json.loads(output.split("```json\n", 1)[1].rsplit("```", 1)[0])
    else:
        value = json.loads(output)
    assert value["exit_code"] == code
    return value, output


def replace_resource(monkeypatch, tmp_path, data):
    """Substitute installed resource bytes, leaving loader/validation real."""
    original = resources.files
    (tmp_path / "workflows.json").write_bytes(
        data if isinstance(data, bytes) else json.dumps(data).encode()
    )
    monkeypatch.setattr(
        resources,
        "files",
        lambda package: tmp_path if package == "jira_as" else original(package),
    )


def resource_data():
    return json.loads(
        resources.files("jira_as").joinpath("workflows.json").read_bytes()
    )


def test_discovery_is_pure_and_only_delivered_entry_is_supported(monkeypatch):
    for name in ("JIRA_SITE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(name)
    monkeypatch.setattr(config_manager.ConfigManager, "get_instance", forbidden)
    monkeypatch.setattr(engine, "create_surface", forbidden)
    monkeypatch.setattr(engine, "ProductIndexes", forbidden)
    listing, _ = invoke("list")
    assert [row["id"] for row in listing["entries"]] == ["list-projects"]
    assert listing["support"] is True and listing["availability"] == "unknown"
    assert listing["complete"] is True and listing["continuation"] is None
    found, _ = invoke("search", "What Jira projects can I see?")
    assert found["entries"] == listing["entries"]
    empty, _ = invoke("search", "sourdough bakery")
    assert empty["entries"] == [] and empty["complete"] is True
    exhausted, _ = invoke("list", "--offset", "1")
    assert exhausted["entries"] == []
    described, _ = invoke("describe", "list-projects")
    assert described["binding"]["operation_id"] == "searchProjects"
    assert described["binding"]["document"] == "platform"
    assert described["binding"]["scope"] == {"in": "site"}
    assert described["inputs"]["limit"] == {
        "type": "integer",
        "default": 25,
        "minimum": 1,
        "maximum": 100,
    }
    assert described["inputs"]["offset"]["maximum"] == 9223372036854775807
    authored = resource_data()["workflows"][0]["examples"]
    first_invocation = next(row for row in authored if row["kind"] == "invocation")
    assert described["examples"] == [first_invocation]
    examples, _ = invoke("describe", "list-projects", "--examples")
    assert all(set(row) == {"kind", "value"} for row in examples["examples"])
    assert examples["examples"] == authored


def test_cold_root_help_is_credential_free_in_isolated_process(tmp_path):
    # Keep cold imports and their captured aliases outside parent test state.
    probe = dedent(
        """
        import sys

        sys.path.insert(0, sys.argv[1])

        import requests
        from as_engine.surface import Surface
        from as_engine.transport import HTTPTransport
        from jira_as import config_manager, engine

        def forbidden(*args, **kwargs):
            raise AssertionError("cold help constructed execution machinery")

        config_manager.ConfigManager.__init__ = forbidden
        config_manager.ConfigManager.get_instance = classmethod(forbidden)
        engine.create_surface = forbidden
        Surface.__init__ = forbidden
        HTTPTransport.__init__ = forbidden
        requests.Session.__init__ = forbidden
        requests.Session.send = forbidden

        from jira_as.cli.main import cli

        cli.main(args=["--help"], prog_name="jira-as")
        """
    )
    source_root = Path(__file__).resolve().parents[1] / "src"
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(source_root)],
        cwd=tmp_path,
        env={
            "HOME": str(tmp_path),
            "PATH": os.defpath,
            "TMPDIR": str(tmp_path),
            "LC_ALL": "C",
            "NO_COLOR": "1",
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stderr == ""
    output = " ".join(result.stdout.split())
    assert "Usage: jira-as [OPTIONS] [COMMAND] [ARGS]..." in output
    assert "Jira Assistant Skills CLI." in output
    routing = (
        "For user tasks, first check supported workflows. "
        "Search your request below, then describe a matching ID for its run command."
    )
    assert routing in output
    assert output.index(routing) < output.index("Workflows (")
    assert output.index("Workflows (") < output.index("Commands:")
    assert 'Start: workflows search "task" --format json' in output
    assert "workflows describe ID includes a run example" in output
    assert (
        f"Workflows (jira-as {metadata.version('jira-as')}, catalog r1, indexed-read-v1)"
        in output
    )
    assert result.stdout.index("Workflows (") < result.stdout.index("Commands:")
    for option in ("--version", "--output", "--verbose", "--quiet", "--help"):
        assert option in result.stdout
    command_lines = result.stdout.split("Commands:", 1)[1].splitlines()
    commands = {line.split()[0] for line in command_lines if line.strip()}
    assert {"api", "help", "workflows"} <= commands


def test_installed_resource_provenance_and_whitespace_digest(monkeypatch, tmp_path):
    raw = resources.files("jira_as").joinpath("workflows.json").read_bytes()
    before, _ = invoke("describe", "list-projects")
    assert before["product_version"] == metadata.version("jira-as") == "2.0.0rc1"
    assert before["engine_version"] == metadata.version("as-engine")
    assert before["definition_digest"] == hashlib.sha256(raw).hexdigest()
    assert (
        before["revision"]
        == before["catalog_revision"]
        == before["schema_version"]
        == 1
    )
    assert (
        before["required_capabilities"]
        == before["runtime_capabilities"]
        == ["indexed-read-v1"]
    )
    replace_resource(monkeypatch, tmp_path, raw + b"\n")
    after, _ = invoke("describe", "list-projects")
    assert after["definition_digest"] == hashlib.sha256(raw + b"\n").hexdigest()
    assert after["definition_digest"] != before["definition_digest"]
    assert after["product_version"] == before["product_version"]


def test_indexed_read_and_reduced_page_continuation(transport):
    transport["responses"] = [
        Response(200, page(PROJECTS[:2], limit=2, last=False)),
        Response(200, page(PROJECTS[2:], offset=2)),
    ]
    first, _ = invoke("run", "list-projects")
    assert first["status"] == "completed-read" and first["complete"] is False
    assert first["evidence"]["document"] == "platform"
    assert first["evidence"]["operation_id"] == "searchProjects"
    assert first["limit"] == 25 and first["returned_count"] == 2
    assert first["continuation"] == {
        "workflow": "list-projects",
        "inputs": {"limit": 25, "offset": 2},
    }
    second, _ = invoke(
        "run", first["continuation"]["workflow"], "--limit", "25", "--offset", "2"
    )
    assert second["complete"] is True and second["continuation"] is None
    assert second["range"] == {"start": 2, "end": 3}
    items = first["items"] + second["items"]
    assert [(row["id"], row["key"], row["name"]) for row in items] == [
        ("10001", "AAA", "Alpha"),
        ("10002", "BBB", "Shared"),
        ("10003", "CCC", "Shared"),
    ]
    assert all(row["url_source"] == "provider-self" for row in items)
    assert transport["calls"] == [
        (
            "searchProjects",
            "GET",
            "/rest/api/3/project/search",
            {"orderBy": "key", "action": "view", "maxResults": 25, "startAt": offset},
            None,
        )
        for offset in (0, 2)
    ]
    assert transport["closed"] == len(transport["constructed"]) == 2


def test_default_bound_requires_two_reads_for_27_projects(transport):
    rows = [
        project(20000 + i, f"P{i:02}", "Shared" if i in {4, 26} else f"Project {i}")
        for i in range(27)
    ]
    transport["responses"] = [
        Response(200, page(rows[:25], total=27, last=False)),
        Response(200, page(rows[25:], offset=25, total=27)),
    ]
    first, _ = invoke("run", "list-projects")
    assert len(transport["calls"]) == 1
    assert first["returned_count"] == 25 and first["complete"] is False
    assert first["continuation"]["inputs"] == {"limit": 25, "offset": 25}
    final, _ = invoke("run", "list-projects", "--offset", "25")
    assert final["complete"] is True and final["returned_count"] == 2
    assert [r["id"] for r in first["items"] + final["items"]] == [r["id"] for r in rows]
    assert (
        len([r for r in first["items"] + final["items"] if r["name"] == "Shared"]) == 2
    )


@pytest.mark.parametrize("format", ["json", "markdown"])
@pytest.mark.parametrize(
    "payload,code,complete,reason",
    [
        (page([], total=0), 0, True, "final-page"),
        (page([], last=False), 1, None, "no-progress"),
        ({"values": [], "startAt": 0}, 0, None, "completion-unknown"),
        ({"values": PROJECTS, "startAt": 0}, 0, None, "completion-unknown"),
        ({"values": PROJECTS, "total": 4}, 0, False, "offset-unestablished"),
        ({"values": PROJECTS, "isLast": True}, 0, True, "final-page"),
    ],
)
def test_empty_and_incomplete_evidence(
    transport, format, payload, code, complete, reason
):
    transport["responses"] = [Response(200, payload)]
    result, _ = invoke("run", "list-projects", code=code, format=format)
    assert result["complete"] is complete
    assert result["reason"]["code"] == reason
    assert result["continuation"] is None
    assert len(transport["calls"]) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("startAt", True),
        ("startAt", -1),
        ("startAt", 1),
        ("maxResults", False),
        ("maxResults", 0),
        ("maxResults", 26),
        ("maxResults", 2),
        ("total", True),
        ("total", -1),
        ("total", 2),
        ("total", 4),
        ("isLast", "true"),
        ("isLast", False),
    ],
)
def test_contradictory_metadata_is_unknown(transport, field, value):
    payload = page()
    payload[field] = value
    transport["responses"] = [Response(200, payload)]
    result, _ = invoke("run", "list-projects", code=1)
    assert result["status"] == "unknown" and result["complete"] is None
    assert result["reason"]["code"] == "malformed-page"
    assert result["continuation"] is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"values": {}},
        page([{"id": "10001"}], total=1),
        page([PROJECTS[0], PROJECTS[0]], total=2),
        page([PROJECTS[0], {**PROJECTS[1], "key": "AAA"}], total=2),
    ],
)
def test_malformed_page_and_duplicate_identity_are_unknown(transport, payload):
    transport["responses"] = [Response(200, payload)]
    result, _ = invoke("run", "list-projects", code=1)
    assert result["status"] == "unknown" and result["complete"] is None
    assert result["continuation"] is None


def test_overflow_is_visible_and_never_exhaustive(transport):
    transport["responses"] = [Response(200, page(limit=2))]
    result, _ = invoke("run", "list-projects", "--limit", "2", code=1)
    assert result["status"] == "unknown" and result["complete"] is None
    assert result["evidence"]["received_count"] == 3
    assert result["evidence"]["omitted_count"] == 1
    assert result["returned_count"] == 2 and result["continuation"] is None


@pytest.mark.parametrize(
    "args",
    [
        ("--limit", "0"),
        ("--limit", "101"),
        ("--limit", "true"),
        ("--limit", "2.5"),
        ("--offset", "-1"),
        ("--offset", "9223372036854775808"),
        ("--limit", "2", "--limit=3"),
        ("--offset=1", "--offset", "1"),
        ("--transport", "http"),
        ("--site", "https://untrusted.test"),
        ("--allow-site",),
        ("--body", "{}"),
        ("--all",),
        ("extra",),
    ],
)
def test_invalid_or_duplicate_run_inputs_precede_surface(monkeypatch, args):
    monkeypatch.setattr(engine, "create_surface", forbidden)
    result, _ = invoke("run", "list-projects", *args, code=2)
    assert (
        result["status"] == "needs-input"
        and result["reason"]["code"] == "invalid-input"
    )
    assert result["items"] == [] and result["continuation"] is None


@pytest.mark.parametrize(
    "argv",
    [
        ["run", "list-projects", "--limit", "--format", "json"],
        ["run", "list-projects", "--format", "json", "--format=json"],
        ["describe", "list-projects", "--examples", "--examples", "--format", "json"],
        ["search", "projects", "--offset", "0", "--offset=0", "--format", "json"],
        ["run", "--format", "json"],
    ],
)
def test_parser_failures_have_single_structured_stderr(argv):
    result = CliRunner().invoke(cli, ["workflows", *argv])
    assert result.exit_code == 2 and result.stdout == "", (
        result.output,
        result.exception,
    )
    assert json.loads(result.stderr)["status"] == "needs-input"


@pytest.mark.parametrize(
    "query,reason",
    [
        ("", "invalid-discovery-input"),
        ("x" * 513, "invalid-discovery-input"),
        ("😀" * 512, "query-output-too-large"),
        ("projects " + "😀" * 503, "query-output-too-large"),
    ],
)
def test_search_input_and_escaped_output_bounds(query, reason):
    result, text = invoke("search", query, code=2, format="markdown")
    assert result["reason"]["code"] == reason and result["status"] == "needs-input"
    assert len(text) <= 3200 and result["continuation"] is None
    if reason == "query-output-too-large":
        assert "query" not in result
        assert result["next_actions"] == [{"action": "shorten-query"}]


@pytest.mark.parametrize("action", ["describe", "run"])
def test_unknown_workflow_does_not_construct_surface(monkeypatch, action):
    monkeypatch.setattr(engine, "create_surface", forbidden)
    result, _ = invoke(action, "unavailable-task", code=2)
    assert result["support"] is False and result["status"] == "needs-input"
    assert result["next_actions"] == [{"action": "search-catalog"}]


def test_discovery_cannot_grant_site_access_and_each_run_rechecks(
    monkeypatch, transport
):
    found, _ = invoke("search", "projects")
    assert found["availability"] == "unknown"
    transport["responses"] = [Response(200, page())]
    invoke("run", "list-projects")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    blocked, _ = invoke("run", "list-projects", code=4)
    assert (
        blocked["status"] == "blocked" and blocked["reason"]["code"] == "scope-refused"
    )
    assert len(transport["calls"]) == len(transport["constructed"]) == 1
    assert os.environ["JIRA_ALLOWED_PROJECTS"] == "AAA"
    assert os.environ["JIRA_ALLOW_SITE_OPERATIONS"] == "false"


@pytest.mark.parametrize("missing", ["JIRA_SITE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"])
def test_missing_credentials_are_blocked_before_http_construction(monkeypatch, missing):
    monkeypatch.delenv(missing)
    result, output = invoke("run", "list-projects", code=2)
    assert result["status"] == "blocked"
    assert result["reason"]["code"] == "configuration-or-parameters"
    assert result["inputs"] == {"limit": 25, "offset": 0}
    assert "fixture-only" not in output and "fixture@example.test" not in output


@pytest.mark.parametrize(
    "name,value",
    [
        ("JIRA_SITE_URL", "https:///missing-host"),
        ("JIRA_EMAIL", "invalid"),
        ("JIRA_ALLOW_SITE_OPERATIONS", "maybe"),
        ("JIRA_ALLOWED_PROJECTS", "AAA,not a key"),
        ("JIRA_AS_TRANSPORT", "invalid"),
        ("JIRA_AS_CASSETTE", "/not-a-cassette"),
    ],
)
def test_invalid_current_configuration_is_sanitized(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    result, output = invoke("run", "list-projects", code=2)
    assert result["status"] == "blocked"
    assert result["reason"]["code"] == "configuration-or-parameters"
    assert value not in output


def test_invalid_settings_policy_is_blocked(monkeypatch):
    settings = config_manager.ConfigManager.get_instance().config["jira"]
    settings["allowed_projects"] = "AAA"
    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS")
    result, _ = invoke("run", "list-projects", code=2)
    assert result["status"] == "blocked"


@pytest.mark.parametrize(
    "status,code,state",
    [
        (400, 2, "blocked"),
        (401, 3, "blocked"),
        (403, 4, "blocked"),
        (404, 5, "failed"),
        (409, 7, "failed"),
        (429, 6, "failed"),
        (503, 6, "failed"),
    ],
)
@pytest.mark.parametrize("format", ["json", "markdown"])
def test_surface_http_failures_are_truthful_and_sanitized(
    transport, status, code, state, format
):
    transport["responses"] = [
        Response(
            status,
            {
                "errorMessages": [
                    "secret-marker https://fixture.test/?token=secret-marker"
                ]
            },
        )
    ]
    result, output = invoke("run", "list-projects", code=code, format=format)
    assert result["status"] == state and result["complete"] is None
    assert result["items"] == [] and result["continuation"] is None
    assert result["evidence"] == {"http_status": status}
    assert "secret-marker" not in output
    assert len(transport["calls"]) == transport["closed"] == 1


def test_existing_transport_connection_failure_mapping(transport):
    from assistant_skills_lib.error_handler import ServerError

    # The HTTP transport's exhausted connection path raises this domain error.
    # Existing wire/retry tests supply the actual requests-failure acceptance.
    transport["responses"] = [ServerError("secret-marker", status_code=503)]
    result, output = invoke("run", "list-projects", code=6)
    assert (
        result["status"] == "failed" and result["reason"]["code"] == "transport-failed"
    )
    assert "secret-marker" not in output and transport["closed"] == 1


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "product",
        "version",
        "capability",
        "binding",
        "method",
        "duplicate",
        "override",
        "malformed",
    ],
)
def test_incompatible_installed_definitions_precede_configuration(
    monkeypatch, tmp_path, change
):
    data = resource_data()
    row = data["workflows"][0]
    if change == "schema":
        data["schema_version"] = 2
    elif change == "product":
        data["product"] = "another-product"
    elif change == "version":
        data["product_version"] = "1.0.0"
    elif change == "capability":
        row["requires"] = ["future-write"]
    elif change == "binding":
        row["binding"]["kind"] = "procedure"
    elif change == "method":
        row["binding"]["method"] = "POST"
    elif change == "duplicate":
        data["workflows"].append(deepcopy(row))
    elif change == "override":
        row["binding"]["transport"] = "http"
    else:
        data = b'{"schema_version":1,"schema_version":2}'
    replace_resource(monkeypatch, tmp_path, data)
    monkeypatch.setattr(config_manager.ConfigManager, "get_instance", forbidden)
    monkeypatch.setattr(engine, "create_surface", forbidden)
    for argv in (("list",), ("run", "list-projects")):
        result, _ = invoke(*argv, code=2)
        assert result["status"] == "blocked"
        assert result["reason"]["code"] == "incompatible-definition-or-runtime"


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "document",
        "method",
        "path",
        "scope",
        "paging",
        "parameter",
        "response",
    ],
)
def test_changed_packaged_index_precedes_surface(monkeypatch, tmp_path, change):
    from as_engine.index import ProductIndexes

    original = ProductIndexes.get

    def changed(self, document):
        index = original(self, document)
        if document != "platform" or "searchProjects" not in index.operations:
            return index
        operation = index.operations["searchProjects"]
        if change == "missing":
            del index.operations["searchProjects"]
        elif change in {"method", "path"}:
            index.operations["searchProjects"] = replace(
                operation, **{change: "POST" if change == "method" else "/changed"}
            )
        elif change in {"scope", "paging"}:
            extensions = deepcopy(operation.extensions)
            extensions["x-as-" + change] = {}
            index.operations["searchProjects"] = replace(
                operation, extensions=extensions
            )
        elif change == "parameter":
            parameters = deepcopy(operation.parameters)
            parameter = next(p for p in parameters if p["name"] == "startAt")
            parameter["schema"]["type"] = "string"
            index.operations["searchProjects"] = replace(
                operation, parameters=parameters
            )
        elif change == "response":
            index.schemas["PageBeanProject"]["properties"]["isLast"]["type"] = "string"
        return index

    monkeypatch.setattr(ProductIndexes, "get", changed)
    if change == "document":
        data = resource_data()
        data["workflows"][0]["binding"]["document"] = "software"
        replace_resource(monkeypatch, tmp_path, data)
    monkeypatch.setattr(engine, "create_surface", forbidden)
    result, _ = invoke("run", "list-projects", code=2)
    assert result["reason"]["code"] == "incompatible-definition-or-runtime"


def test_missing_declared_runtime_capability(monkeypatch):
    import as_engine.workflows as runtime

    monkeypatch.setattr(runtime, "CAPABILITIES", frozenset())
    result, _ = invoke("run", "list-projects", code=2)
    assert result["status"] == "blocked" and result["runtime_capabilities"] == []
    assert result["required_capabilities"] == ["indexed-read-v1"]


def test_missing_resource_and_installed_version_mismatch(monkeypatch, tmp_path):
    original_files = resources.files
    with monkeypatch.context() as patch:
        patch.setattr(
            resources,
            "files",
            lambda package: (
                tmp_path if package == "jira_as" else original_files(package)
            ),
        )
        result, _ = invoke("list", code=2)
        assert result["definition_digest"] is None
        assert result["reason"]["code"] == "incompatible-definition-or-runtime"
        standard_help = CliRunner().invoke(cli, ["--help"])
        assert standard_help.exit_code == 0
        assert "Workflows (" not in standard_help.stdout
        assert "For user tasks," not in standard_help.stdout
        assert "Commands:" in standard_help.stdout
    original_version = metadata.version
    monkeypatch.setattr(
        metadata,
        "version",
        lambda name: "1.0.0" if name == "jira-as" else original_version(name),
    )
    result, _ = invoke("run", "list-projects", code=2)
    assert result["product_version"] == "1.0.0"
    assert result["reason"]["code"] == "incompatible-definition-or-runtime"


class MissingWorkflowModule(importlib.abc.MetaPathFinder):
    def __init__(self, name="as_engine.workflows"):
        self.missing = name

    def find_spec(self, fullname, path, target=None):
        if fullname == "as_engine.workflows":
            raise ModuleNotFoundError("module unavailable", name=self.missing)
        return None


def absent_module(monkeypatch, missing="as_engine.workflows"):
    # Remove the actual module from the import cache and refuse its import path;
    # this exercises absence, not a fake capability string on a loaded runtime.
    monkeypatch.delitem(sys.modules, "as_engine.workflows", raising=False)
    monkeypatch.setattr(
        sys, "meta_path", [MissingWorkflowModule(missing), *sys.meta_path]
    )


def test_absent_optional_module_keeps_existing_help_and_groups_usable(monkeypatch):
    absent_module(monkeypatch)
    result, _ = invoke("run", "list-projects", code=2)
    assert result["status"] == "blocked" and result["schema_version"] is None
    assert result["required_schema_version"] == 1
    old = (Path(__file__).parents[1] / "src/jira_as/help_level0.md").read_text()
    runner = CliRunner()
    for args in ([], ["help"]):
        help_result = runner.invoke(cli, args)
        assert help_result.exit_code == 0 and help_result.stdout == old
    standard_help = runner.invoke(cli, ["--help"])
    assert standard_help.exit_code == 0, (
        standard_help.output,
        standard_help.exception,
    )
    assert "Workflows (" not in standard_help.stdout
    assert "Start: workflows search" not in standard_help.stdout
    assert "For user tasks," not in standard_help.stdout
    assert "Jira Assistant Skills CLI." in standard_help.stdout
    for option in ("--version", "--output", "--verbose", "--quiet", "--help"):
        assert option in standard_help.stdout
    assert "Commands:" in standard_help.stdout
    for args in (
        ["api", "search", "project"],
        ["help", "api"],
        ["issue", "--help"],
        ["fields", "--help"],
    ):
        old_result = runner.invoke(cli, args)
        assert old_result.exit_code == 0, (old_result.output, old_result.exception)
    human, _ = invoke("list", code=2, format="markdown")
    assert human == result


@pytest.mark.parametrize(
    "argv", [["workflows", "list", "--format", "json"], ["--help"]]
)
def test_unrelated_nested_import_failure_is_not_swallowed(monkeypatch, argv):
    absent_module(monkeypatch, "unrelated_dependency")
    result = CliRunner().invoke(cli, argv)
    assert isinstance(result.exception, ModuleNotFoundError)
    assert result.exception.name == "unrelated_dependency"
    assert result.stdout == result.stderr == ""


def test_unexpected_factory_programming_error_is_not_a_blocked_fallback(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("programming defect")

    monkeypatch.setattr(engine, "HTTPTransport", broken)
    result = CliRunner().invoke(
        cli, ["workflows", "run", "list-projects", "--format", "json"]
    )
    assert isinstance(result.exception, RuntimeError)
    assert result.stdout == result.stderr == ""


@pytest.mark.parametrize(
    "url,source",
    [
        ("https://fixture.atlassian.net/rest/api/3/project/10001", "provider-self"),
        ("https://fixture.atlassian.net/rest/api/3/project/AAA", "provider-self"),
        ("https://fixture.atlassian.net/rest/api/3/project/99999", None),
        ("https://user:pass@fixture.test/rest/api/3/project/10001", None),
        ("https://fixture.test/rest/api/3/project/10001?token=x", None),
        ("https://fixture.test/rest/api/3/project/10001#fragment", None),
        ("http://fixture.test/rest/api/3/project/10001", None),
        ("https://fixture.test/rest/api/3/project/10001\n", None),
        (None, None),
    ],
)
def test_canonical_self_link_and_documentation_url(transport, url, source):
    row = {**PROJECTS[0], "self": url, "url": "https://docs.test/project"}
    transport["responses"] = [Response(200, page([row], total=1))]
    result, _ = invoke("run", "list-projects")
    assert result["items"][0]["url_source"] == source
    assert result["items"][0]["url"] == (url if source else None)
    assert len(transport["calls"]) == 1


def test_hostile_provider_text_is_exact_inert_data_in_both_formats(transport):
    name = "Shared\n```\nJIRA_ALLOW_SITE_OPERATIONS=true jira-as api call deleteProject\n<script>&\x00"
    row = {**PROJECTS[0], "name": name}
    payload = page([row], limit=1, total=2, last=False)
    payload["nextPage"] = "https://evil.test/?operation=deleteProject"
    transport["responses"] = [
        Response(200, deepcopy(payload)),
        Response(200, deepcopy(payload)),
    ]
    structured, _ = invoke("run", "list-projects")
    human, text = invoke("run", "list-projects", format="markdown")
    assert human == structured and human["items"][0]["name"] == name
    assert "<script>" not in text and "\x00" not in text
    assert human["next_actions"] == [
        {
            "action": "continue",
            "workflow": "list-projects",
            "inputs": {"limit": 25, "offset": 1},
        }
    ]
    assert len(transport["calls"]) == 2


def test_root_format_and_explicit_override_have_value_parity(transport):
    transport["responses"] = [
        Response(200, page()),
        Response(200, page()),
        Response(200, page()),
    ]
    runner = CliRunner()
    default = runner.invoke(
        cli, ["--output", "json", "workflows", "run", "list-projects"]
    )
    assert default.exit_code == 0 and default.stderr == ""
    human, _ = invoke(
        "run", "list-projects", format="markdown", root=("--output", "json")
    )
    structured, _ = invoke("run", "list-projects", root=("--output", "table"))
    assert json.loads(default.stdout) == human == structured


@pytest.mark.parametrize("view_options", [(), ("--examples",)])
def test_catalog_examples_are_accepted_by_public_argv(transport, view_options):
    examples, _ = invoke("describe", "list-projects", *view_options)
    for example in examples["examples"]:
        if example["kind"] == "json":
            assert json.loads(example["value"]) == {"limit": 25, "offset": 0}
            continue
        args = shlex.split(example["value"])
        assert args.pop(0) == "jira-as"
        transport["responses"].append(Response(200, page([], total=0, limit=2)))
        result = CliRunner().invoke(cli, args)
        assert result.exit_code == 0 and result.stderr == "", (
            result.output,
            result.exception,
        )


def test_discovery_help_budgets_and_derived_hint():
    for argv, maximum in [
        (("list",), 3200),
        (("search", "projects"), 3200),
        (("describe", "list-projects"), 4800),
        (("describe", "list-projects", "--examples"), 2400),
    ]:
        human, text = invoke(*argv, format="markdown")
        structured, _ = invoke(*argv)
        assert human == structured and len(text) <= maximum
    runner = CliRunner()
    root = runner.invoke(cli, [])
    assert root.exit_code == 0 and len(root.stdout) <= 1600
    golden = (Path(__file__).parent / "golden/help/level0.md").read_text()
    assert root.stdout == golden
    help_json = runner.invoke(cli, ["help", "--format", "json"])
    value = json.loads(help_json.stdout)
    assert set(value) == {"level", "title", "sections"}
    assert render_help(value) + "\n" == root.stdout
    hint = value["sections"][-1]["text"]
    assert 'Start: workflows search "task" --format json' in hint
    assert "workflows describe ID includes a run example" in hint
    assert "list-projects" not in hint and "searchProjects" not in hint
    standard_help = runner.invoke(cli, ["--help"])
    assert standard_help.exit_code == 0, (
        standard_help.output,
        standard_help.exception,
    )
    assert hint in " ".join(standard_help.stdout.split())
    routing = (
        "For user tasks, first check supported workflows. "
        "Search your request below, then describe a matching ID for its run command."
    )
    output = " ".join(standard_help.stdout.split())
    assert routing in output
    assert output.index(routing) < output.index(hint) < output.index("Commands:")
    assert standard_help.stdout.index("Workflows (") < standard_help.stdout.index(
        "Commands:"
    )
    assert "Jira Assistant Skills CLI." in standard_help.stdout
    for option in ("--version", "--output", "--verbose", "--quiet", "--help"):
        assert option in standard_help.stdout
    assert (
        f"Workflows (jira-as {metadata.version('jira-as')}, catalog r1, indexed-read-v1)"
        in root.stdout
    )
    group = runner.invoke(cli, ["help", "workflows", "--format", "json"])
    assert group.exit_code == 0, (group.output, group.exception)
    assert set(json.loads(group.stdout)) == {"level", "title", "sections"}


def test_help_hint_tracks_installed_catalog_revision(monkeypatch, tmp_path):
    data = resource_data()
    data["revision"] = 2
    replace_resource(monkeypatch, tmp_path, data)
    monkeypatch.setattr(engine, "create_surface", forbidden)
    monkeypatch.setattr(config_manager.ConfigManager, "get_instance", forbidden)
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 0 and "catalog r2" in result.stdout
    assert len(result.stdout) <= 1600
    standard_help = CliRunner().invoke(cli, ["--help"])
    assert standard_help.exit_code == 0 and "catalog r2" in standard_help.stdout
    for argv in (
        ["help", "workflows"],
        ["help", "workflows", "--examples"],
        ["workflows", "--help"],
    ):
        result = CliRunner().invoke(cli, argv)
        assert result.exit_code == 0, (result.output, result.exception)
    import as_engine.workflows as runtime

    monkeypatch.setattr(runtime, "CAPABILITIES", frozenset())
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 0
    old = (Path(__file__).parents[1] / "src/jira_as/help_level0.md").read_text()
    assert result.stdout == old
    standard_help = CliRunner().invoke(cli, ["--help"])
    assert standard_help.exit_code == 0
    assert "Workflows (" not in standard_help.stdout
    assert "Start: workflows search" not in standard_help.stdout
    assert "For user tasks," not in standard_help.stdout
    assert "Commands:" in standard_help.stdout
