"""Public MCP over the real installed Jira CLI with controlled provider inputs.

Mandatory SDK imports; no live Jira, synthesized workflow envelopes, or native
ChatGPT proof. The fixed child launcher changes only configuration sources and
HTTPTransport construction. Parser, ConfigManager, indexes, Surface and workflow
logic run from the current installed packages, including editable test installs.
"""

import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import sysconfig
from importlib import metadata, resources
from pathlib import Path
from textwrap import dedent

import as_engine
import mcp_types
import pytest
from as_engine.workflow_mcp import create_server, load_profile
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.shared.exceptions import MCPError
from mcp_types.version import LATEST_HANDSHAKE_VERSION

import jira_as

from . import workflow_scenarios as scenarios

TOOLS = [
    "workflows_list",
    "workflows_search",
    "workflows_describe",
    "workflows_run",
]
FAKE_CONTEXT = {
    "JIRA_SITE_URL": "https://fixture.atlassian.net",
    "JIRA_EMAIL": "fixture@example.test",
    "JIRA_API_TOKEN": "fixture-only-secret-marker",
    "JIRA_ALLOWED_PROJECTS": "AAA",
    "JIRA_ALLOW_SITE_OPERATIONS": "true",
}
ROUTING_NAMES = {
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "PYTHONPATH",
    "PYTHONHOME",
}


def forbidden(*_args, **_kwargs):
    pytest.fail("unexpected network access")


@pytest.fixture(autouse=True)
def isolated_context(monkeypatch):
    for name in tuple(os.environ):
        if (
            name.startswith(("JIRA_", "OPENAI_"))
            or name in {"SITE_URL", "EMAIL", "API_TOKEN"} | ROUTING_NAMES
        ):
            monkeypatch.delenv(name)
    for name, value in FAKE_CONTEXT.items():
        monkeypatch.setenv(name, value)
    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


