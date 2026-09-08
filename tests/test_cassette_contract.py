"""CLI contracts recorded through HTTPTransport against an in-process fake.

The committed cassette is synthetic. It proves offline replay and scrub parity,
not live Jira compatibility. No test in this module is live-marked.
"""

from __future__ import annotations

import base64
import json
import re
import socket
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
import responses

from jira_as.config_manager import ConfigManager
from tests.live.sbx_profile import SbxSession

SITE = "https://cassette-private-site.invalid"
EMAIL = "cassette-private-email@example.invalid"
TOKEN = "cassette-private-token+/=DO-NOT-PERSIST"
ACCOUNT = "cassette-private-account-id"
CLOUD = "cassette-private-cloud-id"
BASIC = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
COOKIE = "cassette-private-cookie"
SECRETS = (SITE, EMAIL, TOKEN, ACCOUNT, CLOUD, BASIC, COOKIE)
CASSETTE = Path(__file__).parent / "cassettes/compatibility.json"
PREFIX = "jas-cassette-synthetic"
STAMP = "2026-09-01T00:00:00Z"


class FakeJira:
    """Small stateful HTTP service; unexpected routes fail the recording test."""

    def __init__(self) -> None:
        self.issues: dict[str, dict[str, Any]] = {}
        self.comments: dict[str, list[dict[str, Any]]] = {}
        self.next_issue = 1
        self.next_child = 10000
        self.calls: list[tuple[str, str]] = []
        self.link_type = {
            "id": "10000",
            "name": "Blocks",
            "outward": "blocks",
            "inward": "is blocked by",
            "self": SITE + "/rest/api/3/issueLinkType/10000",
        }

    def issue(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        return {
            "expand": "names",
            "id": key.split("-")[1],
            "self": SITE + "/rest/api/3/issue/" + key,
            "key": key,
            "fields": {
                "summary": "Cassette example",
                "project": {"key": "SBX"},
                "labels": [PREFIX],
                "issuetype": {"name": "Task"},
                "status": {"name": "Backlog"},
                "priority": {"name": "Medium"},
                "assignee": {"displayName": "Fixture User", "accountId": ACCOUNT},
                "reporter": {"displayName": "Fixture User", "emailAddress": EMAIL},
                "created": STAMP,
                "updated": STAMP,
                "issuelinks": [],
                **deepcopy(fields),
            },
            "cloudId": CLOUD,
            "echo": TOKEN + " " + BASIC + " " + ACCOUNT,
            "_links": {"base": SITE},
        }

    def callback(
        self, request: requests.PreparedRequest
    ) -> tuple[int, dict[str, str], str]:
        assert request.headers.get("Authorization") == "Basic " + BASIC
        url = urlsplit(str(request.url))
        path = url.path.removeprefix("/rest/api/3/")
        query = parse_qs(url.query)
        data = json.loads(request.body) if request.body else {}
        method = str(request.method)
        self.calls.append((method, path))
        status, body = self.route(method, path, query, data)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic " + BASIC,
            "Set-Cookie": COOKIE,
        }
        return status, headers, "" if status == 204 else json.dumps(body)

    def route(
        self, method: str, path: str, query: dict[str, list[str]], data: dict[str, Any]
    ) -> tuple[int, Any]:
        if path == "issue" and method == "POST":
            fields = data["fields"]
            assert fields["project"] == {"key": "SBX"}
            assert str(fields["summary"]).startswith(PREFIX)
            key = f"SBX-{self.next_issue}"
            self.next_issue += 1
            self.issues[key] = self.issue(key, fields)
            self.comments[key] = []
            return 201, {k: self.issues[key][k] for k in ("id", "key", "self")}
        if path == "field" and method == "GET":
            return 200, [
                {
                    "id": "customfield_10016",
                    "name": "Story points",
                    "schema": {"type": "number"},
                },
                {
                    "id": "customfield_10020",
                    "name": "Notes",
                    "schema": {
                        "type": "string",
                        "custom": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
                    },
                },
            ]
        if path == "issueLinkType" and method == "GET":
            return 200, {"issueLinkTypes": [self.link_type]}
        if path == "issueLink" and method == "POST":
            source = data["inwardIssue"]["key"]
            target = data["outwardIssue"]["key"]
            link = {"id": str(self.next_child), "type": self.link_type}
            self.next_child += 1
            for own, other, direction in (
                (source, target, "outwardIssue"),
                (target, source, "inwardIssue"),
            ):
                self.issues[own]["fields"]["issuelinks"].append(
                    {
                        **link,
                        direction: {"key": other, "fields": {"summary": "Fixture"}},
                    }
                )
            return 201, {}
        if path.startswith("issueLink/") and method == "DELETE":
            identity = path.split("/")[1]
            for issue in self.issues.values():
                issue["fields"]["issuelinks"] = [
                    link
                    for link in issue["fields"]["issuelinks"]
                    if link["id"] != identity
                ]
            return 204, None
        if path == "search/jql" and method in {"GET", "POST"}:
            jql = query.get("jql", [data.get("jql", "")])[0]
            assert "project = SBX" in jql
            label = re.search(r'labels\s*=\s*"?([\w-]+)', jql)
            issues = [
                deepcopy(issue)
                for issue in self.issues.values()
                if not label or label[1] in issue["fields"].get("labels", [])
            ]
            if "statusCategory != Done" in jql:
                issues = [i for i in issues if i["fields"]["status"]["name"] != "Done"]
            return 200, {
                "issues": issues,
                "total": len(issues),
                "isLast": True,
                "startAt": 0,
                "maxResults": 100,
            }
        if path.startswith("issue/"):
            parts = path.split("/")
            key = parts[1]
            assert re.fullmatch(r"SBX-[0-9]+", key)
            if key not in self.issues:
                return 404, {"errorMessages": ["Issue does not exist"], "errors": {}}
            issue = self.issues[key]
            if len(parts) == 2:
                if method == "GET":
                    return 200, deepcopy(issue)
                if method == "PUT":
                    issue["fields"].update(deepcopy(data.get("fields", {})))
                    return 204, None
                if method == "DELETE":
                    del self.issues[key]
                    self.comments.pop(key, None)
                    return 204, None
            if parts[2:] == ["transitions"]:
                if method == "GET":
                    return 200, {
                        "transitions": [
                            {
                                "id": "31",
                                "name": "In Progress",
                                "to": {"name": "In Progress"},
                            },
                            {"id": "41", "name": "Done", "to": {"name": "Done"}},
                        ]
                    }
                if method == "POST":
                    issue["fields"]["status"] = {
                        "name": "In Progress"
                        if data["transition"]["id"] == "31"
                        else "Done"
                    }
                    return 204, None
            if parts[2:] == ["comment"]:
                if method == "GET":
                    comments = self.comments[key]
                    return 200, {
                        "comments": comments,
                        "total": len(comments),
                        "maxResults": 50,
                        "startAt": 0,
                    }
                if method == "POST":
                    comment = {
                        "id": str(self.next_child),
                        "body": data["body"],
                        "author": {
                            "displayName": "Fixture User",
                            "accountId": ACCOUNT,
                            "emailAddress": EMAIL,
                        },
                        "created": STAMP,
                    }
                    self.next_child += 1
                    self.comments[key].append(comment)
                    return 201, comment
            if parts[2:] == ["worklog"] and method == "POST":
                self.next_child += 1
                return 201, {
                    "id": str(self.next_child),
                    "timeSpent": "2h 30m",
                    "timeSpentSeconds": 9000,
                    "started": data.get("started", STAMP),
                    "comment": data.get("comment"),
                }
        raise AssertionError(f"unexpected fake request: {method} {path}")


