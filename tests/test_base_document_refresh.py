"""Exercise the Jira refresh command offline through its argv/file seam."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/refresh_base_documents.py"


@pytest.fixture
def pinned(tmp_path):
    old = {
        "openapi": "3.0.3",
        "info": {"title": "Fixture", "version": "1.0.0"},
        "paths": {
            "/issues": {
                "get": {
                    "operationId": "getIssues",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    data = json.dumps(old).encode()
    (tmp_path / "base.json").write_bytes(data)
    record = {
        "id": "fixture",
        "file": "base.json",
        "url": "https://example.invalid/base.json",
        "declared_version": "1.0.0",
        "sha256": hashlib.sha256(data).hexdigest(),
        "fetched_at": "2026-09-07T00:00:00Z",
        "tier": "primary",
        "overlays": [],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format_version": 1, "documents": [record]}))
    old["info"]["version"] = "1.1.0"
    old["paths"]["/new-issues"] = {
        "get": {
            "operationId": "getNewIssues",
            "responses": {"200": {"description": "ok"}},
        }
    }
    new = tmp_path / "new.json"
    new.write_text(json.dumps(old))
    return manifest, new


def invoke(manifest, new, binary, doc_id="fixture"):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest),
            "--from-file",
            f"{doc_id}={new}",
            "--oasdiff",
            str(binary),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def pinned_many(tmp_path):
    records = []
    replacements = {}
    for index, doc_id in enumerate(("platform", "software", "servicedesk"), start=1):
        old = {
            "openapi": "3.0.3",
            "info": {"title": doc_id, "version": "1.0.0"},
            "paths": {
                f"/{doc_id}": {
                    "get": {
                        "operationId": f"get{doc_id.title()}",
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }
        source = tmp_path / f"{doc_id}.json"
        source.write_text(json.dumps(old))
        records.append(
            {
                "id": doc_id,
                "file": source.name,
                "url": f"https://example.invalid/{doc_id}.json",
                "declared_version": "1.0.0",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "fetched_at": "2026-09-07T00:00:00Z",
                "tier": "primary",
                "overlays": [],
            }
        )
        old["info"]["version"] = f"1.{index}.0"
        replacement = tmp_path / f"{doc_id}-new.json"
        replacement.write_text(json.dumps(old))
        replacements[doc_id] = replacement
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format_version": 1, "documents": records}))
    return manifest, replacements


def invoke_many(manifest, replacements, binary):
    command = [sys.executable, str(SCRIPT), "--manifest", str(manifest)]
    for doc_id, replacement in replacements.items():
        command.extend(("--from-file", f"{doc_id}={replacement}"))
    command.extend(("--oasdiff", str(binary)))
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def test_refresh_real_oasdiff_names_changed_operation_and_appends(pinned):
    binary = shutil.which("oasdiff")
    lane_binary = ROOT.parent / "bin/oasdiff"
    if not binary and lane_binary.is_file():
        binary = str(lane_binary)
    if not binary:
        pytest.skip("oasdiff executable unavailable; install it for refresh acceptance")
    manifest, new = pinned
    result = invoke(manifest, new, binary)
    assert result.returncode == 0, result.stderr
    record = json.loads(manifest.read_text())["documents"][0]
    assert record["declared_version"] == "1.1.0"
    assert record["sha256"] == hashlib.sha256(new.read_bytes()).hexdigest()
    assert record["fetched_at"].endswith("Z")
    assert (manifest.parent / "base.json").read_bytes() == new.read_bytes()
    changelog = manifest.parent / "base.changelog.md"
    first = changelog.read_text()
    assert "/new-issues" in first
    assert invoke(manifest, new, binary).returncode == 0
    assert changelog.read_text().startswith(first)
    assert (
        len(re.findall(r"^## \d{4}-\d{2}-\d{2}T", changelog.read_text(), re.MULTILINE))
        == 2
    )


def test_missing_oasdiff_records_named_skip(pinned):
    manifest, new = pinned
    result = invoke(manifest, new, "/nonexistent/oasdiff")
    assert result.returncode == 0, result.stderr
    assert "SKIPPED: oasdiff executable not found" in result.stderr
    assert "SKIPPED: oasdiff" in (manifest.parent / "base.changelog.md").read_text()


def test_refresh_selected_document_leaves_other_primary_pins_and_sources_unchanged(
    pinned_many,
):
    manifest, replacements = pinned_many
    before_manifest = json.loads(manifest.read_text())
    before_sources = {
        record["id"]: (manifest.parent / record["file"]).read_bytes()
        for record in before_manifest["documents"]
    }
    result = invoke_many(
        manifest, {"software": replacements["software"]}, "/nonexistent/oasdiff"
    )
    assert result.returncode == 0, result.stderr
    after_manifest = json.loads(manifest.read_text())
    for record in after_manifest["documents"]:
        source = (manifest.parent / record["file"]).read_bytes()
        if record["id"] == "software":
            assert source == replacements["software"].read_bytes()
            assert record["declared_version"] == "1.2.0"
            assert (manifest.parent / "software.changelog.md").exists()
        else:
            assert source == before_sources[record["id"]]
            assert record == next(
                item
                for item in before_manifest["documents"]
                if item["id"] == record["id"]
            )
            assert not (manifest.parent / f"{record['id']}.changelog.md").exists()


def test_failed_later_candidate_leaves_all_primary_pins_sources_and_changelogs_unchanged(
    pinned_many,
):
    manifest, replacements = pinned_many
    replacements["software"].write_text("not JSON")
    before_manifest = manifest.read_bytes()
    before_sources = {
        path.name: path.read_bytes()
        for path in manifest.parent.glob("*.json")
        if path.name != manifest.name
    }
    result = invoke_many(
        manifest,
        {"platform": replacements["platform"], "software": replacements["software"]},
        "/nonexistent/oasdiff",
    )
    assert result.returncode != 0
    assert manifest.read_bytes() == before_manifest
    assert {
        path.name: path.read_bytes()
        for path in manifest.parent.glob("*.json")
        if path.name != manifest.name
    } == before_sources
    assert not list(manifest.parent.glob("*.changelog.md"))


@pytest.mark.parametrize(
    "failure", ["invalid_json", "wrong_shape", "unknown_id", "bad_pin", "diff_error"]
)
def test_refresh_refuses_without_changing_pins_or_sources(pinned, failure):
    manifest, new = pinned
    binary = "/nonexistent/oasdiff"
    doc_id = "fixture"
    if failure == "invalid_json":
        new.write_text("not JSON")
    elif failure == "wrong_shape":
        new.write_text("{}")
    elif failure == "unknown_id":
        doc_id = "unknown"
    elif failure == "bad_pin":
        (manifest.parent / "base.json").write_text("{}")
    else:
        binary = manifest.parent / "failed-oasdiff"
        binary.write_text("#!/bin/sh\necho fixture-diff-error >&2\nexit 2\n")
        binary.chmod(0o755)
    before_manifest = manifest.read_bytes()
    before_source = (manifest.parent / "base.json").read_bytes()
    result = invoke(manifest, new, binary, doc_id)
    assert result.returncode != 0
    assert manifest.read_bytes() == before_manifest
    assert (manifest.parent / "base.json").read_bytes() == before_source
    assert not (manifest.parent / "base.changelog.md").exists()