@pytest.fixture
def pilot(tmp_path):
    root = tmp_path.resolve()
    root.chmod(0o700)
    console = (Path(sysconfig.get_path("scripts")) / "jira-as").resolve(strict=True)
    assert console.is_file() and os.access(console, os.X_OK)
    # Fail rather than silently execute a console script from another interpreter.
    assert console.read_text().splitlines()[0] == f"#!{sys.executable}"
    console_hash = hashlib.sha256(console.read_bytes()).hexdigest()
    raw = resources.files("jira_as").joinpath("workflows.json").read_bytes()
    catalog = json.loads(raw)
    assert catalog["product"] == "jira-as"
    assert catalog["product_version"] == metadata.version("jira-as")
    assert [row["id"] for row in catalog["workflows"]] == ["list-projects"]
    expected = {
        "product_version": metadata.version("jira-as"),
        "engine_version": metadata.version("as-engine"),
        "schema_version": catalog["schema_version"],
        "catalog_revision": catalog["revision"],
        "definition_digest": hashlib.sha256(raw).hexdigest(),
        "workflow_revisions": {"list-projects": catalog["workflows"][0]["revision"]},
    }
    origins = {
        "jira_as": str(Path(jira_as.__file__).resolve()),
        "as_engine": str(Path(as_engine.__file__).resolve()),
        "product_version": expected["product_version"],
        "engine_version": expected["engine_version"],
        "definition_digest": expected["definition_digest"],
        "console": str(console),
        "console_sha256": console_hash,
        "interpreter": sys.executable,
    }
    data = root / "provider.json"
    evidence = root / "requests.jsonl"
    launcher = root / "fixed-jira"
    # Paths are source literals in this test-owned launcher, never tool arguments
    # or production environment exceptions. Each child reads fresh provider data.
    launcher.write_text(
        f"#!{sys.executable} -I\n"
        + dedent(f"""\
        import hashlib
        import json
        import os
        import runpy
        import socket
        import sys
        from importlib import metadata, resources
        from pathlib import Path

        DATA = Path({str(data)!r})
        EVIDENCE = Path({str(evidence)!r})
        CONSOLE = Path({str(console)!r})

        def record(event, **values):
            with EVIDENCE.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({{"event": event, **values}}) + "\\n")

        def forbidden(*args, **kwargs):
            record("forbidden-access")
            raise AssertionError("unexpected configuration or network access")

        record("launch", argv=sys.argv[1:], names=sorted(os.environ),
               projects=os.environ.get("JIRA_ALLOWED_PROJECTS"),
               site=os.environ.get("JIRA_ALLOW_SITE_OPERATIONS"),
               account=os.environ.get("JIRA_EMAIL"),
               origin=os.environ.get("JIRA_SITE_URL"))
        for name in ("connect", "connect_ex", "sendto"):
            setattr(socket.socket, name, forbidden)
        socket.create_connection = forbidden
        socket.getaddrinfo = forbidden

        import dotenv
        import requests
        dotenv.load_dotenv = lambda *args, **kwargs: False
        dotenv.dotenv_values = lambda *args, **kwargs: {{}}
        requests.Session.send = forbidden

        import as_engine
        import jira_as
        from as_engine.transport import Response
        from jira_as import config_manager, engine

        config_manager.ConfigManager._instances = {{}}
        config_manager.ConfigManager._find_claude_dir = lambda self: None
        config_manager.is_keychain_available = lambda: False
        config = json.loads(DATA.read_text())
        # Deliberately unavailable product configuration is injected only after
        # adapter admission, to distinguish product mapping from admission refusal.
        for name in config.get("remove_env", []):
            assert name in ("JIRA_SITE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
            os.environ.pop(name, None)

        class ControlledTransport:
            def __init__(self, base_url, **settings):
                self.called = False
                record("constructed", base_url=base_url)

            def call(self, operation, parameters, body):
                record("request", operation=operation.operationId,
                       method=operation.method, path=operation.path,
                       parameters=dict(parameters), body=body)
                assert operation.method == "GET", "workflow attempted a write"
                assert not self.called, "unexpected additional transport call"
                self.called = True
                matches = [row for row in config["responses"]
                           if row["offset"] == parameters["startAt"]]
                assert len(matches) == 1, "unexpected provider request"
                row = matches[0]
                return Response(row["status"], row["payload"])

            def close(self):
                record("closed")

        engine.HTTPTransport = ControlledTransport
        assert hashlib.sha256(CONSOLE.read_bytes()).hexdigest() == {console_hash!r}
        record("origins", jira_as=str(Path(jira_as.__file__).resolve()),
               as_engine=str(Path(as_engine.__file__).resolve()),
               product_version=metadata.version("jira-as"),
               engine_version=metadata.version("as-engine"),
               definition_digest=hashlib.sha256(
                   resources.files("jira_as").joinpath("workflows.json").read_bytes()
               ).hexdigest(), console=str(CONSOLE),
               console_sha256=hashlib.sha256(CONSOLE.read_bytes()).hexdigest(),
               interpreter=sys.executable)
        try:
            runpy.run_path(str(CONSOLE), run_name="__main__")
        finally:
            record("finished")
    """)
    )
    launcher.chmod(0o700)
    document = {
        "schema_version": 1,
        "adapter_id": "fixture-jira-workflows",
        "product": "jira-as",
        "executable": str(launcher),
        "executable_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
        "expected": expected,
        "context": {
            "source": "approved-env-v1",
            "account_email": FAKE_CONTEXT["JIRA_EMAIL"],
            "site_url": FAKE_CONTEXT["JIRA_SITE_URL"],
            "home": str(root),
            "cwd": str(root),
            "tmpdir": str(root),
            "scope": {"allowed_projects": ["AAA"], "allow_site_operations": True},
        },
        "limits": {"call_timeout_seconds": 30, "discovery_timeout_seconds": 30},
    }
    profile_path = root / "profile.json"
    profile_path.write_text(json.dumps(document))
    profile_path.chmod(0o600)
    value = {
        "root": root,
        "data": data,
        "evidence": evidence,
        "launcher": launcher,
        "profile_path": profile_path,
        "document": document,
        "origins": origins,
    }
    set_provider(value, scenarios.ORDINARY.payloads())
    return value


def set_provider(pilot, payloads, *, offsets=(0,), status=200, remove_env=()):
    assert len(payloads) == len(offsets)
    pilot["data"].write_text(
        json.dumps(
            {
                "responses": [
                    {"offset": offset, "status": status, "payload": payload}
                    for offset, payload in zip(offsets, payloads)
                ],
                "remove_env": list(remove_env),
            }
        )
    )


