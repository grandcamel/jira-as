"""
Batch processing utilities for large-scale JIRA operations.

Provides:
- Configurable batch sizes with automatic chunking
- Checkpoint/resume capability for long-running operations
- Progress tracking with callbacks
- Rate limiting between batches

This module re-exports the base batch processing classes from assistant-skills-lib
with JIRA-specific defaults and helper functions.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

# Re-export base classes
from assistant_skills_lib import BatchConfig as BaseBatchConfig
from assistant_skills_lib import (
    BatchProcessor,
    BatchProgress,
    CheckpointManager,
    generate_operation_id,
)

# For backward compatibility, re-export all symbols
__all__ = [
    "BatchConfig",
    "BatchProcessor",
    "BatchProgress",
    "CheckpointManager",
    "generate_operation_id",
    "get_recommended_batch_size",
    "list_pending_checkpoints",
]


class BatchConfig(BaseBatchConfig):
    """
    Configuration for JIRA batch processing.

    Extends BaseBatchConfig with JIRA-specific defaults.
    """

    def __post_init__(self) -> None:
        # Set JIRA-specific default checkpoint directory if not specified
        if self.checkpoint_dir is None:
            self.checkpoint_dir = str(Path.home() / ".jira-skills" / "checkpoints")

        # Call parent validation
        super().__post_init__()


def get_recommended_batch_size(total_items: int, operation_type: str = "simple") -> int:
    """
    Get recommended batch size based on total items and operation type.

    Args:
        total_items: Total number of items to process
        operation_type: Type of operation:
            - "simple": Simple field updates (default: 100)
            - "complex": Multi-step operations (default: 50)
            - "clone": Cloning (creates new issues) (default: 25)
            - "transition": Status transitions (default: 50)
            - "assign": Assignments (default: 100)
            - "priority": Priority changes (default: 100)
            - "create": Creating new items (default: 25)
            - "delete": Deleting items (default: 50)

    Returns:
        Recommended batch size
    """
    # Base batch sizes by operation complexity (includes JIRA-specific types)
    base_sizes = {
        "simple": 100,
        "complex": 50,
        "clone": 25,
        "transition": 50,
        "assign": 100,
        "priority": 100,
        "create": 25,
        "delete": 50,
        "update": 100,
    }

    base = base_sizes.get(operation_type, 50)

    # Reduce batch size for very large operations
    if total_items > 5000:
        return max(base // 2, 25)
    elif total_items > 1000:
        return max(base * 3 // 4, 25)

    return base


def list_pending_checkpoints(
    checkpoint_dir: str | None = None,
) -> list[dict[str, Any]]:
    """
    List all pending checkpoints that can be resumed.

    Args:
        checkpoint_dir: Directory containing checkpoints (default: ~/.jira-skills/checkpoints)

    Returns:
        List of checkpoint info dicts
    """
    import json

    if checkpoint_dir is None:
        checkpoint_dir = str(Path.home() / ".jira-skills" / "checkpoints")

    checkpoint_path = Path(checkpoint_dir)
    if not checkpoint_path.exists():
        return []

    checkpoints = []
    for file in checkpoint_path.glob("*.checkpoint.json"):
        try:
            with open(file) as f:
                data = json.load(f)
            progress = BatchProgress(**data)
            if not progress.is_complete:
                checkpoints.append(
                    {
                        "operation_id": file.stem.replace(".checkpoint", ""),
                        "file": str(file),
                        "progress": progress.percent_complete,
                        "processed": progress.processed_items,
                        "total": progress.total_items,
                        "started_at": progress.started_at,
                        "updated_at": progress.updated_at,
                    }
                )
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    return sorted(checkpoints, key=lambda x: x.get("updated_at", ""), reverse=True)
