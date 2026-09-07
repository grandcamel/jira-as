"""Check every Jira overlay action through the public enrichment seam."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
from as_engine.enrichment import entry_cases
from as_engine.overlay import apply_overlay
from referencing import Registry
from referencing.exceptions import NoSuchResource, Unresolvable

SPECS = Path(__file__).resolve().parents[1] / "src/jira_as/specs"


def entry_case_ids():
    """Read only overlay metadata at collection; never retain Base Documents."""
    manifest = json.loads((SPECS / "manifest.json").read_bytes())
    return [
        action["x-as-test"]
        for document in manifest["documents"]
        for overlay_name in document["overlays"]
        for action in json.loads((SPECS / overlay_name).read_bytes())["actions"]
    ]


ENTRY_CASE_IDS = entry_case_ids()


class EntryCaseStream:
    """Yield requested EntryCases while holding at most the current snapshot."""

    def __init__(self, spec_dir, case_ids):
        self.spec_dir = spec_dir
        self.positions = {
            case_id: position for position, case_id in enumerate(case_ids)
        }
        if len(self.positions) != len(case_ids):
            raise ValueError("duplicate x-as-test IDs in Jira overlays")
        self.reset()

    def reset(self):
        self.iterator = iter(entry_cases(self.spec_dir))
        self.position = -1

    def get(self, case_id):
        requested = self.positions[case_id]
        if requested <= self.position:
            self.reset()
        while True:
            case = next(self.iterator)
            self.position += 1
            if case.id == case_id:
                return case


@pytest.fixture(scope="module")
def entry_case_stream():
    return EntryCaseStream(SPECS, ENTRY_CASE_IDS)


def reject_retrieval(uri):
    raise NoSuchResource(ref=uri)


def validate_body(instance, schema, document):
    """Validate examples with local refs only; retrieval remains disabled."""
    envelope = {**document, "allOf": [schema]}
    jsonschema.Draft4Validator(
        envelope, registry=Registry(retrieve=reject_retrieval)
    ).validate(instance)


@pytest.mark.parametrize("case_id", ENTRY_CASE_IDS)
def test_enrichment_entry(case_id, entry_case_stream):
    entry_case_stream.get(case_id).check(validate_body=validate_body)


def test_example_validator_rejects_invalid_bodies_and_external_nested_refs():
    with pytest.raises(jsonschema.ValidationError):
        validate_body({}, {"type": "object", "required": ["issueIdOrKey"]}, {})
    with pytest.raises(Unresolvable):
        validate_body({}, {"$ref": "https://example.invalid/no-network"}, {})


@pytest.mark.parametrize("document_id", ["platform", "software", "servicedesk"])
def test_oas_patch_cross_check(document_id, tmp_path):
    manifest = json.loads((SPECS / "manifest.json").read_bytes())
    entry = next(item for item in manifest["documents"] if item["id"] == document_id)
    binary = shutil.which("oas-patch", path=str(Path(sys.executable).parent))
    assert binary, (
        "oas-patch is a required dev dependency for the independent CI cross-check"
    )
    source = SPECS / entry["file"]
    expected = json.loads(source.read_bytes())
    for index, name in enumerate(entry["overlays"]):
        expected = apply_overlay(expected, json.loads((SPECS / name).read_bytes()))
        output = tmp_path / f"{document_id}-{index}.json"
        result = subprocess.run(
            [binary, "overlay", str(source), str(SPECS / name), "-o", str(output)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(output.read_bytes()) == expected, name
        source = output