def save_profile(pilot):
    pilot["profile_path"].write_text(json.dumps(pilot["document"]))


def events(pilot):
    if not pilot["evidence"].exists():
        return []
    return [json.loads(line) for line in pilot["evidence"].read_text().splitlines()]


def requests_in(rows):
    return [
        (row["operation"], row["method"], row["path"], row["parameters"], row["body"])
        for row in rows
        if row["event"] == "request"
    ]


def assert_child(pilot, rows):
    assert not any(row["event"] == "forbidden-access" for row in rows)
    assert [row for row in rows if row["event"] == "origins"] == [
        {"event": "origins", **pilot["origins"]}
    ]
    assert len([row for row in rows if row["event"] == "launch"]) == 1
    assert len([row for row in rows if row["event"] == "finished"]) == 1
    assert len([row for row in rows if row["event"] == "constructed"]) == len(
        [row for row in rows if row["event"] == "closed"]
    )


def envelope(result, tool):
    assert isinstance(result, mcp_types.CallToolResult)
    assert len(result.content) == 1 and result.content[0].type == "text"
    value = result.structured_content
    assert json.loads(result.content[0].text) == value
    wire = result.model_dump(by_alias=True)
    assert wire["structuredContent"] == value
    assert wire["isError"] is (
        value.get("status") == "adapter-error" or value.get("exit_code", 0) != 0
    )
    assert "structured_content" not in wire and "is_error" not in wire
    Draft202012Validator(tool.output_schema).validate(value)
    scenarios.assert_no_secret_markers(
        result.content[0].text, FAKE_CONTEXT["JIRA_API_TOKEN"]
    )
    return value


async def listed_tools(client):
    assert client.protocol_version == LATEST_HANDSHAKE_VERSION == "2025-11-25"
    listed = await client.list_tools()
    assert [tool.name for tool in listed.tools] == TOOLS
    for tool in listed.tools:
        Draft202012Validator.check_schema(tool.input_schema)
        Draft202012Validator.check_schema(tool.output_schema)
        assert tool.input_schema["additionalProperties"] is False
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
    return {tool.name: tool for tool in listed.tools}


