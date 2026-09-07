"""Frozen JAS-48 contract data checks.

The table below is deliberately independent from the JSON document.  It is a
local transcription of grand-camel-platform/scripts/jira-host OP_PREFIXES,
plus its search and enrich handlers; importing that private host script would
make this CI contract depend on an unrelated checkout.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

CONTRACT_PATH = (
    Path(__file__).parents[2] / "src" / "jira_as" / "compat" / "contract.json"
)
CAPTURE_FIXTURE = Path(__file__).parent / "captures" / "contract-output.json"

# scripts/jira-host:31-44, :263-436, :408-436.  The labels read/merge/write
# pair is one host operation and enrich owns its three ordered child commands.
FROZEN_HOST_OPERATIONS = (
    "read",
    "comments",
    "comment",
    "create",
    "update",
    "transitions",
    "transition",
    "link",
    "unlink",
    "get-links",
    "link-types",
    "labels",
    "search",
    "enrich",
)


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def captures() -> dict[str, str]:
    fixture = json.loads(CAPTURE_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["provenance"]["pin"] == "v1.2.1"
    return fixture["outputs"]


def validate_output(specification: dict[str, Any], stdout: str) -> Any:
    """Validate captured/user-visible output without manufacturing fields.

    The responder fixtures in ``test_invocations`` return only fields which
    this validator requires.  This keeps missing response fields observable.
    """
    kind = specification["kind"]
    if kind == "json":
        payload = json.loads(stdout)
        if specification.get("root") == "array":
            assert isinstance(payload, list), "$ must be an array"
            assert payload, "$ must not be an empty array"
            item_spec = specification["items"]
            for index, item in enumerate(payload):
                assert item_spec["type"] == "object"
                _validate_required(item_spec["required"], item, path=f"$[{index}]")
            return payload
        _validate_required(specification["required"], payload, path="$")
        return payload
    if kind == "text":
        lines = stdout.splitlines()
        for expression in specification.get("lines", []):
            assert any(re.fullmatch(expression, line) for line in lines), (
                f"missing line matching {expression!r} in {stdout!r}"
            )
        for header in specification.get("table_headers", []):
            assert header in stdout, f"missing table header {header!r}"
        return stdout
    if kind == "pair":
        raise AssertionError("pair output must be validated as its two invocations")
    raise AssertionError(f"unknown compatibility output kind: {kind!r}")


def _validate_required(
    requirements: dict[str, Any], payload: Any, *, path: str
) -> None:
    assert isinstance(payload, dict), f"{path} must be an object"
    for key, expected in requirements.items():
        assert key in payload, f"missing required field {path}.{key}"
        value = payload[key]
        if isinstance(expected, str):
            assert _json_type(value) == expected, (
                f"{path}.{key} must be {expected}, got {_json_type(value)}"
            )
            continue
        assert expected["type"] == "object", f"unsupported requirement at {path}.{key}"
        assert isinstance(value, dict), f"{path}.{key} must be object"
        _validate_required(expected["required"], value, path=f"{path}.{key}")


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    raise AssertionError(f"not a JSON value: {value!r}")


def test_contract_has_exactly_the_frozen_host_operation_table(contract):
    records = contract["operations"]
    assert tuple(record["host_op"] for record in records) == FROZEN_HOST_OPERATIONS
    assert len(records) == 14
    assert all(record.get("argv_template") for record in records)


def test_labels_contract_keeps_its_read_modify_write_steps_explicit(contract):
    labels = next(
        item for item in contract["operations"] if item["host_op"] == "labels"
    )
    assert labels["ordered_steps"] == [
        ["issue", "get", "K", "--fields", "labels", "--output", "json"],
        ["issue", "update", "K", "--labels", "MERGED"],
    ]


def test_contract_declares_the_legacy_exit_codes(contract):
    assert contract["exit_codes"] == {
        "success": 0,
        "jira_error": 1,
        "usage_or_refusal": 2,
        "scope_refusal": 1,
        "host_wrapper_usage_refusal": 2,
    }


def test_capture_fixture_is_repository_local():
    assert CAPTURE_FIXTURE.is_relative_to(Path(__file__).parent)
    assert CAPTURE_FIXTURE.is_file()


@pytest.mark.parametrize(
    ("capture", "host_op", "variant_index"),
    [
        ("read", "read", 0),
        ("read-detailed", "read", 1),
        ("read-json", "read", 2),
        ("read-labels-json", "read", 3),
        ("comments", "comments", 0),
        ("comments-after", "comments", 1),
        ("comment-add", "comment", 0),
        ("comment-add-file", "comment", 1),
        ("create", "create", 0),
        ("update-summary", "update", 0),
        ("update-description", "update", 1),
        ("transitions", "transitions", 0),
        ("transition", "transition", 0),
        ("transition-done", "transition", 1),
        ("link", "link", 0),
        ("unlink", "unlink", 0),
        ("get-links", "get-links", 0),
        ("get-links-after", "get-links", 1),
        ("link-types", "link-types", 0),
        ("search", "search", 0),
        ("estimate", "enrich", 0),
        ("timelog-spaced", "enrich", 2),
    ],
)
def test_contract_matches_the_captured_success_shape(
    contract, captures, capture, host_op, variant_index
):
    record = next(item for item in contract["operations"] if item["host_op"] == host_op)
    validate_output(record["variants"][variant_index]["output"], captures[capture])


def test_labels_pair_matches_its_separate_captures(contract, captures):
    record = next(
        item for item in contract["operations"] if item["host_op"] == "labels"
    )
    specification = record["variants"][0]["output"]
    validate_output(
        specification["first"],
        captures["labels-read"],
    )
    validate_output(
        specification["second"],
        captures["labels-update"],
    )


def test_hidden_link_types_preflight_has_its_captured_json_shape(contract, captures):
    record = next(item for item in contract["operations"] if item["host_op"] == "link")
    specification = record["variants"][0]["preflight"]["output"]
    validate_output(
        specification,
        captures["link-types-json"],
    )


def test_removed_required_json_field_fails_the_contract(contract, captures):
    record = next(item for item in contract["operations"] if item["host_op"] == "read")
    fixture = json.loads(captures["read-json"])
    del fixture["fields"]["labels"]
    with pytest.raises(
        AssertionError, match=r"missing required field \$\.fields\.labels"
    ):
        validate_output(record["variants"][2]["output"], json.dumps(fixture))