@pytest.fixture(autouse=True)
def socket_guard(monkeypatch):
    def denied(*_args, **_kwargs):
        raise AssertionError("cassette contract attempted network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def configure_offline(monkeypatch, tmp_path):
    """Isolate the test's own metadata cache; never use a developer's config."""
    from jira_as.config_manager import ConfigManager

    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda _self: None)
    ConfigManager.reset_instance()
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path / "instance"))
    monkeypatch.setenv("JIRA_DEFAULT_PROJECT", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    for name in (
        "JIRA_AS_RECORD",
        "JIRA_AS_CASSETTE",
        "JIRA_AS_SIMULATION_SEED",
        "JIRA_MOCK_MODE",
    ):
        monkeypatch.delenv(name, raising=False)


def record_local_fixture(path, monkeypatch, tmp_path):
    """Use the host recorder inventory unchanged, intercepted at HTTP send."""
    from jira_as.config_manager import ConfigManager
    from scripts.record_cassettes import record_session
    from tests.live.sbx_profile import SbxSession

    configure_offline(monkeypatch, tmp_path)
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "http")
    monkeypatch.setattr(
        ConfigManager, "get_credentials", lambda _self: (SITE, EMAIL, TOKEN)
    )
    monkeypatch.setattr(
        ConfigManager, "get_api_config", lambda _self: {"max_retries": 0}
    )
    fake = FakeJira()
    with responses.RequestsMock(assert_all_requests_are_fired=False) as wire:
        for method in ("GET", "POST", "PUT", "DELETE"):
            wire.add_callback(
                method, re.compile(re.escape(SITE) + r"/.*"), callback=fake.callback
            )
        session = SbxSession(prefix=PREFIX, transport="http", cache_dir=tmp_path)
        payload = record_session(path, session)
    assert not fake.issues, "synthetic cleanup must remove every created issue"
    assert fake.calls
    return payload