async def paired_call(
    pilot, profile, client, tool, args, argv, *, code=0, offsets=(), limit=25
):
    before = len(events(pilot))
    direct = subprocess.run(
        [str(pilot["launcher"]), "workflows", argv[0], "--format=json", *argv[1:]],
        cwd=pilot["root"],
        env=profile.environment(run=tool.name == "workflows_run"),
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert direct.returncode == code, (direct.stdout, direct.stderr)
    assert (direct.stdout if code else direct.stderr) == ""
    expected = json.loads(direct.stderr if code else direct.stdout)
    direct_rows = events(pilot)[before:]
    before = len(events(pilot))
    result = await client.call_tool(tool.name, args)
    actual = envelope(result, tool)
    assert actual == expected
    scenarios.assert_exit_code(actual, code)
    mcp_rows = events(pilot)[before:]
    for rows in (direct_rows, mcp_rows):
        assert_child(pilot, rows)
        requests = requests_in(rows)
        if limit == 25:
            scenarios.assert_project_requests(requests, offsets)
        else:
            # The shared request oracle fixes maxResults=25; this explicit limit2
            # check adds the overflow request contract without changing that oracle.
            assert limit == 2 and offsets == (0,)
            assert requests == [
                (
                    "searchProjects",
                    "GET",
                    "/rest/api/3/project/search",
                    {"orderBy": "key", "action": "view", "maxResults": 2, "startAt": 0},
                    None,
                )
            ]
    assert requests_in(direct_rows) == requests_in(mcp_rows)
    return actual, result, mcp_rows


def assert_bootstrap(pilot, rows):
    assert requests_in(rows) == []
    assert not any(row["event"] in {"forbidden-access", "constructed"} for row in rows)
    launches = [row for row in rows if row["event"] == "launch"]
    assert [row["argv"][1] for row in launches] in (["list"], ["list", "describe"])
    assert all(not set(FAKE_CONTEXT).intersection(row["names"]) for row in launches)
    assert [row for row in rows if row["event"] == "origins"] == [
        {"event": "origins", **pilot["origins"]} for _ in launches
    ]
    assert len([row for row in rows if row["event"] == "finished"]) == len(launches)


async def server_client(pilot):
    profile = load_profile(pilot["profile_path"])
    before = len(events(pilot))
    server = await create_server(profile)
    assert_bootstrap(pilot, events(pilot)[before:])
    return profile, Client(server, mode="legacy", raise_exceptions=True)


async def read_pair(pilot, *, code=0, inputs=None, offsets=(0,)):
    profile, connection = await server_client(pilot)
    async with connection as client:
        tools = await listed_tools(client)
        args = {"workflow": "list-projects"}
        values = {"limit": 25, "offset": 0, **(inputs or {})}
        if inputs is not None:
            args["inputs"] = inputs
        return await paired_call(
            pilot,
            profile,
            client,
            tools["workflows_run"],
            args,
            (
                "run",
                f"--limit={values['limit']}",
                f"--offset={values['offset']}",
                "--",
                "list-projects",
            ),
            code=code,
            offsets=offsets,
            limit=values["limit"],
        )


def test_installed_catalog_discovery_and_ordinary_read(pilot):
    async def check():
        profile, connection = await server_client(pilot)
        async with connection as client:
            tools = await listed_tools(client)
            for name, args, argv in (
                ("list", {}, ("list",)),
                (
                    "search",
                    {"query": "What Jira projects can I see?"},
                    ("search", "What Jira projects can I see?"),
                ),
                ("search", {"query": "-projects"}, ("search", "--", "-projects")),
                (
                    "describe",
                    {"workflow": "list-projects"},
                    ("describe", "list-projects"),
                ),
                (
                    "describe",
                    {"workflow": "list-projects", "examples": True},
                    ("describe", "--examples", "list-projects"),
                ),
            ):
                value, _, rows = await paired_call(
                    pilot, profile, client, tools["workflows_" + name], args, argv
                )
                for key, expected in pilot["document"]["expected"].items():
                    if key != "workflow_revisions":
                        assert value[key] == expected
                assert value["availability"] == "unknown"
                launch = next(row for row in rows if row["event"] == "launch")
                assert not set(FAKE_CONTEXT).intersection(launch["names"])
                if name == "describe" and not args.get("examples"):
                    run_schema = tools["workflows_run"].input_schema
                    assert run_schema["properties"]["workflow"]["enum"] == [
                        "list-projects"
                    ]
                    assert (
                        run_schema["properties"]["inputs"]["additionalProperties"]
                        is False
                    )
                    assert (
                        run_schema["properties"]["inputs"]["properties"]
                        == value["inputs"]
                    )
                    assert value["binding"]["operation_id"] == "searchProjects"
                    assert value["binding"]["scope"] == {"in": "site"}
            value, _, _ = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects"},
                ("run", "list-projects"),
                offsets=(0,),
            )
            # Account-visible projects outside the fake AAA project allowlist
            # remain visible under the separately admitted site-read permission.
            assert [row["key"] for row in value["items"]] == [
                row["key"] for row in scenarios.ORDINARY.payload()["values"]
            ]
            assert value["complete"] is True and value["continuation"] is None
            assert value["returned_count"] == 3

    asyncio.run(check())


def test_reduced_page_pair_uses_same_items_requests_and_continuation(pilot):
    set_provider(pilot, scenarios.REDUCED_PAGE.payloads(), offsets=(0, 2))

    async def check():
        profile, connection = await server_client(pilot)
        async with connection as client:
            tools = await listed_tools(client)
            first, _, first_rows = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects"},
                ("run", "list-projects"),
                offsets=(0,),
            )
            scenarios.assert_reduced_first(first)
            second, _, second_rows = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                first["continuation"],
                ("run", "--limit=25", "--offset=2", "list-projects"),
                offsets=(2,),
            )
            scenarios.assert_reduced_second(second)
            scenarios.assert_reduced_items(first, second)
            scenarios.assert_project_requests(
                requests_in(first_rows + second_rows), (0, 2)
            )

    asyncio.run(check())


