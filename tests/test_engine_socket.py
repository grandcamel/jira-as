"""Credential-free Generic Surface clients through the real Split Mode seam."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from as_engine.errors import SurfaceError
from as_engine.index import ProductIndexes
from as_engine.responder import Responder
from as_engine.serve import fake_sidecar
from as_engine.surface import Surface
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager
from jira_as.engine import create_surface

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def socket_config(monkeypatch):
    for name in (
        "JIRA_AS_SOCKET",
        "JIRA_AS_SERVE_TCP",
        "JIRA_AS_SERVE_TOKEN",
        "JIRA_AS_RECORD",
        "JIRA_AS_CASSETTE",
        "JIRA_AS_SIMULATION_SEED",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "socket")
    config = SimpleNamespace(
        get_allowed_projects=lambda: ["SBX"], get_allow_site_operations=lambda: False
    )
    # No credential or API-settings method exists: any access fails the test.
    monkeypatch.setattr(ConfigManager, "get_instance", lambda: config)


@pytest.fixture
def server():
    indexes = ProductIndexes(ROOT / "src/jira_as/_generated")
    responders = {}

    def transport(document, index):
        if document not in responders:
            responders[document] = Responder(index)
            if "getIssue" in index.operations:
                responders[document].seed(
                    "getIssue",
                    [
                        Response(
                            200, {"key": "SBX-1", "fields": {"summary": "socket proof"}}
                        )
                    ]
                    * 4,
                )
        return responders[document]

    try:
        with fake_sidecar(
            surface_factory=lambda: Surface(indexes, transport), allowlist=["SBX"]
        ) as value:
            yield value
    except PermissionError as exc:
        if exc.errno != 1:
            raise
        pytest.skip(
            "NOT RUN: sandbox socket bind denied: errno=1 Operation not permitted"
        )


def test_click_runner_without_credentials(socket_config, monkeypatch, server):
    monkeypatch.setenv("JIRA_AS_SOCKET", str(server.socket_path))
    result = CliRunner().invoke(
        cli, ["api", "call", "getIssue", "--issue-id-or-key", "SBX-1"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "key": "SBX-1",
        "fields": {"summary": "socket proof"},
    }
    assert json.loads(server.call_log.read_text())["outcome"] == "ok 200"


def test_subprocess_scrubbed_environment(server, tmp_path):
    binary = Path(sys.executable).parent / "jira-as"
    if not binary.is_file():
        fallback = shutil.which("jira-as")
        if fallback is None:
            pytest.skip(f"jira-as not found at {binary} or via shutil.which('jira-as')")
        binary = Path(fallback)

    # Build an allowlisted environment from scratch, never inherit credentials.
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    env = {
        "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
        "HOME": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "JIRA_AS_TRANSPORT": "socket",
        "JIRA_AS_SOCKET": str(server.socket_path),
        "JIRA_ALLOWED_PROJECTS": "SBX",
        "JIRA_ALLOW_SITE_OPERATIONS": "false",
    }
    result = subprocess.run(
        [
            str(binary),
            "api",
            "call",
            "getIssue",
            "--issue-id-or-key",
            "SBX-1",
        ],
        env=env,
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "key": "SBX-1",
        "fields": {"summary": "socket proof"},
    }
    assert json.loads(server.call_log.read_text())["outcome"] == "ok 200"


def test_socket_factory_never_loads_credentials(socket_config, monkeypatch):
    from as_engine.socket_transport import SocketTransport

    monkeypatch.setenv("JIRA_AS_SOCKET", "/not-connected")
    surface = create_surface()
    document, index, _ = surface.resolve("getIssue")
    assert isinstance(surface.transport_factory(document, index), SocketTransport)
    with pytest.raises(SurfaceError) as exc:
        surface.call("getIssue", {})
    assert exc.value.code == 2


def test_local_scope_refuses_before_connect(socket_config, monkeypatch):
    monkeypatch.setenv("JIRA_AS_SOCKET", "/not-connected")
    with pytest.raises(SurfaceError) as exc:
        create_surface().call("getIssue", {"issueIdOrKey": "OTHER-1"})
    assert exc.value.code == 4


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"JIRA_AS_SOCKET": ""},
        {"JIRA_AS_SERVE_TCP": "127.0.0.1:1234"},
        {"JIRA_AS_SOCKET": "/a", "JIRA_AS_SERVE_TOKEN": "test"},
        {"JIRA_AS_SERVE_TCP": "0.0.0.0:1234", "JIRA_AS_SERVE_TOKEN": "test"},
        {"JIRA_AS_SERVE_TCP": "127.0.0.1:0", "JIRA_AS_SERVE_TOKEN": "test"},
    ],
)
def test_socket_configuration_rejected(socket_config, monkeypatch, values):
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        create_surface()