def materialize_replay(case, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in case["files"].items():
        (directory / name).write_text(content, encoding="utf-8")
    steps = deepcopy(case["steps"])
    for step in steps:
        argv = step["argv"]
        for index, token in enumerate(argv):
            if token.startswith("@"):
                name = token[1:]
                assert name in case["files"]
                argv[index] = (
                    str(directory / name)
                    if index and argv[index - 1] == "--body-file"
                    else "@" + str(directory / name)
                )
    return steps


def check_output(step, outcome):
    from tests.compat.test_contract import validate_output

    assert outcome.exit_code == step.get("exit", 0), outcome.output
    spec = step["output"]
    if spec["kind"] == "error":
        error = json.loads(outcome.stderr)
        assert error["status"] == 404
    elif spec["kind"] == "array":
        assert isinstance(json.loads(outcome.stdout), list)
    elif spec["kind"] == "none":
        assert json.loads(outcome.stdout) is None
    else:
        # The recorder intentionally removes the entire site URL. Restore only
        # its URI shape for the pinned text grammar, never a field or value.
        validate_output(
            spec, outcome.stdout.replace("<as-site-1>", "https://cassette.invalid")
        )


@pytest.fixture
def playback(monkeypatch, tmp_path):
    from jira_as.config_manager import ConfigManager

    configure_offline(monkeypatch, tmp_path)
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "cassette")
    monkeypatch.setenv("JIRA_AS_CASSETTE", str(CASSETTE))

    def denied(*_args, **_kwargs):
        raise AssertionError("playback attempted HTTP or credential loading")

    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr(requests.Session, "send", denied)
    yield
    ConfigManager.reset_instance()


def test_recorded_fake_scrubs_secrets_and_has_byte_parity(tmp_path, monkeypatch):
    from scripts.record_cassettes import sidecar_path

    path = tmp_path / "recorded.json"
    record_local_fixture(path, monkeypatch, tmp_path / "profile")
    for target in (path, sidecar_path(path)):
        raw = target.read_text()
        assert all(secret not in raw for secret in SECRETS)
    assert path.read_bytes() == CASSETTE.read_bytes()
    assert sidecar_path(path).read_bytes() == sidecar_path(CASSETTE).read_bytes()


def test_all_contract_and_generic_invocations_replay_without_network(
    playback, tmp_path
):
    from click.testing import CliRunner

    from jira_as.cli.main import cli
    from scripts.record_cassettes import invocation_digest, sidecar_path
    from tests.live.scenarios import CASES

    payload = json.loads(sidecar_path(CASSETTE).read_text())
    assert payload["invocations_sha256"] == invocation_digest(payload["cases"])
    assert [case["id"] for case in payload["cases"]] == [case["id"] for case in CASES]
    transcripts = []
    for index, case in enumerate(payload["cases"]):
        for step in materialize_replay(case, tmp_path / str(index)):
            outcome = CliRunner().invoke(cli, step["argv"])
            check_output(step, outcome)
            if case["id"] in {"contract:read:0", "generic:getIssue"}:
                transcripts.append(
                    {
                        "case": case["id"],
                        "argv": step["argv"],
                        "exit": outcome.exit_code,
                        "stdout": outcome.stdout,
                    }
                )
    print(
        "socket-guarded cassette transcripts: "
        + json.dumps(transcripts, sort_keys=True)
    )


def test_cassette_records_nested_prerequisites():
    interactions = json.loads(CASSETTE.read_text())["interactions"]
    operations = {row["operationId"] for row in interactions}
    assert {
        "getFields",
        "getIssueLinkTypes",
        "getIssue",
        "deleteIssueLink",
        "addWorklog",
        "addComment",
        "doTransition",
    } <= operations
    assert any(
        row["operationId"] == "getIssue"
        and row["parameters"].get("fields") == ["issuelinks"]
        for row in interactions
    )


def test_sidecar_is_not_a_player_cassette():
    from as_engine.cassette import Player

    from scripts.record_cassettes import sidecar_path

    with pytest.raises(ValueError):
        Player(sidecar_path(CASSETTE))