def test_default_bound_27_projects_requires_explicit_second_call(pilot):
    set_provider(pilot, scenarios.DEFAULT_BOUND.payloads(), offsets=(0, 25))

    async def check():
        profile, connection = await server_client(pilot)
        async with connection as client:
            tools = await listed_tools(client)
            first, _, rows = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects"},
                ("run", "list-projects"),
                offsets=(0,),
            )
            scenarios.assert_default_bound_first(first)
            assert len(requests_in(rows)) == 1
            final, _, rows = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects", "inputs": {"offset": 25}},
                ("run", "--offset=25", "list-projects"),
                offsets=(25,),
            )
            scenarios.assert_default_bound_final(first, final)
            assert len(requests_in(rows)) == 1

    asyncio.run(check())


@pytest.mark.parametrize(
    "case", scenarios.EMPTY_AND_INCOMPLETE, ids=lambda case: case.name
)
def test_empty_and_unknown_completion_matches_cli(pilot, case):
    set_provider(pilot, case.payloads())
    value, _, _ = asyncio.run(read_pair(pilot, code=case.code))
    scenarios.assert_empty_or_incomplete(value, case.complete, case.reason)


@pytest.mark.parametrize("field,value", scenarios.CONTRADICTORY_METADATA)
def test_contradictory_provider_metadata_matches_cli(pilot, field, value):
    set_provider(pilot, [scenarios.contradictory_page(field, value)])
    value, _, _ = asyncio.run(read_pair(pilot, code=1))
    scenarios.assert_contradictory_metadata(value)


@pytest.mark.parametrize("case", scenarios.MALFORMED_PAGES, ids=lambda case: case.name)
def test_malformed_and_duplicate_provider_identity_matches_cli(pilot, case):
    set_provider(pilot, case.payloads())
    value, _, _ = asyncio.run(read_pair(pilot, code=case.code))
    scenarios.assert_unknown_page(value)


def test_overflow_keeps_received_and_omitted_evidence(pilot):
    set_provider(pilot, scenarios.OVERFLOW.payloads())
    value, _, _ = asyncio.run(read_pair(pilot, code=1, inputs={"limit": 2}))
    scenarios.assert_overflow(value)


@pytest.mark.parametrize("url,source", scenarios.LINK_CASES)
def test_provider_links_match_cli(pilot, url, source):
    set_provider(pilot, [scenarios.link_page(url)])
    value, _, _ = asyncio.run(read_pair(pilot))
    scenarios.assert_canonical_link(value, url, source)


def test_hostile_provider_name_is_inert_exact_data(pilot):
    set_provider(pilot, scenarios.HOSTILE_TEXT.payloads())
    value, result, _ = asyncio.run(read_pair(pilot))
    scenarios.assert_hostile_text(value)
    text = result.content[0].text
    assert "<script>" not in text and "\x00" not in text and "```" not in text


@pytest.mark.parametrize("case", scenarios.HTTP_FAILURES, ids=lambda case: case.name)
def test_http_failure_status_exit_and_sanitization_match_cli(pilot, case):
    set_provider(pilot, case.payloads(), status=case.http_status)
    value, result, _ = asyncio.run(read_pair(pilot, code=case.code))
    scenarios.assert_http_failure(value, case.http_status, case.status)
    scenarios.assert_no_secret_markers(result.content[0].text, "secret-marker")


def test_explicit_empty_project_scope_and_false_site_policy_reach_real_guard(
    pilot, monkeypatch
):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    pilot["document"]["context"]["scope"] = {
        "allowed_projects": [],
        "allow_site_operations": False,
    }
    save_profile(pilot)
    value, _, rows = asyncio.run(
        read_pair(pilot, code=scenarios.SCOPE_DENIED.code, offsets=())
    )
    scenarios.assert_failure(
        value, scenarios.SCOPE_DENIED.status, scenarios.SCOPE_DENIED.reason
    )
    launch = next(row for row in rows if row["event"] == "launch")
    assert launch["projects"] == "" and launch["site"] == "false"
    assert requests_in(rows) == []


def test_explicit_empty_projects_with_site_read_is_not_missing_context(
    pilot, monkeypatch
):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "")
    pilot["document"]["context"]["scope"]["allowed_projects"] = []
    save_profile(pilot)
    value, _, rows = asyncio.run(read_pair(pilot))
    assert [row["key"] for row in value["items"]] == [
        row["key"] for row in scenarios.ORDINARY.payload()["values"]
    ]
    launch = next(row for row in rows if row["event"] == "launch")
    assert launch["projects"] == "" and launch["site"] == "true"


