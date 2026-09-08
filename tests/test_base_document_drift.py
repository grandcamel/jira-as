"""Offline coverage for the Jira Base Document drift job."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_base_document_drift.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("jira_drift", SCRIPT)
assert SPEC and SPEC.loader
drift = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(drift)


def oasdiff() -> str:
    binary = shutil.which("oasdiff") or ROOT.parent / "bin/oasdiff"
    if not Path(binary).is_file():
        pytest.skip("local oasdiff is unavailable")
    return str(binary)


def platform_record() -> dict[str, Any]:
    manifest = json.loads((ROOT / "src/jira_as/specs/manifest.json").read_text())
    return next(item for item in manifest["documents"] if item["id"] == "platform")


def document(description: str = "old", include: bool = True) -> dict[str, Any]:
    paths: dict[str, Any] = {
        "/issues": {
            "get": {
                "operationId": "getIssues",
                "description": description,
                "responses": {"200": {"description": "ok"}},
            }
        }
    }
    if not include:
        paths = {}
    return {
        "openapi": "3.0.3",
        "info": {"title": "Fixture", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": {"Issue": {"type": "object"}}},
    }


@pytest.fixture
def fixture_manifest(tmp_path: Path) -> Path:
    old = document()
    source = json.dumps(old).encode()
    (tmp_path / "base.json").write_bytes(source)
    (tmp_path / "overlay.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "target": '$.paths["/issues"].get',
                        "x-as-test": "issues",
                    }
                ]
            }
        )
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "format_version": 1,
                "documents": [
                    {
                        "id": "fixture",
                        "file": "base.json",
                        "url": "https://example.invalid/base.json",
                        "declared_version": "1.0.0",
                        "sha256": hashlib.sha256(source).hexdigest(),
                        "overlays": ["overlay.json"],
                    }
                ],
            }
        )
    )
    return manifest


def altered_platform_copy(tmp_path: Path) -> tuple[Path, str]:
    record = platform_record()
    source = ROOT / "src/jira_as/specs" / record["file"]
    document = json.loads(source.read_text())
    pointer = sorted(drift.enriched_operation_pointers(source.parent, record))[0]
    _, _, encoded_path, method = pointer.split("/")
    path = encoded_path.replace("~1", "/").replace("~0", "~")
    operation = document["paths"][path][method]
    operation["description"] = (operation.get("description") or "") + "\nDrift fixture."
    replacement = tmp_path / "jira-platform-altered.json"
    replacement.write_text(json.dumps(document))
    return replacement, operation["operationId"]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--oasdiff", oasdiff(), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def fixture_run(
    manifest: Path, replacement: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    return run(
        "--manifest",
        str(manifest),
        "--from-file",
        f"fixture={replacement}",
        *extra,
    )


def test_unchanged_vendored_platform_copy_is_silent(tmp_path: Path):
    record = platform_record()
    source = ROOT / "src/jira_as/specs" / record["file"]
    replacement = tmp_path / source.name
    shutil.copyfile(source, replacement)
    result = run("--from-file", f"platform={replacement}")
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


def test_breaking_removed_enriched_operation_emits_ticket(
    fixture_manifest: Path, tmp_path: Path
):
    replacement = tmp_path / "removed.json"
    replacement.write_text(json.dumps(document(include=False)))
    result = fixture_run(fixture_manifest, replacement, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "Jira Base Document drift: fixture" in result.stdout


def test_unenriched_narrative_change_is_silent(fixture_manifest: Path, tmp_path: Path):
    changed = document()
    changed["paths"]["/other"] = {
        "get": {
            "operationId": "getOther",
            "description": "changed",
            "responses": {"200": {"description": "ok"}},
        }
    }
    replacement = tmp_path / "other.json"
    replacement.write_text(json.dumps(changed))
    result = fixture_run(fixture_manifest, replacement)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("field", ["components", "security", "servers"])
def test_global_dependency_marks_enriched_operation(fixture_manifest: Path, field: str):
    old, new = document(), document()
    if field == "components":
        new["components"]["schemas"]["Issue"]["description"] = "changed"
    elif field == "security":
        new["security"] = [{"oauth": []}]
    else:
        new["servers"] = [{"url": "https://changed.example.invalid"}]
    record = json.loads(fixture_manifest.read_text())["documents"][0]
    assert drift.changed_enriched_operations(
        old, new, fixture_manifest.parent, record
    ) == ["getIssues (GET /issues)"]


def test_bad_overlay_target_fails_closed(fixture_manifest: Path):
    (fixture_manifest.parent / "overlay.json").write_text(
        json.dumps({"actions": [{"target": "$.info", "x-as-test": "bad"}]})
    )
    record = json.loads(fixture_manifest.read_text())["documents"][0]
    with pytest.raises(ValueError, match="unsupported enrichment target"):
        drift.enriched_operation_pointers(fixture_manifest.parent, record)


def test_pin_mismatch_fails_before_diff(fixture_manifest: Path, tmp_path: Path):
    (fixture_manifest.parent / "base.json").write_text(json.dumps(document("corrupt")))
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(document("new")))
    result = fixture_run(fixture_manifest, replacement)
    assert result.returncode == 1
    assert "does not match manifest pin" in result.stderr


def test_altered_vendored_enriched_platform_operation_emits_dry_run(tmp_path: Path):
    replacement, operation_id = altered_platform_copy(tmp_path)
    result = run("--dry-run", "--from-file", f"platform={replacement}")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["project"] == {"key": "JAS"}
    assert payload["components"] == [{"name": "jira-as"}]
    assert payload["issuetype"] == {"name": "Task"}
    assert payload["labels"] == ["base-document-drift"]
    assert operation_id in payload["description"]
    assert "/description" in payload["description"]


def test_file_ticket_uses_fake_filer_for_an_offline_finding(
    tmp_path: Path, monkeypatch
):
    replacement, _ = altered_platform_copy(tmp_path)
    filed: list[dict[str, object]] = []
    monkeypatch.setattr(
        drift,
        "_jira_credentials",
        lambda: ("https://jira.example.test", "worker@example.test", "token"),
    )
    monkeypatch.setattr(drift, "file_ticket", filed.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--oasdiff",
            oasdiff(),
            "--file-ticket",
            "--from-file",
            f"platform={replacement}",
        ],
    )
    assert drift.main() == 0
    assert len(filed) == 1
    assert filed[0]["components"] == [{"name": "jira-as"}]


def test_unchanged_file_ticket_uses_fake_filer_without_filing(
    tmp_path: Path, monkeypatch
):
    record = platform_record()
    source = ROOT / "src/jira_as/specs" / record["file"]
    replacement = tmp_path / source.name
    shutil.copyfile(source, replacement)
    filed: list[dict[str, object]] = []
    monkeypatch.setattr(
        drift,
        "_jira_credentials",
        lambda: ("https://jira.example.test", "worker@example.test", "token"),
    )
    monkeypatch.setattr(drift, "file_ticket", filed.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--oasdiff",
            oasdiff(),
            "--file-ticket",
            "--from-file",
            f"platform={replacement}",
        ],
    )
    assert drift.main() == 0
    assert filed == []


def test_file_ticket_posts_adf_without_redirect(monkeypatch):
    captured: dict[str, Any] = {}

    class Response:
        status = 201

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> Literal[False]:
            return False

    class Opener:
        def open(self, request: Any, timeout: int) -> Response:
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

    monkeypatch.setattr(
        drift,
        "_jira_credentials",
        lambda: ("https://jira.example.test", "worker@example.test", "token"),
    )
    monkeypatch.setattr(drift, "build_opener", lambda *_handlers: Opener())
    drift.file_ticket(
        {
            "project": {"key": "JAS"},
            "issuetype": {"name": "Task"},
            "summary": "drift",
            "description": "heading\nbody",
            "components": [{"name": "jira-as"}],
            "labels": ["base-document-drift"],
        }
    )
    assert captured["request"].full_url == "https://jira.example.test/rest/api/3/issue"
    body = json.loads(captured["request"].data)
    assert body["fields"]["description"]["type"] == "doc"


def test_unknown_replacement_id_fails_without_fetching(tmp_path: Path):
    replacement = tmp_path / "document.json"
    replacement.write_text("{}")
    result = run("--from-file", f"unknown={replacement}")
    assert result.returncode == 1
    assert "unknown or duplicate document ids" in result.stderr