def test_recorder_refuses_existing_output_before_setup(tmp_path):
    from scripts.record_cassettes import record_session
    from tests.live.sbx_profile import SbxSession

    target = tmp_path / "existing.json"
    target.write_text("do not replace")
    with pytest.raises(ValueError, match="existing"):
        record_session(target, SbxSession())
    assert target.read_text() == "do not replace"


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_recorder_preserves_failed_step_before_cleanup(
    tmp_path, monkeypatch, capsys, cleanup_fails
):
    from contextlib import nullcontext

    from scripts import record_cassettes as recorder

    argv = ["issue", "get", "SBX-9"]
    case = {"id": "contract:read:0", "steps": [{"argv": argv, "exit": 0}]}
    cleaned = []

    def cleanup():
        captured = capsys.readouterr().err
        assert "contract:read:0" in captured
        assert json.dumps(argv) in captured
        assert "exit=1" in captured
        assert "captured stdout detail" in captured
        assert "captured stderr detail" in captured
        assert "recording failed: contract:read:0 exited 1" in captured
        cleaned.append(True)
        if cleanup_fails:
            raise RuntimeError("cleanup probe failure")
        return "SBX cleanup verified: remaining=0"

    session = SimpleNamespace(
        prepare=lambda case: case,
        activate=lambda case: None,
        use_surface=lambda surface: nullcontext(),
        invoke=lambda argv: SimpleNamespace(
            exit_code=1,
            output="captured stdout detail\ncaptured stderr detail",
            stderr="captured stderr detail",
        ),
        cleanup=cleanup,
        ledger=lambda: "SBX ledger: keys=SBX-9",
    )
    monkeypatch.setattr(recorder, "CASES", [case])
    monkeypatch.setattr(recorder, "create_surface", lambda: None)
    target = tmp_path / "failed.json"
    with pytest.raises(
        RuntimeError, match="^recording failed: contract:read:0 exited 1$"
    ):
        recorder.record_session(target, session)
    assert cleaned == [True]
    captured = capsys.readouterr().err
    assert (
        "SBX cleanup also failed: cleanup probe failure" in captured
    ) == cleanup_fails
    assert "SBX ledger: keys=SBX-9" in captured
    assert not recorder.sidecar_path(target).exists()


def test_recorder_cleanup_failure_still_fails_successful_recording(
    tmp_path, monkeypatch, capsys
):
    from contextlib import nullcontext

    from scripts import record_cassettes as recorder

    error = RuntimeError("cleanup probe failure")

    def cleanup():
        raise error

    session = SimpleNamespace(
        use_surface=lambda surface: nullcontext(),
        cleanup=cleanup,
        ledger=lambda: "SBX ledger: keys=SBX-9",
    )
    monkeypatch.setattr(recorder, "CASES", [])
    monkeypatch.setattr(recorder, "create_surface", lambda: None)
    with pytest.raises(RuntimeError) as caught:
        recorder.record_session(tmp_path / "recorded.json", session)
    assert caught.value is error
    assert "SBX ledger: keys=SBX-9" in capsys.readouterr().err


@pytest.mark.parametrize("count_stream", ["stderr", "stdout-before", "stdout-after"])
def test_cleanup_accepts_empty_search_with_paging_count(monkeypatch, count_stream):
    import click

    session = SbxSession(prefix="safe", transport="http")
    searches = []

    @click.command()
    def empty_search():
        if count_stream != "stdout-after":
            click.echo("count=0", err=count_stream == "stderr")
        click.echo("[]")
        if count_stream == "stdout-after":
            click.echo("count=0")

    def invoke(argv):
        assert argv[:3] == ["api", "call", "searchAndReconsileIssuesUsingJql"]
        assert "--all" in argv
        searches.append(argv)
        result = session.runner.invoke(empty_search)
        assert "count=0" in result.output
        return result

    monkeypatch.setattr(session, "invoke", invoke)
    assert "remaining=0" in session.cleanup()
    assert len(searches) == 2  # Recovery and final label verification both run.


@pytest.mark.parametrize(
    "stdout",
    ["count=0\nnot-json", 'count=0\n{"issues": []}', 'count=1\n[{"key": "OTHER-1"}]'],
)
def test_cleanup_count_filter_still_rejects_invalid_recovery(monkeypatch, stdout):
    session = SbxSession(prefix="safe", transport="http")
    monkeypatch.setattr(
        session, "invoke", lambda argv: SimpleNamespace(exit_code=0, stdout=stdout)
    )
    with pytest.raises(RuntimeError, match="label-recovery.*label-verification"):
        session.cleanup()


@pytest.fixture
def cleanup_runner(monkeypatch):
    """Exercise the profile's real invocation path with a scripted Click runner."""
    from contextlib import nullcontext

    from tests.live import sbx_profile

    waits = []
    monkeypatch.setattr(sbx_profile.time, "sleep", waits.append)

    def make(
        searches,
        *,
        tracked=True,
        get_status=404,
        error_at=None,
        max_created=40,
        captured_argv=None,
    ):
        session = SbxSession(prefix="safe", transport="http", max_created=max_created)
        if tracked:
            session.created_keys.add("SBX-9")
            session.create_attempts = 1
        commands = []

        def invoke(_cli, argv, **_):
            if captured_argv is not None:
                captured_argv.append(list(argv))
            operation = argv[2]
            commands.append(operation)
            if operation == "searchAndReconsileIssuesUsingJql":
                response = searches.pop(0) if len(searches) > 1 else searches[0]
                if isinstance(response, Exception):
                    raise response
                if isinstance(response, SimpleNamespace):
                    return response
                return SimpleNamespace(
                    exit_code=0, stdout=json.dumps(response), stderr=""
                )
            if operation == error_at:
                raise RuntimeError(f"{operation} wire unavailable")
            if operation == "deleteIssue":
                return SimpleNamespace(exit_code=0, stdout="null", stderr="")
            assert operation == "getIssue"
            if get_status == 200:
                return SimpleNamespace(
                    exit_code=0, stdout='{"key": "SBX-9"}', stderr=""
                )
            return SimpleNamespace(
                exit_code=5,
                stdout="",
                stderr=json.dumps({"status": get_status, "message": "probe detail"}),
            )

        monkeypatch.setattr(session, "_ensure_surface", lambda: None)
        monkeypatch.setattr(session, "use_surface", lambda surface: nullcontext())
        monkeypatch.setattr(session.runner, "invoke", invoke)
        return session, commands, waits

    return make