def assert_admission_refusal(value, code):
    assert value["status"] == "adapter-error"
    error = value["error"]
    assert error["code"] == code and error["phase"] == "admission"
    assert error["cleanup"] == "not-started" and error["child_exit_code"] is None
    assert error["stdout_bytes"] == error["stderr_bytes"] == 0
    assert error["counts_complete"] is True
    assert error["dispatch_blocked"] is False


async def refused_run(pilot, code, args=None):
    _, connection = await server_client(pilot)
    async with connection as client:
        tools = await listed_tools(client)
        before = events(pilot)
        result = await client.call_tool(
            "workflows_run", {"workflow": "list-projects"} if args is None else args
        )
        value = envelope(result, tools["workflows_run"])
        assert_admission_refusal(value, code)
        assert events(pilot) == before
        launches = [row for row in before if row["event"] == "launch"]
        assert len(launches) == 2
        assert [row["argv"][1] for row in launches] == ["list", "describe"]
        assert requests_in(before) == []


@pytest.mark.parametrize("missing", list(FAKE_CONTEXT))
def test_missing_context_refuses_before_run_child(pilot, monkeypatch, missing):
    monkeypatch.delenv(missing)
    asyncio.run(refused_run(pilot, "runtime-context-unavailable"))


@pytest.mark.parametrize(
    "name,value",
    [
        ("JIRA_EMAIL", "other@example.test"),
        ("JIRA_SITE_URL", "https://other.atlassian.net"),
        ("JIRA_ALLOWED_PROJECTS", "SBX"),
        ("JIRA_ALLOW_SITE_OPERATIONS", "false"),
        ("JIRA_DEFAULT_PROJECT", "AAA"),
    ],
)
def test_mismatched_account_site_or_scope_refuses_before_run(
    pilot, monkeypatch, name, value
):
    monkeypatch.setenv(name, value)
    asyncio.run(refused_run(pilot, "identity-binding-mismatch"))


@pytest.mark.parametrize(
    "args",
    [
        {"workflow": "list-projects", "env": {"JIRA_ALLOW_SITE_OPERATIONS": "true"}},
        {"workflow": "list-projects", "command": "jira-as"},
        {"workflow": "list-projects", "executable": "/bin/echo"},
        {"workflow": "list-projects", "argv": ["--allow-site"]},
        {"workflow": "list-projects", "transport": "responder"},
        {"workflow": "list-projects", "credentials": "not-authority"},
        {"workflow": "list-projects", "inputs": {"site": "https://other.test"}},
        {"workflow": "list-projects", "inputs": {"limit": True}},
        {"workflow": "list-projects", "inputs": {"limit": 25.0}},
        {"workflow": "list-projects", "inputs": {"offset": -1}},
        {"workflow": "list-projects", "inputs": None},
    ],
)
def test_model_cannot_select_authority_or_coerce_inputs(pilot, args):
    asyncio.run(refused_run(pilot, "invalid-input", args))


def test_unknown_tool_and_workflow_have_distinct_errors(pilot):
    async def check():
        _, connection = await server_client(pilot)
        async with connection as client:
            tools = await listed_tools(client)
            before = events(pilot)
            with pytest.raises(MCPError) as error:
                await client.call_tool("arbitrary_shell", {})
            assert error.value.code == -32602
            result = await client.call_tool(
                "workflows_run", {"workflow": "delete-project"}
            )
            assert_admission_refusal(
                envelope(result, tools["workflows_run"]), "unsupported-workflow"
            )
            assert events(pilot) == before

    asyncio.run(check())


@pytest.mark.parametrize("missing", ["JIRA_SITE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"])
def test_product_configuration_failure_after_valid_adapter_admission(pilot, missing):
    # The launcher removes this fake product source after the adapter snapshots
    # valid fake authority. The resulting product failure is not admission proof.
    set_provider(pilot, scenarios.ORDINARY.payloads(), remove_env=(missing,))
    value, result, _ = asyncio.run(read_pair(pilot, code=2, offsets=()))
    scenarios.assert_failure(value, "blocked", "configuration-or-parameters")
    scenarios.assert_no_secret_markers(
        result.content[0].text,
        FAKE_CONTEXT["JIRA_API_TOKEN"],
        FAKE_CONTEXT["JIRA_EMAIL"],
    )


