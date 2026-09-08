"""Offline tests of configuration and refusal before client construction."""

import json
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from jira_as.cli.cli_utils import get_client_from_context, handle_jira_errors
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager
from jira_as.error_handler import ValidationError
from jira_as.project_guard import check_project_access


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """Use only test-owned settings and restore any preexisting singleton."""
    monkeypatch.delenv("JIRA_ALLOWED_PROJECTS", raising=False)
    monkeypatch.setattr(ConfigManager, "_instances", {})
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "params",
    [
        {"issue_key": "demo-1"},
        {"issues": "DEMO-1,DEMO-20"},
        {"issues": ("DEMO-1", "DEMO-2")},
        {"project": " demo "},
        {"projects": "DEMO,SECOND"},
        {"jql": 'project = "DEMO" AND status = Open'},
        {"jql": "PROJECT in ('demo', SECOND)"},
        {"jql": '"project" = DEMO OR project = SECOND'},
        {"jql": "project NOT IN (DEMO, SECOND)"},
        {"project_type": "software", "key": "DEMO"},
        {"key_or_project": "DEMO"},
        {"key_or_project": "DEMO-1"},
        {"project": None, "force": True},
    ],
)
def test_allowed_references(params):
    check_project_access(params, ["DEMO", "SECOND"])


@pytest.mark.parametrize(
    "params, project",
    [
        ({"issue_key": "OTHER-1"}, "OTHER"),
        ({"issues": "DEMO-1,other-2"}, "OTHER"),
        ({"issues": ["DEMO-1", ("OTHER-2",)]}, "OTHER"),
        ({"fields": {"parent": "OTHER-2"}}, "OTHER"),
        ({"body": "See https://example.test/browse/OTHER-12"}, "OTHER"),
        ({"project": "OTHER"}, "OTHER"),
        ({"projects": "DEMO,OTHER"}, "OTHER"),
        ({"project_key": "other"}, "OTHER"),
        ({"to_project": "OTHER"}, "OTHER"),
        ({"target_project": "OTHER"}, "OTHER"),
        ({"share_project": "OTHER"}, "OTHER"),
        ({"project_filter": "OTHER"}, "OTHER"),
        ({"project_key_filter": "OTHER"}, "OTHER"),
        ({"project_type": "software", "key": "OTHER"}, "OTHER"),
        ({"key_or_project": "OTHER"}, "OTHER"),
        ({"project_id": "12345"}, "12345"),
        ({"project_id": 12345}, "12345"),
        ({"jql": "project = other"}, "OTHER"),
        ({"jql": '"project" = "OTHER"'}, "OTHER"),
        ({"jql": "'project' in ('DEMO', 'OTHER')"}, "OTHER"),
        ({"jql": "project = DEMO OR project = OTHER"}, "OTHER"),
        ({"jql": 'project in (DEMO,"Other Team")'}, "OTHER TEAM"),
        ({"jql": 'project = "Other\\"Team"'}, 'OTHER"TEAM'),
        ({"jql": "project != OTHER"}, "OTHER"),
        ({"jql": "project not in (DEMO, OTHER)"}, "OTHER"),
        ({"jql": "project was in (DEMO, OTHER)"}, "OTHER"),
        ({"jql": "project was not OTHER"}, "OTHER"),
        ({"jql": "project = 12345"}, "12345"),
        ({"issue_key": "A-1"}, "A"),
        ({"issue_key": "LONGPROJECTKEY-1"}, "LONGPROJECTKEY"),
    ],
)
def test_outside_reference_names_project_and_setting(params, project):
    with pytest.raises(ValidationError) as error:
        check_project_access(params, ["DEMO"])
    assert project in str(error.value)
    assert "jira.allowed_projects" in str(error.value)


def test_absent_policy_does_not_even_scan():
    params = MagicMock()
    check_project_access(params, None)
    params.items.assert_not_called()


def test_empty_policy_denies_named_project():
    with pytest.raises(ValidationError, match="DEMO"):
        check_project_access({"issue_key": "DEMO-1"}, [])


def test_known_limits_are_reference_checks_only():
    check_project_access(
        {"issue_key": "12345", "jql": "status = Open", "filter_id": "7"}, []
    )