@pytest.mark.parametrize("verification", [False, True])
@pytest.mark.parametrize("item", [{"id": "24688"}, {"id": "24688", "key": None}])
def test_cleanup_missing_key_names_malformed_item_fields(
    cleanup_runner, verification, item
):
    responses = [[], [item]] if verification else [[item], []]
    session, commands, waits = cleanup_runner(responses, tracked=False)
    phase = "label-verification" if verification else "label-recovery"
    with pytest.raises(RuntimeError, match=f"{phase}: .*malformed envelope") as caught:
        session.cleanup()
    assert f"item keys: {sorted(item)}" in str(caught.value)
    assert "non-SBX key" not in str(caught.value)
    assert "deleteIssue" not in commands
    assert not waits


def test_cleanup_recovers_populated_id_and_key_with_explicit_fields(cleanup_runner):
    captured_argv = []
    session, _, waits = cleanup_runner(
        [[{"id": "24688", "key": "SBX-5"}], []],
        captured_argv=captured_argv,
    )
    session.create_attempts = 2  # One known key and one lost create response.
    assert "remaining=0" in session.cleanup()
    assert session.created_keys == session.deleted_keys == {"SBX-5", "SBX-9"}
    searches = [
        argv for argv in captured_argv if argv[2] == "searchAndReconsileIssuesUsingJql"
    ]
    assert (
        searches
        == [
            [
                "api",
                "call",
                "searchAndReconsileIssuesUsingJql",
                "--jql",
                'project = SBX AND labels = "safe"',
                "--all",
                "--fields",
                "key",
                "--format",
                "json",
            ]
        ]
        * 2
    )
    deletes = [argv for argv in captured_argv if argv[2] == "deleteIssue"]
    assert [argv[argv.index("--issueIdOrKey") + 1] for argv in deletes] == [
        "SBX-5",
        "SBX-9",
    ]
    assert not waits


def test_cleanup_empty_count_stderr_recovers_no_keys(cleanup_runner):
    session, commands, waits = cleanup_runner(
        [SimpleNamespace(exit_code=0, stdout="[]", stderr="count=0\n")],
        tracked=False,
    )
    assert "tracked=0 remaining=0" in session.cleanup()
    assert not session.created_keys
    assert commands == ["searchAndReconsileIssuesUsingJql"] * 2
    assert not waits


def test_cleanup_foreign_key_remains_a_non_sbx_refusal(cleanup_runner):
    session, commands, waits = cleanup_runner(
        [[{"id": "24688", "key": "OTHER-5"}]], tracked=False
    )
    with pytest.raises(RuntimeError, match="non-SBX key") as caught:
        session.cleanup()
    assert "malformed envelope" not in str(caught.value)
    assert "deleteIssue" not in commands
    assert not waits


def test_cleanup_empty_recovery_still_deletes_known_keys(cleanup_runner):
    session, commands, waits = cleanup_runner([[], []])
    assert "remaining=0" in session.cleanup()
    assert commands == [
        "searchAndReconsileIssuesUsingJql",
        "deleteIssue",
        "getIssue",
        "searchAndReconsileIssuesUsingJql",
    ]
    assert not waits
    assert session.ledger() == "SBX ledger: keys=SBX-9 deleted=SBX-9 run_label=safe"


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("index unavailable"),
        OSError("index timeout"),
        SimpleNamespace(exit_code=5, stdout="", stderr="index query rejected"),
    ],
)
def test_cleanup_recovery_search_failure_is_advisory(cleanup_runner, failure):
    session, commands, waits = cleanup_runner([failure, []])
    summary = session.cleanup()
    assert "remaining=0" in summary
    assert "label-recovery:" in summary
    assert (
        failure.stderr if isinstance(failure, SimpleNamespace) else str(failure)
    ) in summary
    assert "deleteIssue" in commands and "getIssue" in commands
    assert not waits


def test_cleanup_persistent_index_lag_defers_to_404(cleanup_runner):
    session, commands, waits = cleanup_runner([[], [{"key": "SBX-9"}]])
    summary = session.cleanup()
    assert "remaining=0" in summary
    assert "label-lag: SBX-9" in summary
    assert commands.count("searchAndReconsileIssuesUsingJql") == 6
    assert commands.count("getIssue") == 2
    assert waits == [3] * 4
    assert sum(waits) < 20


