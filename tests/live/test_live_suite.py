"""Caller-visible SBX scenarios; normally skipped until ``--live`` is supplied."""

from __future__ import annotations

import json
import os

import pytest

from tests.compat.test_contract import validate_output

from .scenarios import CASES

pytestmark = pytest.mark.live


def _validate(shape, stdout: str) -> None:
    kind = shape["kind"]
    if kind in {"json", "text"}:
        validate_output(shape, stdout)
    elif kind == "array":
        assert isinstance(json.loads(stdout), list)
    elif kind == "error":
        assert json.loads(stdout)["status"] == 404
    elif kind == "none":
        assert json.loads(stdout) is None
    else:
        raise AssertionError(f"unknown live output shape: {kind}")


def _simulation_gap(case, shape, result) -> None:
    """Document simulator capabilities absent from the host contract."""
    if os.environ.get("JIRA_AS_TRANSPORT") != "simulation":
        return
    output = result.output
    if "Jira simulation does not implement" in output:
        pytest.skip(result.output.strip())
    if "unsupported simulation JQL clause" in output:
        pytest.skip("simulation lacks labels-filtered JQL")
    if (
        shape["kind"] == "json"
        and result.output.lstrip().startswith("{")
        and "expand" in shape.get("required", {})
        and "expand" not in json.loads(result.stdout)
    ):
        pytest.skip("simulation getIssue lacks the host JSON envelope")
    if case["host_op"] == "create" and "URL: /browse/" in output:
        pytest.skip("simulation create lacks the host absolute browse URL")
    if case["host_op"] == "enrich" and "Time logged: None" in output:
        pytest.skip("simulation worklog omits rendered timeSpent")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_contract_and_generic_scenarios(sbx_session, tmp_path, case):
    if os.environ.get("JIRA_AS_TRANSPORT") == "simulation" and case.get(
        "setup", {}
    ).get("link"):
        pytest.skip("simulation lacks link-type prerequisite capability")
    materialized = sbx_session.prepare(case, tmp_path)
    for step in materialized["steps"]:
        if step["argv"][:2] == ["search", "query"] or "--jql" in step["argv"]:
            sbx_session.wait_for_index(materialized["key"])
        result = sbx_session.invoke(step["argv"])
        _simulation_gap(case, step["output"], result)
        assert result.exit_code == step["exit"], result.output
        _validate(step["output"], result.stderr if step["exit"] else result.stdout)


def test_owned_delete_preview_then_confirm(sbx_session, tmp_path):
    case = {
        "id": "risk-delete",
        "host_op": "risk",
        "variant": 0,
        "steps": [],
        "setup": {"issue": True},
    }
    issue = sbx_session.prepare(case, tmp_path)["key"]
    preview = sbx_session.invoke(
        ["api", "call", "deleteIssue", "--issueIdOrKey", issue, "--format", "json"]
    )
    assert preview.exit_code == 0, preview.output
    preview_json = json.loads(preview.output)
    assert preview_json["operationId"] == "deleteIssue"
    assert preview_json["risk"] == "irreversible"
    assert preview_json["dry_run"] is True
    present = sbx_session.invoke(
        ["api", "call", "getIssue", "--issueIdOrKey", issue, "--format", "json"]
    )
    assert present.exit_code == 0, present.output
    confirmed = sbx_session.invoke(
        [
            "api",
            "call",
            "deleteIssue",
            "--issueIdOrKey",
            issue,
            "--confirm",
            "--format",
            "json",
        ]
    )
    assert confirmed.exit_code == 0, confirmed.output
    sbx_session.deleted_keys.add(issue)
    missing = sbx_session.invoke(
        ["api", "call", "getIssue", "--issueIdOrKey", issue, "--format", "json"]
    )
    assert missing.exit_code == 5
    assert json.loads(missing.stderr)["status"] == 404


def test_survivor_bulk_update_dry_run(sbx_session, tmp_path):
    case = {
        "id": "survivor",
        "host_op": "survivor",
        "variant": 0,
        "steps": [],
        "setup": {"issue": True},
    }
    issue = sbx_session.prepare(case, tmp_path)["key"]
    jql = f"project = SBX AND key = {issue}"
    sbx_session.wait_for_index(issue, jql)
    dry_run = sbx_session.invoke(
        [
            "search",
            "bulk-update",
            jql,
            "--add-labels",
            "dry-run-probe",
            "--dry-run",
            "--output",
            "json",
        ]
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert json.loads(dry_run.stdout) == {
        "would_update": 1,
        "issues": [issue],
        "changes": {
            "add_labels": ["dry-run-probe"],
            "remove_labels": None,
            "priority": None,
        },
    }


def test_survivor_fields_cache_warm(sbx_session):
    warmed = sbx_session.invoke(["fields", "cache", "warm"])
    assert warmed.exit_code == 0, warmed.output
