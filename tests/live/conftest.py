"""Fixtures for the SBX-only CLI live suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from as_engine.simulation import JiraSimulationStore

from jira_as import engine
from jira_as.config_manager import ConfigManager

from .sbx_profile import SbxSession, sbx_scope


@pytest.fixture(scope="session")
def sbx_session(tmp_path_factory, request):
    """Use the shared simulation store offline; host mode keeps engine HTTP."""
    session = SbxSession(cache_dir=tmp_path_factory.mktemp("live-cache"))
    if os.environ.get("JIRA_AS_TRANSPORT") == "simulation":
        patch = pytest.MonkeyPatch()
        patch.setenv("JIRA_DEFAULT_PROJECT", "SBX")
        patch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
        patch.setenv("JIRA_FIELDS_CACHE_DIR", str(session.cache_dir / "instance"))
        patch.setattr(Path, "home", classmethod(lambda _cls: session.cache_dir))
        patch.setattr(ConfigManager, "_find_claude_dir", lambda _self: None)
        ConfigManager._instances = {}
        surface = engine.create_surface(
            transport="simulation", store=JiraSimulationStore()
        )
        surface.scope_allowlist = ("SBX",)
        context = session.use_surface(surface)
        context.__enter__()
        try:
            yield session
        finally:
            try:
                request.config._sbx_cleanup_summary = session.cleanup()
            finally:
                context.__exit__(None, None, None)
                ConfigManager._instances = {}
                patch.undo()
        return
    with sbx_scope():
        try:
            yield session
        finally:
            request.config._sbx_cleanup_summary = session.cleanup()


def pytest_terminal_summary(terminalreporter, config):
    summary = getattr(config, "_sbx_cleanup_summary", None)
    if summary:
        terminalreporter.write_line(summary)