@pytest.mark.parametrize(
    "intermediate", [[{"key": "SBX-9"}], RuntimeError("index busy")]
)
def test_cleanup_verification_retries_until_index_clears(cleanup_runner, intermediate):
    session, commands, waits = cleanup_runner([[], intermediate, []])
    summary = session.cleanup()
    assert "remaining=0" in summary
    assert "label-lag" not in summary
    assert commands.count("getIssue") == 1
    assert commands.count("searchAndReconsileIssuesUsingJql") == 3
    assert waits == [3]


@pytest.fixture
def index_runner(monkeypatch):
    """Keep invoke's argv gate and create tracking while simulating index lag."""
    from contextlib import nullcontext

    from tests.live import sbx_profile

    waits = []
    monkeypatch.setattr(sbx_profile.time, "sleep", waits.append)

    def make(searches):
        session = SbxSession(prefix="safe", transport="cassette")
        commands = []
        indexed = False

        def invoke(_cli, argv, **_):
            nonlocal indexed
            commands.append(list(argv))
            if argv[:3] == ["api", "call", "createIssue"]:
                payload = {"key": "SBX-9"}
            elif "--all" in argv:
                assert argv[:3] == ["api", "call", "searchAndReconsileIssuesUsingJql"]
                assert argv[argv.index("--fields") + 1] == "key"
                assert argv[argv.index("--jql") + 1] == "project = SBX AND key = SBX-9"
                payload = searches.pop(0)
                indexed = any(item.get("key") == "SBX-9" for item in payload)
            elif argv[:2] == ["search", "bulk-update"]:
                assert argv == [
                    "search",
                    "bulk-update",
                    "project = SBX AND key = SBX-9",
                    "--add-labels",
                    "dry-run-probe",
                    "--dry-run",
                    "--output",
                    "json",
                ]
                payload = {
                    "would_update": int(indexed),
                    "issues": ["SBX-9"] if indexed else [],
                    "changes": {
                        "add_labels": ["dry-run-probe"],
                        "remove_labels": None,
                        "priority": None,
                    },
                }
            else:
                assert indexed, "measured search ran before index readiness"
                if argv[:2] == ["search", "query"]:
                    stdout = (
                        "Found 1 issue(s)\n"
                        "Key Type Status Priority Assignee Reporter Summary\n"
                    )
                    return SimpleNamespace(
                        exit_code=0, stdout=stdout, stderr="", output=stdout
                    )
                assert argv[:3] == ["api", "call", "searchAndReconsileIssuesUsingJql"]
                payload = {"issues": [{"key": "SBX-9"}]}
            stdout = json.dumps(payload)
            return SimpleNamespace(exit_code=0, stdout=stdout, stderr="", output=stdout)

        monkeypatch.setattr(session, "_ensure_surface", lambda: None)
        monkeypatch.setattr(session, "use_surface", lambda surface: nullcontext())
        monkeypatch.setattr(session.runner, "invoke", invoke)
        return session, commands, waits

    return make


@pytest.mark.parametrize("misses", [0, 1, 4])
def test_index_wait_returns_attempts_and_reports_only_lag(index_runner, capsys, misses):
    session, commands, waits = index_runner([[]] * misses + [[{"key": "SBX-9"}]])
    assert session.wait_for_index("SBX-9") == misses + 1
    assert len(commands) == misses + 1
    assert waits == [3] * misses
    output = capsys.readouterr().out
    if misses:
        assert f"JQL index lag: SBX-9 visible after {misses + 1} attempts" in output
    else:
        assert output == ""


def test_bulk_dry_run_waits_for_exact_indexed_key(index_runner, tmp_path, capsys):
    from tests.live.test_live_suite import test_survivor_bulk_update_dry_run

    session, commands, waits = index_runner([[], [{"key": "SBX-9"}]])
    test_survivor_bulk_update_dry_run(session, tmp_path)
    assert session.created_keys == {"SBX-9"}
    assert [argv[:3] for argv in commands] == [
        ["api", "call", "createIssue"],
        ["api", "call", "searchAndReconsileIssuesUsingJql"],
        ["api", "call", "searchAndReconsileIssuesUsingJql"],
        ["search", "bulk-update", "project = SBX AND key = SBX-9"],
    ]
    assert waits == [3]
    assert "JQL index lag: SBX-9 visible after 2 attempts" in capsys.readouterr().out


@pytest.mark.parametrize("miss", [[], [{"key": "SBX-8"}]])
def test_bulk_dry_run_index_bound_exhausted(index_runner, tmp_path, miss):
    from tests.live.test_live_suite import test_survivor_bulk_update_dry_run

    session, commands, waits = index_runner([miss] * 5)
    with pytest.raises(
        RuntimeError, match="JQL index lag: SBX-9 not visible after 5 attempts"
    ):
        test_survivor_bulk_update_dry_run(session, tmp_path)
    assert len(commands) == 6  # One create and exactly five readiness searches.
    assert all(argv[:2] != ["search", "bulk-update"] for argv in commands)
    assert waits == [3] * 4


