"""Fields cache and textarea overrides through caller-visible seams."""

import json

from as_engine.simulation import JiraSimulationStore
from click.testing import CliRunner

from jira_as import engine
from jira_as.autocomplete_cache import InstanceFieldsCache
from jira_as.cli.main import cli


def test_cold_warm_describe_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    runner = CliRunner()
    cold = runner.invoke(cli, ["fields", "list", "--output", "json"])
    assert cold.exit_code == 0 and "cache is cold" in cold.output
    describe = runner.invoke(cli, ["api", "describe", "createIssue"])
    assert "automatic textarea conversion is inactive" in describe.output
    surface = engine.create_surface(transport="simulation", store=JiraSimulationStore())
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    warm = runner.invoke(cli, ["fields", "cache", "warm", "--transport", "simulation"])
    assert warm.exit_code == 0, warm.output
    listed = runner.invoke(cli, ["fields", "list", "--output", "json"])
    assert any(row["id"] == "customfield_10010" for row in json.loads(listed.output))
    assert runner.invoke(cli, ["fields", "get", "customfield_10010"]).exit_code == 0
    assert not surface.scope_allow_site
    public = runner.invoke(cli, ["api", "call", "getFields"])
    assert public.exit_code == 4, public.output


def test_wire_auto_override_cold_and_preencoded(tmp_path, monkeypatch):
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    from as_engine.responder import Responder

    from jira_as.cli.commands import api_cmds

    surface = engine.create_surface(transport="responder")
    _, index, _ = surface.resolve("createIssue")
    responder = Responder(index)
    surface.transport_factory = lambda *_: responder
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)
    runner = CliRunner()
    args = [
        "api",
        "call",
        "createIssue",
        "--project",
        "SBX",
        "--field",
        "fields.project.key=SBX",
        "--field",
        "fields.summary=x",
        "--field",
        "fields.issuetype.name=Task",
        "--field",
        "customfield_10010=**md**",
    ]

    def sent(extra=()):
        result = runner.invoke(cli, [*args, *extra])
        assert result.exit_code == 0, result.output
        return responder.requests[-1][2]["fields"]["customfield_10010"]

    assert sent() == "**md**"
    assert sent(["--adf-field", "customfield_10010"])["type"] == "doc"
    InstanceFieldsCache(tmp_path).write(JiraSimulationStore().fields)
    assert sent()["type"] == "doc"
    bad = runner.invoke(
        cli, ["api", "call", "getFields", "--adf-field", "customfield_10010"]
    )
    assert bad.exit_code == 2 and "declared textarea" in bad.output


def test_cache_malformed_expired_and_detached(tmp_path):
    cache = InstanceFieldsCache(tmp_path)
    assert cache.read() is None
    original = JiraSimulationStore().fields
    cached = cache.write(original)
    cached.clear()
    assert cache.read() == original
    envelope = json.loads(cache.path.read_text())
    envelope["fetched_at"] = 0
    cache.path.write_text(json.dumps(envelope))
    assert cache.read() is None
    cache.path.write_text('{"version":2,"fetched_at":true,"fields":[]}')
    assert cache.read() is None


def test_describe_instance_parameter_points_to_cache_without_override(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    result = CliRunner().invoke(cli, ["api", "describe", "getContextsForField"])
    assert result.exit_code == 0, result.output
    assert "fields list" in result.output and "Cache is cold" in result.output
    assert "--adf-field" not in result.output
