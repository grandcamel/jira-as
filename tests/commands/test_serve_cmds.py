"""Serve startup policy through Click; actual socket tests live in the engine."""

import json
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from jira_as.cli.commands import serve_cmds
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def startup(monkeypatch):
    for name in (
        "JIRA_ALLOWED_PROJECTS",
        "JIRA_ALLOW_SITE_OPERATIONS",
        "JIRA_AS_RECORD",
        "JIRA_AS_CASSETTE",
        "JIRA_AS_SIMULATION_SEED",
        "XDG_RUNTIME_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    config = SimpleNamespace(config={"jira": {}}, service_name="jira")
    config.get_allowed_projects = lambda: ConfigManager.get_allowed_projects(config)
    config.get_allow_site_operations = lambda: ConfigManager.get_allow_site_operations(
        config
    )
    monkeypatch.setattr(ConfigManager, "get_instance", lambda: config)
    calls = []

    def capture(factory, **kwargs):
        surface = factory()
        assert surface.scope_allowlist == tuple(kwargs["allowlist"])
        assert surface.scope_allow_site == kwargs["allow_site"]
        calls.append(kwargs)

    monkeypatch.setattr(serve_cmds, "run_server", capture)
    return config, calls


def write_binding(tmp_path, value):
    (tmp_path / "jira-binding.json").write_text(json.dumps(value))
    return str(tmp_path)


@pytest.mark.parametrize(
    "setting,binding,override,expected,source",
    [
        (None, None, None, [], "empty default"),
        (["GC"], None, None, ["GC"], "configured policy"),
        (["GC"], ["JAS", "GC"], None, ["JAS", "GC"], "binding"),
        (["GC"], ["JAS", "GC"], "SBX", ["SBX"], "JIRA_ALLOWED_PROJECTS"),
        (["GC"], ["JAS", "GC"], "", [], "JIRA_ALLOWED_PROJECTS"),
    ],
)
def test_effective_policy(
    startup, tmp_path, monkeypatch, setting, binding, override, expected, source
):
    config, calls = startup
    if setting is not None:
        config.config["jira"]["allowed_projects"] = setting
    args = ["serve", "--call-log", str(tmp_path / "calls")]
    if binding is not None:
        args += [
            "--binding",
            write_binding(
                tmp_path,
                {"schema_version": 1, "primary": binding[0], "permitted": binding},
            ),
        ]
    if override is not None:
        monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", override)
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert calls[0]["allowlist"] == expected
    assert result.stderr == f"serve: allowlist source={source}; count={len(expected)}\n"


@pytest.mark.parametrize(
    "record",
    [
        None,
        {},
        {"schema_version": True, "primary": "SBX", "permitted": ["SBX"]},
        {"schema_version": 1, "primary": "SBX", "permitted": []},
        {"schema_version": 1, "primary": "SBX", "permitted": ["OTHER"]},
        {"schema_version": 1, "primary": "SBX", "permitted": ["SBX", "SBX"]},
        {"schema_version": 1, "primary": "SBX", "permitted": ["SBX"], "extra": True},
        {"schema_version": 1, "primary": "SBX", "permitted": [1]},
    ],
)
def test_malformed_or_missing_binding_refuses_even_with_env(
    startup, tmp_path, monkeypatch, record
):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    if record is not None:
        write_binding(tmp_path, record)
    result = CliRunner().invoke(
        cli,
        ["serve", "--binding", str(tmp_path), "--call-log", str(tmp_path / "calls")],
    )
    assert result.exit_code == 2, result.output
    assert "binding" in result.output
    assert startup[1] == []


@pytest.mark.parametrize(
    "text",
    [
        "not-json",
        '{"schema_version":1,"schema_version":1,"primary":"SBX","permitted":["SBX"]}',
    ],
)
def test_invalid_binding_json(startup, tmp_path, text):
    (tmp_path / "jira-binding.json").write_text(text)
    result = CliRunner().invoke(
        cli,
        ["serve", "--binding", str(tmp_path), "--call-log", str(tmp_path / "calls")],
    )
    assert result.exit_code == 2
    assert startup[1] == []


def test_default_socket_and_site_override(startup, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    result = CliRunner().invoke(
        cli, ["serve", "--call-log", str(tmp_path / "calls"), "--no-allow-site"]
    )
    assert result.exit_code == 0, result.output
    assert startup[1][0]["socket_path"] == tmp_path / "jira-as.sock"
    assert startup[1][0]["allow_site"] is False


def test_tcp_private_token_file(startup, tmp_path):
    token = tmp_path / "token"
    token.write_text("synthetic-session-token\n")
    token.chmod(0o600)
    result = CliRunner().invoke(
        cli,
        [
            "serve",
            "--call-log",
            str(tmp_path / "calls"),
            "--tcp",
            "127.0.0.1:4321",
            "--token-file",
            str(token),
        ],
    )
    assert result.exit_code == 0, result.output
    assert startup[1][0]["tcp"] == ("127.0.0.1", 4321)
    assert startup[1][0]["token"] == "synthetic-session-token"
    assert "synthetic-session-token" not in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["--tcp", "127.0.0.1:12"],
        ["--token-file", "unused"],
        ["--tcp", "0.0.0.0:12", "--token-file", "unused"],
        ["--socket", "unused", "--tcp", "127.0.0.1:12", "--token-file", "unused"],
    ],
)
def test_invalid_endpoint_options(startup, tmp_path, args):
    result = CliRunner().invoke(
        cli, ["serve", "--call-log", str(tmp_path / "calls"), *args]
    )
    assert result.exit_code == 2
    assert startup[1] == []


def test_version_matches_client():
    runner = CliRunner()
    client, server = (
        runner.invoke(cli, ["--version"]),
        runner.invoke(cli, ["serve", "--version"]),
    )
    assert client.exit_code == server.exit_code == 0
    assert client.stdout == server.stdout
    assert "2.0.0rc1" in server.stdout
    assert "git " in server.stdout or "build " in server.stdout


def test_call_log_required():
    result = CliRunner().invoke(cli, ["serve"])
    assert result.exit_code == 2
    assert "--call-log" in result.output