@pytest.mark.parametrize(
    "case_id", ["contract:search:0", "generic:searchAndReconsileIssuesUsingJql"]
)
def test_post_create_search_scenarios_wait_for_index(index_runner, tmp_path, case_id):
    from tests.live.scenarios import CASES
    from tests.live.test_live_suite import test_contract_and_generic_scenarios

    case = next(case for case in CASES if case["id"] == case_id)
    session, commands, waits = index_runner([[], [{"key": "SBX-9"}]])
    test_contract_and_generic_scenarios(session, tmp_path, case)
    assert len(commands) == 4  # Create, two readiness searches, measured search.
    assert "--all" in commands[1] and "--all" in commands[2]
    assert "--all" not in commands[3]
    assert waits == [3]


def test_cleanup_indexed_live_key_is_a_leak(cleanup_runner):
    session, commands, waits = cleanup_runner(
        [[], [{"key": "SBX-9"}]],
        tracked=False,
        get_status=200,
    )
    with pytest.raises(RuntimeError, match="label-leak: SBX-9") as caught:
        session.cleanup()
    assert "exit=0" in str(caught.value)
    assert commands.count("getIssue") == 1
    assert waits == [3] * 4


def test_cleanup_indexed_unknown_status_is_not_lag(cleanup_runner):
    session, _, _ = cleanup_runner(
        [[], [{"key": "SBX-9"}]],
        tracked=False,
        get_status=500,
    )
    with pytest.raises(RuntimeError, match="label-verification:SBX-9") as caught:
        session.cleanup()
    assert "probe detail" in str(caught.value)
    assert "500" in str(caught.value)
    assert "label-lag" not in str(caught.value)


@pytest.mark.parametrize("operation", ["deleteIssue", "getIssue"])
def test_cleanup_keeps_operation_exception_text(cleanup_runner, operation):
    session, commands, _ = cleanup_runner([[], []], error_at=operation)
    with pytest.raises(RuntimeError, match=f"{operation} wire unavailable"):
        session.cleanup()
    assert commands[-1] == "searchAndReconsileIssuesUsingJql"


def test_cleanup_verification_search_error_surfaces_after_retries(cleanup_runner):
    session, commands, waits = cleanup_runner([[], RuntimeError("index unavailable")])
    with pytest.raises(RuntimeError, match="label-verification: index unavailable"):
        session.cleanup()
    assert commands.count("searchAndReconsileIssuesUsingJql") == 6
    assert waits == [3] * 4


def test_cleanup_recovery_cap_remains_a_real_refusal(cleanup_runner):
    session, commands, waits = cleanup_runner(
        [[{"key": "SBX-9"}]],
        tracked=False,
        max_created=0,
    )
    with pytest.raises(RuntimeError, match="label-recovery: .*creation cap"):
        session.cleanup()
    assert "deleteIssue" not in commands
    assert not waits


def test_cleanup_empty_index_does_not_hide_unresolved_creation(cleanup_runner):
    session, _, _ = cleanup_runner([[]], tracked=False)
    session.create_attempts = 1
    with pytest.raises(
        RuntimeError, match="unresolved-create-response: attempts=1 tracked=0"
    ):
        session.cleanup()


def test_profile_refuses_mismatched_allowlist_before_invocation(monkeypatch):
    monkeypatch.setenv("JIRA_DEFAULT_PROJECT", "SBX")
    monkeypatch.setattr(
        ConfigManager,
        "get_instance",
        lambda: SimpleNamespace(
            get_allowed_projects=lambda: ["OTHER"],
            get_allow_site_operations=lambda: False,
        ),
    )
    with pytest.raises(ValueError, match="allowed projects"):
        SbxSession(prefix="safe").validate_profile()


def test_cleanup_recovers_lost_response_key_and_requires_404(monkeypatch):
    monkeypatch.delenv("JIRA_AS_TRANSPORT", raising=False)
    session = SbxSession(prefix="safe")
    session.create_attempts = 1
    deleted = set()  # Create response was lost: only label recovery knows the key.

    def invoke(argv, **_):
        if "deleteIssue" in argv:
            deleted.add("SBX-9")
            return SimpleNamespace(exit_code=0, stdout="null", stderr="")
        if "getIssue" in argv:
            return SimpleNamespace(
                exit_code=5, stdout="", stderr=json.dumps({"status": 404})
            )
        return SimpleNamespace(
            exit_code=0,
            stdout=json.dumps([] if deleted else [{"key": "SBX-9"}]),
            stderr="",
        )

    monkeypatch.setattr(session, "invoke", invoke)
    assert "remaining=0" in session.cleanup()
    assert session.created_keys == deleted == {"SBX-9"}