def test_missing_settings_allow_all_without_opening_files(isolated_config):
    with patch("builtins.open", side_effect=AssertionError("unexpected file read")):
        config = ConfigManager.get_instance()
        assert config.get_allowed_projects() is None
        with patch("jira_as.cli.cli_utils.get_jira_client") as factory:
            ctx = click.Context(click.Command("test"))
            ctx.params = {"issue_key": "OTHER-1"}
            assert get_client_from_context(ctx) is factory.return_value
            assert get_client_from_context(ctx) is factory.return_value
            factory.assert_called_once_with()


def test_settings_local_overrides_team(isolated_config):
    (isolated_config / "settings.json").write_text(
        json.dumps({"jira": {"allowed_projects": ["TEAM"]}})
    )
    (isolated_config / "settings.local.json").write_text(
        json.dumps({"jira": {"allowed_projects": [" demo ", "SECOND", "demo"]}})
    )
    assert ConfigManager.get_instance().get_allowed_projects() == ["DEMO", "SECOND"]


def test_settings_file_refusal_never_reaches_client_or_credentials(isolated_config):
    (isolated_config / "settings.json").write_text(
        json.dumps({"jira": {"allowed_projects": ["DEMO"]}})
    )
    with (
        patch("jira_as.cli.cli_utils.get_jira_client") as factory,
        patch.object(ConfigManager, "get_credentials") as credentials,
    ):
        result = CliRunner().invoke(cli, ["issue", "get", "OTHER-1"])
    assert result.exit_code == 1
    assert "OTHER" in result.output
    assert "jira.allowed_projects" in result.output
    factory.assert_not_called()
    credentials.assert_not_called()


def test_env_overrides_settings(monkeypatch):
    config = ConfigManager.get_instance()
    config.config["jira"]["allowed_projects"] = ["TEAM"]
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", " demo , SECOND,demo")
    assert config.get_allowed_projects() == ["DEMO", "SECOND"]


@pytest.mark.parametrize("value", [None, "DEMO", [1], [""], ["DEMO-1"], {}])
def test_invalid_setting_refused(value):
    config = ConfigManager.get_instance()
    config.config["jira"]["allowed_projects"] = value
    with pytest.raises(ValidationError, match="jira.allowed_projects"):
        config.get_allowed_projects()


@pytest.mark.parametrize("value", ["DEMO,", ",DEMO", "DEMO,,SECOND", "123"])
def test_invalid_override_refused(monkeypatch, value):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", value)
    with pytest.raises(ValidationError, match="jira.allowed_projects"):
        ConfigManager.get_instance().get_allowed_projects()


def test_explicit_empty_setting_and_override(monkeypatch):
    config = ConfigManager.get_instance()
    config.config["jira"]["allowed_projects"] = []
    assert config.get_allowed_projects() == []
    config.config["jira"]["allowed_projects"] = ["DEMO"]
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "")
    assert config.get_allowed_projects() == []


@pytest.mark.parametrize("cached", [False, True])
def test_refusal_precedes_factory_and_cached_client(monkeypatch, cached):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "DEMO")
    ctx = click.Context(click.Command("test"))
    ctx.params = {"issue_key": "OTHER-1"}
    client = MagicMock()
    if cached:
        ctx.obj = {"_client": client}
    with patch("jira_as.cli.cli_utils.get_jira_client") as factory:
        with pytest.raises(ValidationError, match="OTHER"):
            get_client_from_context(ctx)
        factory.assert_not_called()
        assert not client.mock_calls


@pytest.mark.parametrize(
    "args",
    [
        ["issue", "get", "OTHER-1"],
        ["search", "query", "project in (DEMO, OTHER)"],
    ],
)
def test_public_cli_refuses_before_factory_in_mock_mode(monkeypatch, args):
    monkeypatch.setenv("JIRA_MOCK_MODE", "true")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "DEMO")
    with patch("jira_as.cli.cli_utils.get_jira_client") as factory:
        result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    assert "OTHER" in result.output
    assert "jira.allowed_projects" in result.output
    factory.assert_not_called()


def test_refusal_uses_existing_error_decorator(monkeypatch):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "DEMO")

    @click.command()
    @click.argument("issue_key")
    @click.pass_context
    @handle_jira_errors
    def command(ctx, issue_key):
        get_client_from_context(ctx)

    result = CliRunner().invoke(command, ["OTHER-1"])
    assert result.exit_code == 1
    assert "jira.allowed_projects" in result.output