def test_loaded_profile_keeps_context_snapshot_and_drops_unrelated_secrets(
    pilot, monkeypatch
):
    async def check():
        profile, connection = await server_client(pilot)
        monkeypatch.setenv("JIRA_EMAIL", "other@example.test")
        monkeypatch.setenv("JIRA_SITE_URL", "https://other.atlassian.net")
        monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
        monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "tunnel-secret-marker")
        monkeypatch.setenv("PYTHONPATH", "/not-a-routing-option")
        # A caller's mutable document copy is not the validated profile snapshot.
        copy = profile.document
        copy["context"]["scope"]["allow_site_operations"] = False
        async with connection as client:
            tools = await listed_tools(client)
            _, result, rows = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects"},
                ("run", "list-projects"),
                offsets=(0,),
            )
            launch = next(row for row in rows if row["event"] == "launch")
            assert launch["account"] == FAKE_CONTEXT["JIRA_EMAIL"]
            assert launch["origin"] == FAKE_CONTEXT["JIRA_SITE_URL"]
            assert launch["projects"] == "AAA" and launch["site"] == "true"
            assert not {"OPENAI_API_KEY", "PYTHONPATH"}.intersection(launch["names"])
            scenarios.assert_no_secret_markers(
                result.content[0].text, "tunnel-secret-marker"
            )

    asyncio.run(check())


@pytest.mark.parametrize(
    "field", ["product_version", "engine_version", "definition_digest"]
)
def test_wrong_operator_package_or_catalog_binding_blocks_bootstrap(pilot, field):
    # Change operator expectations, never installed metadata or workflow functions.
    expected = pilot["document"]["expected"]
    if field == "definition_digest":
        expected[field] = "0" * 64 if expected[field] != "0" * 64 else "1" * 64
    else:
        expected[field] += "-wrong"
    save_profile(pilot)

    async def check():
        _, connection = await server_client(pilot)
        async with connection as client:
            tools = await listed_tools(client)
            run = tools["workflows_run"].input_schema
            assert "enum" not in run["properties"]["workflow"]
            assert run["properties"]["inputs"]["properties"] == {}
            before = events(pilot)
            assert len([row for row in before if row["event"] == "launch"]) == 1
            assert requests_in(before) == []
            result = await client.call_tool("workflows_list", {})
            value = envelope(result, tools["workflows_list"])
            assert value["error"]["code"] == "incompatible-output"
            assert value["error"]["phase"] == "bootstrap"
            assert value["error"]["cleanup"] == "reaped"
            assert value["error"]["child_exit_code"] == 0
            assert value["error"]["dispatch_blocked"] is True
            again = await client.call_tool(
                "workflows_run", {"workflow": "list-projects"}
            )
            assert envelope(again, tools["workflows_run"]) == value
            assert events(pilot) == before

    asyncio.run(check())


def test_sdk_stdio_initialization_tools_and_real_installed_read(pilot):
    async def check():
        profile = load_profile(pilot["profile_path"])
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                "-I",
                "-m",
                "as_engine.workflow_mcp",
                "--profile",
                str(pilot["profile_path"]),
            ],
            cwd=pilot["root"],
            env=profile.environment(run=True),
        )
        # Use the SDK transport's framed reader, not asyncio's default 64 KiB
        # readline limit. The engine raw-wire battery owns its explicit frame cap.
        async with Client(parameters, mode="legacy", read_timeout_seconds=45) as client:
            assert_bootstrap(pilot, events(pilot))
            tools = await listed_tools(client)
            assert "inputSchema" in tools["workflows_run"].model_dump(by_alias=True)
            value, result, _ = await paired_call(
                pilot,
                profile,
                client,
                tools["workflows_run"],
                {"workflow": "list-projects"},
                ("run", "list-projects"),
                offsets=(0,),
            )
            assert result.is_error is False
            assert value["complete"] is True and value["returned_count"] == 3

    asyncio.run(check())