@pytest.mark.parametrize("generic", [False, True])
def test_profile_reowns_recreated_key_and_cleans_it_up(monkeypatch, tmp_path, generic):
    from contextlib import nullcontext

    session = SbxSession(prefix="safe", transport="simulation")
    session.created_keys.add("SBX-9")
    session.deleted_keys.add("SBX-9")
    session.create_attempts = 1
    session._active_directory = tmp_path
    commands = []
    present = False

    def invoke(_cli, argv, **_):
        nonlocal present
        commands.append(argv)
        if argv[:2] == ["issue", "create"] or argv[:3] == [
            "api",
            "call",
            "createIssue",
        ]:
            present = True
            stdout = '{"key": "SBX-9"}' if generic else "✓ Created issue: SBX-9\n"
            return SimpleNamespace(exit_code=0, stdout=stdout, stderr="")
        if argv[:3] == ["api", "call", "deleteIssue"]:
            assert present
            present = False
            return SimpleNamespace(exit_code=0, stdout="null", stderr="")
        assert argv[:3] == ["api", "call", "getIssue"]
        assert not present
        return SimpleNamespace(exit_code=5, stdout="", stderr='{"status": 404}')

    monkeypatch.setattr(session, "_ensure_surface", lambda: None)
    monkeypatch.setattr(session, "use_surface", lambda surface: nullcontext())
    monkeypatch.setattr(session.runner, "invoke", invoke)
    if generic:
        (tmp_path / "create.json").write_text(
            json.dumps(
                {
                    "fields": {
                        "project": {"key": "SBX"},
                        "summary": "safe recreated",
                        "labels": ["safe"],
                    }
                }
            )
        )
        argv = ["api", "call", "createIssue", "--body", "@create.json"]
    else:
        argv = [
            "issue",
            "create",
            "--project",
            "SBX",
            "--summary",
            "safe recreated",
            "--labels",
            "safe",
        ]
    assert session.invoke(argv).exit_code == 0
    assert session.created_keys == {"SBX-9"}
    assert not session.deleted_keys
    assert session.create_attempts == 2
    assert "remaining=0" in session.cleanup()
    assert session.deleted_keys == {"SBX-9"}
    assert [argv[2] for argv in commands[1:]] == ["deleteIssue", "getIssue"]


def test_cleanup_rejects_non404_verification(monkeypatch):
    monkeypatch.delenv("JIRA_AS_TRANSPORT", raising=False)
    session = SbxSession(prefix="safe")
    session.created_keys.add("SBX-9")
    session.create_attempts = 1

    def invoke(argv, **_):
        if "deleteIssue" in argv:
            return SimpleNamespace(exit_code=0, stdout="null", stderr="")
        if "getIssue" in argv:
            return SimpleNamespace(
                exit_code=5, stdout="", stderr=json.dumps({"status": 500})
            )
        return SimpleNamespace(exit_code=0, stdout="[]", stderr="")

    monkeypatch.setattr(session, "invoke", invoke)
    with pytest.raises(RuntimeError, match="not-404"):
        session.cleanup()


def test_creation_cap_refuses_before_a_wire_attempt(tmp_path):
    session = SbxSession(prefix="safe", max_created=0)
    with pytest.raises(RuntimeError, match="creation cap"):
        session._create_issue(Path(tmp_path), "cap")


@pytest.mark.parametrize(
    "allowed,site,default,ok",
    [
        (None, False, "SBX", True),
        (["SBX"], False, "SBX", True),
        (["SBX", "GC"], False, "SBX", False),
        ([], False, "SBX", False),
        (["SBX"], True, "SBX", False),
        (["SBX"], False, "GC", False),
    ],
)
def test_host_scope_bootstrap_narrows_only_absent_policy(
    monkeypatch, allowed, site, default, ok
):
    import os

    from tests.live.sbx_profile import sbx_scope

    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS", raising=False)
    monkeypatch.setenv("JIRA_DEFAULT_PROJECT", default)
    monkeypatch.setattr(
        ConfigManager,
        "get_instance",
        lambda: SimpleNamespace(
            get_allowed_projects=lambda: allowed,
            get_allow_site_operations=lambda: site,
        ),
    )
    if ok:
        with sbx_scope():
            assert os.environ.get("JIRA_ALLOWED_PROJECTS") == "SBX"
        assert "JIRA_ALLOWED_PROJECTS" not in os.environ
    else:
        with pytest.raises(ValueError, match="SBX live profile refused"):
            with sbx_scope():
                pytest.fail("refused scope entered the run")


def test_sidecar_measured_argv_pass_the_gate():
    from scripts.record_cassettes import sidecar_path
    from tests.test_devhost_argv import _check_gate

    for case in json.loads(sidecar_path(CASSETTE).read_text())["cases"]:
        for step in case["steps"]:
            _check_gate(step["argv"])
