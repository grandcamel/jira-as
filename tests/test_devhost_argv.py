"""Replayable Jira argv examples for the supervisor's host gate."""

import json
import re
from copy import deepcopy
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
    assert len(shapes[:40]) == 40
    for shape in shapes[:40]:
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


def contract_shapes():
    """Every machine contract variant, ordered pair step and typed preflight."""
    contract = json.loads(
        (Path(__file__).parents[1] / "src/jira_as/compat/contract.json").read_text()
    )
    rows = []
    for operation in contract["operations"]:
        for variant_index, variant in enumerate(operation["variants"]):
            tokens = variant["argv"]
            chunks = (
                [tokens[: tokens.index("=>")], tokens[tokens.index("=>") + 1 :]]
                if "=>" in tokens
                else [tokens]
            )
            if variant.get("preflight"):
                chunks = [variant["preflight"]["argv"], *chunks]
            for step_index, argv in enumerate(chunks):
                rows.append(
                    {
                        "origin": "contract",
                        "case": f"{operation['host_op']}:{variant_index}:{step_index}",
                        "argv": argv,
                        **(
                            {"files": {"comment.md": "Cassette comment"}}
                            if "@comment.md" in argv
                            else {}
                        ),
                    }
                )
    return rows


def generic_shapes():
    """Bounded deterministic sample, derived from compiled parameter schemas.

    These are argv-gate probes. The original forty rows independently exercise
    actual CLI dispatch; arbitrary sampled operations are never sent to Jira.
    """
    from jira_as.engine import create_surface

    surface = create_surface(transport="responder")
    rows = []
    for document, index in surface.indexes.primary():
        candidates = []
        for operation in sorted(
            index.operations.values(), key=lambda item: item.operationId
        ):
            identities = [
                p
                for p in operation.parameters
                if p["name"]
                in {
                    "issueIdOrKey",
                    "issueKey",
                    "projectIdOrKey",
                    "projectKeyOrId",
                    "projectKey",
                }
            ]
            if identities and not operation.deprecated:
                candidates.append((operation, identities))
        for operation, identities in candidates[:20]:
            argv = ["api", "call", operation.operationId]
            for parameter in operation.parameters:
                if parameter not in identities and not parameter.get("required"):
                    continue
                name = parameter["name"]
                value = (
                    "SBX"
                    if name.lower().startswith("project")
                    else "SBX-1"
                    if parameter in identities
                    else "1"
                    if parameter.get("type") in {"integer", "number"}
                    else "fixture"
                )
                argv += ["--" + name, value]
            files = {}
            if operation.request_body_required:
                # Keep body values out of argv, including project-bearing maps.
                files["sample.json"] = {"fields": {"project": {"key": "SBX"}}}
                argv += ["--body", "@sample.json"]
            if operation.extensions.get("x-as-risk", "safe") != "safe":
                argv += ["--confirm"]
            for selector in ([], ["--project", "SBX"]):
                rows.append(
                    {
                        "origin": "generic",
                        "case": f"{document}:{operation.operationId}:{bool(selector)}",
                        "argv": [*argv, *selector],
                        **({"files": files} if files else {}),
                    }
                )
    return rows


def generated_shapes():
    """Replayable export with provenance; import lazily to avoid recorder cycles."""
    from scripts.record_cassettes import RECORDER_ARGV
    from tests.live.scenarios import LIVE_ARGV

    return [
        *contract_shapes(),
        *({**deepcopy(row), "origin": "recorder"} for row in RECORDER_ARGV),
        *({**deepcopy(row), "origin": "live"} for row in LIVE_ARGV),
        *generic_shapes(),
    ]


def test_generated_shapes_match_replayable_export(shapes):
    generated = generated_shapes()
    assert shapes[40:] == generated
    for row in generated:
        _check_gate(row["argv"])
    counts = {
        origin: sum(row["origin"] == origin for row in generated)
        for origin in ("contract", "recorder", "live", "generic")
    }
    print("devhost generated counts: " + json.dumps(counts, sort_keys=True))
    assert len({row["case"].split(":")[0] for row in contract_shapes()}) == 14
    assert counts["contract"] == 28
    assert all(counts.values())


def test_generated_materialized_file_arguments_pass_gate(tmp_path):
    """The gate sees filenames, and the body checks prove the hidden SBX scope."""
    for row in generated_shapes():
        argv = list(row["argv"])
        for name, body in row.get("files", {}).items():
            target = tmp_path / name
            target.write_text(json.dumps(body) if not isinstance(body, str) else body)
            argv = ["@" + target.name if item == "@" + name else item for item in argv]
            if isinstance(body, dict) and "project" in body.get("fields", {}):
                assert body["fields"]["project"] == {"key": "SBX"}
        _check_gate(argv)


def test_gc278_field_project_shape_is_a_recorded_refusal():
    """Keep the host finding visible; an @file form is admitted separately."""
    with pytest.raises(AssertionError):
        _check_gate(
            [
                "api",
                "call",
                "createIssue",
                "--project",
                "SBX",
                "--field",
                "fields.project.key=SBX",
            ]
        )
    _check_gate(
        ["api", "call", "createIssue", "--project", "SBX", "--body", "@create.json"]
    )
