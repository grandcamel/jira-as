"""Generated Jira scope tags preserve hand decisions and resolve publicly."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from as_engine.build import compile_product

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "src/jira_as/specs"
IDS = ("platform", "software", "servicedesk")


@pytest.fixture(scope="module")
def generated_indexes(tmp_path_factory):
    out = tmp_path_factory.mktemp("jira-scope-indexes")
    compile_product(SPECS, out)
    return {name: json.loads((out / f"{name}.index.json").read_bytes()) for name in IDS}


def test_regeneration_is_stable_and_preserves_pinned_sources(tmp_path):
    specs = tmp_path / "specs"
    shutil.copytree(SPECS, specs)
    before = {
        path.name: path.read_bytes() for path in specs.iterdir() if path.is_file()
    }
    command = [
        sys.executable,
        str(ROOT / "scripts/generate_scope_tags.py"),
        "--spec-dir",
        str(specs),
    ]
    first = subprocess.run(command, capture_output=True, text=True, timeout=30)
    first_outputs = {
        name: (specs / f"{name}.scope.overlay.json").read_bytes() for name in IDS
    }
    second = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    for name in ("platform", "software", "servicedesk"):
        assert (specs / f"{name}.scope.overlay.json").exists()
        assert (specs / f"{name}.scope.overlay.json").read_bytes() == first_outputs[
            name
        ]
        assert (
            first_outputs[name] == (SPECS / f"{name}.scope.overlay.json").read_bytes()
        )
    for name, content in before.items():
        if not name.endswith(".scope.overlay.json"):
            assert (specs / name).read_bytes() == content


def test_critical_scope_forms_and_numeric_routes(generated_indexes):
    platform = generated_indexes["platform"]["operations"]
    software = generated_indexes["software"]["operations"]
    servicedesk = generated_indexes["servicedesk"]["operations"]
    assert platform["getProject"]["extensions"]["x-as-scope"] == {
        "in": "path",
        "name": "projectIdOrKey",
    }
    assert platform["getIssue"]["extensions"]["x-as-scope"] == {
        "in": "key",
        "name": "issueIdOrKey",
        "separator": "-",
    }
    assert platform["searchAndReconsileIssuesUsingJql"]["extensions"]["x-as-scope"] == {
        "in": "query",
        "name": "jql",
        "clause": "project",
        "conjunction": True,
        "order_by": ["key", "created", "updated"],
    }
    assert platform["searchAndReconsileIssuesUsingJqlPost"]["extensions"][
        "x-as-scope"
    ] == {
        "in": "body",
        "path": "/jql",
        "clause": "project",
        "conjunction": True,
        "order_by": ["key", "created", "updated"],
    }
    assert platform["createFilter"]["extensions"]["x-as-scope"] == {"in": "site"}
    assert software["getBoard"]["extensions"]["x-as-scope"] == {"in": "site"}
    assert software["getSprint"]["extensions"]["x-as-scope"] == {"in": "site"}
    assert software["getAllBoards"]["extensions"]["x-as-scope"] == {
        "in": "query",
        "name": "projectKeyOrId",
    }
    assert servicedesk["getServiceDeskById"]["extensions"]["x-as-scope"] == {
        "in": "site"
    }
    assert servicedesk["getOrganization"]["extensions"]["x-as-scope"] == {"in": "site"}


def test_generated_test_ids_use_exposed_identity_names():
    actions = json.loads((SPECS / "software.scope.overlay.json").read_text())["actions"]
    ids = {action["x-as-test"] for action in actions}
    assert "scope_software_getSoftwareIssue" in ids
    assert "scope_software_getIssue" not in ids


def test_all_compiled_operations_have_scope_tags(generated_indexes):
    operations = [
        operation
        for index in generated_indexes.values()
        for operation in index["operations"].values()
    ]
    assert len(operations) == 797
    assert all("x-as-scope" in operation["extensions"] for operation in operations)
