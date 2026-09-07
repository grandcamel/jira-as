"""Replayable Jira argv examples for the supervisor's host gate."""

import json
import re
from pathlib import Path

import pytest
import requests
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager

# Kept local deliberately: the test must not import Grand Camel.  This mirrors
# grand-camel-platform/scripts/jira-dev-host:61-220 for host-replay parity.
ISSUE_KEY = re.compile(
    r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]{1,9})-([0-9]+)(?![0-9])"
)
PROJECT_CLAUSE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?P<negated>not\s+)?project(?:\s*[\"']\s*)?\s*"
    r"(?P<op>!=|!~|=|~|:|\bnot\s+in\b|\bin\b|\bwas\s+not\s+in\b|\bwas\s+in\b|\bwas\s+not\b|\bwas\b|\bchanged\b)"
    r"\s*(?P<value>\([^)]*\)|\"[^\"]*\"|'[^']*'|\{[^}]*\}|[A-Za-z0-9_-]+)?"
)
JQL_CLAUSE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:status|statuscategory|assignee|reporter|creator|issuetype|type|issuekey|key|id|"
    r"parent|summary|description|text|comment|labels|priority|resolution|created|updated|resolved|due|duedate|"
    r"sprint|fixversion|affectedversion|component|filter|watcher|worklogauthor)\s*"
    r"(?:!=|!~|=|~|<=|>=|<|>|\bin\b|\bnot\s+in\b|\bis\b|\bwas\b|\bchanged\b)|\border\s+by\b"
)
TOP_LEVEL_OR = re.compile(r"(?i)(?<![A-Za-z0-9_])or(?![A-Za-z0-9_])")
JSON_KEY = re.compile(r'"(?:key|id|name)"\s*:\s*"?([A-Za-z0-9_-]+)"?')
SAVED_FILTER = re.compile(
    r"(?i)(?<![A-Za-z0-9_])filter\s*(?:!=|=|\bnot\s+in\b|\bin\b|\bwas\s+not\s+in\b|\bwas\s+in\b|\bwas\s+not\b|\bwas\b|\bchanged\b)"
    r"\s*(?:\([^)]*\)|\"[^\"]*\"|'[^']*'|[A-Za-z0-9_-]*)"
)
ALLOWED_PROJECT_OPERATORS = {"=", "~", ":", "in"}


def _sandbox(value):
    return value.strip().strip("\"'").upper() == "SBX"


def _project_values(raw):
    raw = raw.strip()
    if raw.startswith("{"):
        return JSON_KEY.findall(raw) or [raw]
    if raw.startswith("("):
        raw = raw[1:-1] if raw.endswith(")") else raw[1:]
        return [item.strip().strip("\"'") for item in raw.split(",")]
    return [raw.strip("\"'")]


def _jql_branches(argument):
    depth = 0
    branch_start = 0
    branches = []
    index = 0
    while index < len(argument):
        char = argument[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            match = TOP_LEVEL_OR.match(argument, index)
            if match:
                branches.append(argument[branch_start:index])
                index = match.end()
                branch_start = index
                continue
        index += 1
    return [*branches, argument[branch_start:]]


def _check_gate(argv):
    """Return normally only for argv accepted by jira-dev-host's gate."""
    for index, argument in enumerate(argv):
        assert all(_sandbox(match.group(1)) for match in ISSUE_KEY.finditer(argument))
        assert not SAVED_FILTER.search(argument)
        clauses = list(PROJECT_CLAUSE.finditer(argument))
        for clause in clauses:
            assert not clause.group("negated")
            assert (
                " ".join(clause.group("op").lower().split())
                in ALLOWED_PROJECT_OPERATORS
            )
            assert clause.group("value")
            assert all(
                _sandbox(value) and not value.isdigit()
                for value in _project_values(clause.group("value"))
            )
        if JQL_CLAUSE.search(argument):
            assert all(
                any(match.group("value") for match in PROJECT_CLAUSE.finditer(branch))
                for branch in _jql_branches(argument)
            )
        option, _, inline = argument.partition("=")
        assert option != "--filter"
        if option.startswith("--project") or option == "-p":
            value = inline if "=" in argument else argv[index + 1]
            assert _sandbox(value)
        if (
            argument.startswith("-p")
            and not argument.startswith("--")
            and len(argument) > 2
        ):
            assert _sandbox(argument[2:])


def _visible_project_identity(argv):
    return (
        bool(ISSUE_KEY.search(" ".join(argv)))
        or any(item.startswith("--project") for item in argv)
        or any(
            PROJECT_CLAUSE.search(argument) and match.group("value")
            for argument in argv
            for match in PROJECT_CLAUSE.finditer(argument)
        )
    )


@pytest.fixture
def shapes():
    return json.loads(
        (Path(__file__).with_name("devhost_shapes.json")).read_text(encoding="utf-8")
    )


def test_fixture_has_forty_replayable_shapes(shapes):
    assert len(shapes) == 40
    for shape in shapes:
        _check_gate(shape["argv"])
        assert _visible_project_identity(shape["argv"])


@pytest.mark.parametrize("shape_index", range(40))
def test_every_host_shape_reaches_responder(monkeypatch, tmp_path, shapes, shape_index):
    shape = shapes[shape_index]
    _check_gate(shape["argv"])
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv(
        "JIRA_ALLOW_SITE_OPERATIONS", "true" if shape.get("site") else "false"
    )
    ConfigManager._instances = {}
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda _self: None)
    monkeypatch.setattr(
        requests.Session, "send", lambda *_a, **_kw: pytest.fail("HTTP attempted")
    )
    calls = []
    original = Responder.call

    def record(self, operation, parameters, body):
        calls.append((operation.operationId, parameters, body))
        return original(self, operation, parameters, body)

    monkeypatch.setattr(Responder, "call", record)
    argv = list(shape["argv"])
    for name, payload in shape.get("files", {}).items():
        source = tmp_path / f"{name}.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        argv = ["@" + str(source) if item == "@" + name else item for item in argv]
    try:
        result = CliRunner().invoke(cli, argv)
        assert result.exit_code == 0, result.output
        assert calls, "the shape must send through the responder, not only dry-run"
        for payload in shape.get("files", {}).values():
            assert calls[-1][2] == payload
    finally:
        ConfigManager._instances = {}


@pytest.mark.parametrize(
    "argv",
    [
        ["api", "call", "getIssue", "--issueIdOrKey", "GC-1"],
        ["api", "call", "getProject", "--projectIdOrKey", "10001"],
        ["api", "call", "getProject", "-pGC"],
        ["api", "call", "searchAndReconsileIssuesUsingJql", "--filter", "42"],
        [
            "api",
            "call",
            "searchAndReconsileIssuesUsingJql",
            "--jql",
            "project = SBX OR status = Open",
        ],
    ],
)
def test_local_gate_rejects_representative_unsafe_argv(argv):
    with pytest.raises(AssertionError):
        _check_gate(argv)
