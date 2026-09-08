"""SBX-only lifecycle for CLI-level live and recorder scenarios."""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch
from uuid import uuid4

from as_engine.surface import Surface
from click.testing import CliRunner, Result

from jira_as import engine
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager

from .scenarios import materialize

_SBX_KEY = re.compile(r"^SBX-[1-9][0-9]*$")


@contextlib.contextmanager
def sbx_scope() -> Iterator[None]:
    """Narrow a wrapper's omitted allowlist; reject explicit wider policy."""
    if os.environ.get("JIRA_DEFAULT_PROJECT") != "SBX":
        raise ValueError("SBX live profile refused: JIRA_DEFAULT_PROJECT must be SBX")
    config = ConfigManager.get_instance()
    allowed = config.get_allowed_projects()
    if allowed is not None and allowed != ["SBX"]:
        raise ValueError(
            "SBX live profile refused: allowed projects must be exactly SBX"
        )
    if config.get_allow_site_operations():
        raise ValueError("SBX live profile refused: site operations must be disabled")
    settings = (
        {}
        if "JIRA_ALLOWED_PROJECTS" in os.environ
        else {"JIRA_ALLOWED_PROJECTS": "SBX"}
    )
    with patch.dict(os.environ, settings):
        yield


class _NonClosingSurface:
    """Delegate a shared surface while making CLI callback close calls harmless."""

    def __init__(self, surface: Surface) -> None:
        object.__setattr__(self, "_surface", surface)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._surface, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._surface, name, value)

    def close(self) -> None:
        return None


