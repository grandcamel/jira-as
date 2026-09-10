"""Jira batch configuration and discoverable durable checkpoints."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from jira_as import (
    BatchConfig,
    BatchProgress,
    CheckpointManager,
    get_recommended_batch_size,
    list_pending_checkpoints,
)


def test_config_uses_jira_home_and_preserves_explicit_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert BatchConfig().checkpoint_dir == str(
        tmp_path / ".jira-skills" / "checkpoints"
    )
    config = BatchConfig(checkpoint_dir=str(tmp_path / "chosen"), batch_size=75)
    assert config.checkpoint_dir == str(tmp_path / "chosen")
    assert config.batch_size == 75


@pytest.mark.parametrize(
    "operation, expected",
    [
        ("simple", 100),
        ("complex", 50),
        ("clone", 25),
        ("transition", 50),
        ("assign", 100),
        ("priority", 100),
        ("create", 25),
        ("delete", 50),
        ("update", 100),
        ("custom-operation", 50),
    ],
)
def test_recommended_size_for_operation(operation, expected):
    assert get_recommended_batch_size(100, operation) == expected


@pytest.mark.parametrize(
    "total, simple, complex_size, clone",
    [(1000, 100, 50, 25), (1001, 75, 37, 25), (5000, 75, 37, 25), (5001, 50, 25, 25)],
)
def test_size_recommendations_at_large_operation_boundaries(
    total, simple, complex_size, clone
):
    assert get_recommended_batch_size(total) == simple
    assert get_recommended_batch_size(total, "complex") == complex_size
    assert get_recommended_batch_size(total, "clone") == clone


def test_missing_and_empty_checkpoint_directory(tmp_path):
    directory = tmp_path / "checkpoints"
    assert list_pending_checkpoints(str(directory)) == []
    directory.mkdir()
    assert list_pending_checkpoints(str(directory)) == []


def test_saved_checkpoint_exposes_resumable_progress(tmp_path):
    progress = BatchProgress(
        total_items=8,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        started_at="2026-09-01T10:00:00",
        processed_keys=["SBX-1", "SBX-2", "SBX-3"],
        errors={"SBX-3": "Unavailable"},
    )
    manager = CheckpointManager(str(tmp_path), "bulk-update")
    manager.save(progress)
    path = tmp_path / "bulk-update.checkpoint.json"
    saved = json.loads(path.read_text())
    assert saved["processed_keys"] == ["SBX-1", "SBX-2", "SBX-3"]
    assert saved["errors"] == {"SBX-3": "Unavailable"}
    assert list_pending_checkpoints(str(tmp_path)) == [
        {
            "operation_id": "bulk-update",
            "file": str(path),
            "progress": 37.5,
            "processed": 3,
            "total": 8,
            "started_at": "2026-09-01T10:00:00",
            "updated_at": saved["updated_at"],
        }
    ]


def test_listing_skips_finished_and_corrupt_files_and_sorts_newest_first(tmp_path):
    # Public progress dataclasses serialize historical checkpoint records with
    # fixed timestamps, independent of the current clock used by save().
    records = [
        ("older", 2, "2026-09-01T10:00:00"),
        ("newer", 4, "2026-09-02T10:00:00"),
        ("finished", 10, "2026-09-03T10:00:00"),
    ]
    for name, processed, updated in records:
        progress = BatchProgress(
            total_items=10, processed_items=processed, updated_at=updated
        )
        (tmp_path / f"{name}.checkpoint.json").write_text(json.dumps(asdict(progress)))
    (tmp_path / "broken.checkpoint.json").write_text('{"total_items":')
    (tmp_path / "unknown-field.checkpoint.json").write_text('{"unexpected": true}')
    (tmp_path / "array.checkpoint.json").write_text("[]")
    (tmp_path / "unrelated.json").write_text(
        json.dumps(asdict(BatchProgress(total_items=10)))
    )
    pending = list_pending_checkpoints(str(tmp_path))
    assert [entry["operation_id"] for entry in pending] == ["newer", "older"]
    assert [entry["progress"] for entry in pending] == [40.0, 20.0]
    assert [entry["processed"] for entry in pending] == [4, 2]


def test_default_checkpoint_listing_uses_redirected_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    directory = tmp_path / ".jira-skills" / "checkpoints"
    CheckpointManager(str(directory), "resume-me").save(BatchProgress(total_items=2))
    pending = list_pending_checkpoints()
    assert len(pending) == 1
    assert pending[0]["operation_id"] == "resume-me"
    assert pending[0]["file"] == str(directory / "resume-me.checkpoint.json")