@dataclass
class SbxSession:
    """Own and remove disposable SBX resources without touching credentials.

    The host wrapper supplies credentials to the standard engine factory.  This
    class does not resolve or retain them; it only confirms the runtime scope
    before making its first setup request.
    """

    prefix: str | None = None
    transport: str | None = None
    cache_dir: Path | None = None
    max_created: int = 40
    runner: CliRunner = field(default_factory=CliRunner, init=False)
    created_keys: set[str] = field(default_factory=set, init=False)
    deleted_keys: set[str] = field(default_factory=set, init=False)
    create_attempts: int = field(default=0, init=False)
    _prepared: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _surface: Surface | None = field(default=None, init=False)
    _directory: Path | None = field(default=None, init=False)
    _active_directory: Path | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.prefix = self.prefix or f"jas-cassette-x{uuid4().hex[:12]}"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.prefix):
            raise ValueError("SBX live profile refused: invalid run prefix")
        if not 0 <= self.max_created <= 45:
            raise ValueError("SBX live profile refused: maximum is 45 issues")

    @property
    def run_label(self) -> str:
        return self.prefix or ""

    def validate_profile(self) -> None:
        """Fail closed on an inherited non-SBX configuration before any wire call."""
        if os.environ.get("JIRA_DEFAULT_PROJECT") != "SBX":
            raise ValueError(
                "SBX live profile refused: JIRA_DEFAULT_PROJECT must be SBX"
            )
        config = ConfigManager.get_instance()
        if config.get_allow_site_operations():
            raise ValueError(
                "SBX live profile refused: site operations must be disabled"
            )
        allowed = config.get_allowed_projects()
        if allowed != ["SBX"]:
            raise ValueError(
                "SBX live profile refused: allowed projects must be exactly SBX"
            )

    def _ensure_surface(self) -> Surface:
        self.validate_profile()
        if self._surface is None:
            self._surface = engine.create_surface(transport=self.transport)
        return self._surface

    @contextlib.contextmanager
    def use_surface(self, surface: Surface) -> Iterator["SbxSession"]:
        """Route compatibility and generic CLI paths through an owned surface."""
        from jira_as.cli.commands import api_cmds

        old_engine = engine.create_surface
        old_api = api_cmds.create_surface
        proxy = _NonClosingSurface(surface)
        engine.create_surface = lambda **_: proxy
        api_cmds.create_surface = lambda **_: proxy
        previous = self._surface
        self._surface = surface
        try:
            yield self
        finally:
            engine.create_surface = old_engine
            api_cmds.create_surface = old_api
            self._surface = previous

    def _gate(self, argv: list[str]) -> None:
        # Deliberately call the same mirror used by the host argv test.
        from tests.test_devhost_argv import _check_gate

        _check_gate(argv)

    def invoke(self, argv: list[str], *, input: str | None = None) -> Result:
        self._gate(argv)
        surface = self._ensure_surface()
        is_create = argv[:2] == ["issue", "create"] or argv[:3] == [
            "api",
            "call",
            "createIssue",
        ]
        if is_create:
            if self.create_attempts >= self.max_created:
                raise RuntimeError(
                    f"SBX live profile refused: creation cap {self.max_created}"
                )
            if argv[:2] == ["issue", "create"]:
                project = argv[argv.index("--project") + 1]
                summary = argv[argv.index("--summary") + 1]
                labels = (
                    argv[argv.index("--labels") + 1].split(",")
                    if "--labels" in argv
                    else []
                )
            else:
                body_name = argv[argv.index("--body") + 1]
                if not body_name.startswith("@"):
                    raise ValueError("SBX create requires a JSON @file body")
                body_path = (self._active_directory or Path.cwd()) / body_name[1:]
                fields = json.loads(body_path.read_text())["fields"]
                project = fields.get("project", {}).get("key")
                summary = fields.get("summary", "")
                labels = fields.get("labels", [])
            if (
                project != "SBX"
                or not summary.startswith(self.run_label + " ")
                or self.run_label not in labels
            ):
                raise ValueError(
                    "SBX create requires SBX, run-prefixed summary and run label"
                )
            self.create_attempts += 1
        previous = Path.cwd()
        try:
            if self._active_directory is not None:
                os.chdir(self._active_directory)
            with self.use_surface(surface):
                result = self.runner.invoke(cli, argv, input=input)
            if is_create and result.exit_code == 0:
                if argv[:2] == ["issue", "create"]:
                    match = re.search(
                        r"^✓ Created issue: (SBX-[1-9][0-9]*)$",
                        result.stdout,
                        re.MULTILINE,
                    )
                    key = match.group(1) if match else None
                else:
                    key = json.loads(result.stdout).get("key")
                if not isinstance(key, str) or not _SBX_KEY.fullmatch(key):
                    raise RuntimeError("SBX create returned a malformed or non-SBX key")
                self.created_keys.add(key)
            return result
        finally:
            os.chdir(previous)

    def _create_issue(self, directory: Path, suffix: str) -> str:
        if self.create_attempts >= self.max_created:
            raise RuntimeError(
                f"SBX live profile refused: creation cap {self.max_created}"
            )
        directory.mkdir(parents=True, exist_ok=True)
        body = directory / "setup.json"
        body.write_text(
            json.dumps(
                {
                    "fields": {
                        "project": {"key": "SBX"},
                        "issuetype": {"name": "Task"},
                        "summary": f"{self.run_label} {suffix}",
                        "labels": [self.run_label],
                    }
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        previous = self._active_directory
        self._active_directory = directory
        result = self.invoke(
            [
                "api",
                "call",
                "createIssue",
                "--project",
                "SBX",
                "--body",
                f"@{body.name}",
                "--format",
                "json",
            ]
        )
        self._active_directory = previous
        if result.exit_code != 0:
            raise RuntimeError(f"SBX setup create failed: {result.output}")
        try:
            payload = json.loads(result.stdout)
            key = payload["key"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError("SBX setup create returned no issue key") from exc
        if not isinstance(key, str) or not _SBX_KEY.fullmatch(key):
            raise RuntimeError("SBX setup create returned a non-SBX key")
        self.created_keys.add(key)
        return key

    def prepare(
        self, case: dict[str, Any], directory: Path | None = None
    ) -> dict[str, Any]:
        """Create only the disposable prerequisites required by one scenario."""
        self._ensure_surface()
        directory = (
            directory or self._directory or (self.cache_dir or Path.cwd()) / "bodies"
        )
        directory.mkdir(parents=True, exist_ok=True)
        self._directory = directory
        key = (
            self._create_issue(directory, case["id"].replace(":", "-"))
            if case.get("setup", {}).get("issue")
            or case.get("setup", {}).get("deleted")
            else "SBX-1"
        )
        other = key
        if case.get("setup", {}).get("other"):
            other = self._create_issue(
                directory, case["id"].replace(":", "-") + "-other"
            )
        materialized = materialize(
            case, key, other, self.run_label, directory / case["id"].replace(":", "-")
        )
        self._active_directory = materialized["directory"]
        for step in materialized["steps"]:
            self._gate(step["argv"])
        if case.get("setup", {}).get("comment"):
            seeded = self.invoke(
                [
                    "collaborate",
                    "comment",
                    "add",
                    key,
                    "--body",
                    "seed comment",
                    "--format",
                    "markdown",
                ]
            )
            if seeded.exit_code != 0:
                raise RuntimeError(f"SBX comment setup failed: {seeded.output}")
        if case.get("setup", {}).get("link"):
            source, target = (
                (other, key) if case["host_op"] == "get-links" else (key, other)
            )
            linked = self.invoke(
                ["relationships", "link", source, "--type", "Blocks", "--to", target]
            )
            if linked.exit_code != 0:
                raise RuntimeError(f"SBX link setup failed: {linked.output}")
        if case.get("setup", {}).get("deleted"):
            deleted = self.invoke(
                [
                    "api",
                    "call",
                    "deleteIssue",
                    "--issueIdOrKey",
                    key,
                    "--confirm",
                    "--format",
                    "json",
                ]
            )
            if deleted.exit_code != 0:
                raise RuntimeError(f"SBX deleted-key setup failed: {deleted.output}")
            self.deleted_keys.add(key)
        materialized["key"] = key
        materialized["other_key"] = other
        self._prepared[case["id"]] = materialized
        return materialized

    def activate(self, case: dict[str, Any]) -> dict[str, Any]:
        """Select a prepared case's body directory for the measured loop."""
        materialized = self._prepared.get(case["id"], case)
        directory = materialized.get("directory")
        if not isinstance(directory, Path):
            raise ValueError(f"SBX scenario was not prepared: {case['id']}")
        self._active_directory = directory
        return materialized

    def ledger(self) -> str:
        """Return the retained cleanup authority without exposing credentials."""
        return (
            f"SBX ledger: keys={','.join(sorted(self.created_keys)) or '-'} "
            f"deleted={','.join(sorted(self.deleted_keys)) or '-'} run_label={self.run_label}"
        )

    @staticmethod
    def _missing(result: Result) -> bool:
        if result.exit_code == 0:
            return False
        try:
            return json.loads(result.stderr).get("status") == 404
        except (AttributeError, json.JSONDecodeError):
            return False

    def _recover_labeled(self) -> set[str]:
        result = self.invoke(
            [
                "api",
                "call",
                "searchAndReconsileIssuesUsingJql",
                "--jql",
                f'project = SBX AND labels = "{self.run_label}"',
                "--all",
                "--format",
                "json",
            ]
        )
        if result.exit_code:
            raise RuntimeError("SBX cleanup label search failed")
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise RuntimeError("SBX cleanup label search returned a malformed envelope")
        recovered = set()
        for item in payload:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("key"), str)
                or not _SBX_KEY.fullmatch(item["key"])
            ):
                raise RuntimeError("SBX cleanup label search returned a non-SBX key")
            recovered.add(item["key"])
        if len(recovered | self.created_keys) > self.max_created:
            raise RuntimeError("SBX cleanup recovery exceeded the creation cap")
        return recovered

    def cleanup(self) -> str:
        """Recover lost responses, delete owned keys, then prove exact absence."""
        errors: list[str] = []
        simulation = (
            self.transport or os.environ.get("JIRA_AS_TRANSPORT")
        ) == "simulation"
        if not simulation:
            try:
                self.created_keys.update(self._recover_labeled())
            except (ValueError, RuntimeError):
                errors.append("label-recovery")
        for key in sorted(self.created_keys - self.deleted_keys):
            result = self.invoke(
                [
                    "api",
                    "call",
                    "deleteIssue",
                    "--issueIdOrKey",
                    key,
                    "--confirm",
                    "--format",
                    "json",
                ]
            )
            if result.exit_code == 0 or self._missing(result):
                self.deleted_keys.add(key)
            else:
                errors.append(f"delete:{key}")
        for key in sorted(self.created_keys):
            result = self.invoke(
                [
                    "api",
                    "call",
                    "getIssue",
                    "--issueIdOrKey",
                    key,
                    "--format",
                    "json",
                ]
            )
            if not self._missing(result):
                errors.append(f"not-404:{key}")
        if not simulation:
            try:
                if self._recover_labeled():
                    errors.append("labeled-survivor")
            except (ValueError, RuntimeError):
                errors.append("label-verification")
        if not simulation and self.create_attempts != len(self.created_keys):
            errors.append("unresolved-create-response")
        if errors:
            print(self.ledger(), file=sys.stderr)
            raise RuntimeError("SBX cleanup failed: " + ",".join(errors))
        if simulation:
            return f"SBX simulation cleanup: tracked={len(self.created_keys)} remaining=0 verified-by-key; label recovery unsupported run_label={self.run_label}"
        return f"SBX cleanup verified: tracked={len(self.created_keys)} remaining=0 run_label={self.run_label}"

    def __enter__(self) -> "SbxSession":
        self._ensure_surface()
        return self

    def __exit__(self, *_: Any) -> None:
        self.cleanup()
