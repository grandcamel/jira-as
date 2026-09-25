"""The scope opt-out, verified at the argv and recorded transport boundaries."""

import json

import pytest
import requests
from as_engine.errors import SurfaceError
from as_engine.responder import Responder
from as_engine.surface import Surface
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager
from jira_as.engine import create_surface

SEARCH = "searchAndReconsileIssuesUsingJql"
# Accepted by the enforcing conjunction grammar ...
PROVABLE = [
    "project = TTRP",
    "project = TTRP ORDER BY updated DESC",
    "project = TTRP AND statusCategory = Done",
]
# ... and refused by it even when no allowlist is configured.
UNPROVABLE = ["project = TTRP OR project = CSRE", "assignee = currentUser()"]
WARNING = "Warning: scope enforcement is permissive"
requires_scope_switch = pytest.mark.skipif(
    not isinstance(getattr(Surface, "scope_enforcement", None), property),
    reason="as-engine main does not yet include scope_enforcement",
)


@pytest.fixture
def unrestricted(monkeypatch):
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    for name in (
        "JIRA_ALLOWED_PROJECTS",
        "JIRA_ALLOW_SITE_OPERATIONS",
        "JIRA_SCOPE_ENFORCEMENT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda _: None)
    ConfigManager.reset_instance()
    monkeypatch.setattr(
        requests.Session, "send", lambda *_a, **_kw: pytest.fail("HTTP attempted")
    )
    calls = []
    original = Responder.call

    def record(self, operation, parameters, body):
        calls.append((operation.operationId, parameters, body))
        return original(self, operation, parameters, body)

    monkeypatch.setattr(Responder, "call", record)
    yield calls
    ConfigManager.reset_instance()


def invoke(*args):
    return CliRunner().invoke(cli, ["api", "call", *args])


def usage_error(result, calls, message):
    assert result.exit_code == 2, (result.output, result.exception)
    assert json.loads(result.stderr)["messages"] == [message]
    assert calls == []


@pytest.mark.parametrize("jql", UNPROVABLE)
def test_default_refuses_unproved_jql_with_no_allowlist(unrestricted, jql):
    result = invoke(SEARCH, "--jql", jql)
    assert result.exit_code == 4, result.output
    error = json.loads(result.stderr)
    assert "allowlist=null" in error["messages"][0]
    assert unrestricted == []


def test_default_accepts_provable_jql_without_warning(unrestricted):
    for jql in PROVABLE:
        result = invoke(SEARCH, "--jql", jql)
        assert result.exit_code == 0, result.output
        assert WARNING not in result.stderr
    assert [call[1] for call in unrestricted] == [{"jql": jql} for jql in PROVABLE]


@requires_scope_switch
def test_permissive_sends_every_query_and_warns_once_per_command(
    unrestricted, monkeypatch
):
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    for jql in PROVABLE + UNPROVABLE:
        result = invoke(SEARCH, "--jql", jql)
        assert result.exit_code == 0, result.output
        assert result.stderr.count(WARNING) == 1
    assert [call[1] for call in unrestricted] == [
        {"jql": jql} for jql in PROVABLE + UNPROVABLE
    ]


@requires_scope_switch
def test_permissive_warning_is_written_once_per_surface(
    unrestricted, monkeypatch, capsys
):
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    surface = create_surface(transport="responder")
    for jql in UNPROVABLE:
        assert surface.call(SEARCH, {"jql": jql}).status == 200
    assert capsys.readouterr().err.count(WARNING) == 1
    assert len(unrestricted) == 2


def test_explicit_enforcing_assignment_wins_over_permissive_setting(
    unrestricted, monkeypatch, capsys
):
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    surface = create_surface(transport="responder")
    surface.scope_enforcement = "enforcing"
    with pytest.raises(SurfaceError) as error:
        surface.call(SEARCH, {"jql": UNPROVABLE[0]})
    assert error.value.code == 4
    assert WARNING not in capsys.readouterr().err
    assert unrestricted == []


def test_per_call_permissive_is_refused_before_send(unrestricted, capsys):
    surface = create_surface(transport="responder")
    with pytest.raises(SurfaceError) as error:
        surface.call(SEARCH, {"jql": UNPROVABLE[0]}, scope_enforcement="permissive")
    assert error.value.code == 2
    assert "not supported per call" in error.value.messages[0]
    assert WARNING not in capsys.readouterr().err
    assert unrestricted == []


@requires_scope_switch
def test_late_permissive_assignment_checks_policy_and_warns_once(unrestricted, capsys):
    surface = create_surface(transport="responder")
    assert surface.call(SEARCH, {"jql": PROVABLE[0]}).status == 200
    surface.scope_enforcement = "permissive"
    for jql in UNPROVABLE:
        assert surface.call(SEARCH, {"jql": jql}).status == 200
    assert capsys.readouterr().err.count(WARNING) == 1
    surface.scope_allowlist = ("SBX",)
    with pytest.raises(SurfaceError) as error:
        surface.call(SEARCH, {"jql": UNPROVABLE[0]})
    assert error.value.code == 2
    assert len(unrestricted) == 3


@requires_scope_switch
@pytest.mark.parametrize(
    "operation,flags",
    [
        ("getServerInfo", []),
        ("getIssue", ["--issueIdOrKey", "GC-1", "--project", "SBX"]),
        ("getIssue", ["--issueIdOrKey", "10001"]),
    ],
)
def test_permissive_skips_site_and_identity_checks(
    unrestricted, monkeypatch, operation, flags
):
    assert invoke(operation, *flags).exit_code == 4
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", " Permissive ")
    result = invoke(operation, *flags)
    assert result.exit_code == 0, result.output
    assert [call[0] for call in unrestricted] == [operation]


@pytest.mark.parametrize("allowlist", ["SBX", ""])
def test_permissive_with_an_allowlist_is_a_usage_error(
    unrestricted, monkeypatch, allowlist
):
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", allowlist)
    result = invoke(SEARCH, "--jql", "project = SBX")
    usage_error(
        result,
        unrestricted,
        "JIRA_SCOPE_ENFORCEMENT=permissive cannot be combined with a project "
        "allowlist; unset jira.allowed_projects and JIRA_ALLOWED_PROJECTS",
    )
    assert WARNING not in result.stderr


def test_settings_file_allowlist_also_conflicts(unrestricted, monkeypatch):
    ConfigManager.get_instance().config["jira"]["allowed_projects"] = ["SBX"]
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    usage_error(
        invoke(SEARCH, "--jql", "project = SBX"),
        unrestricted,
        "JIRA_SCOPE_ENFORCEMENT=permissive cannot be combined with a project "
        "allowlist; unset jira.allowed_projects and JIRA_ALLOWED_PROJECTS",
    )


@pytest.mark.parametrize("value", ["off", "false", "", "permissive,enforcing"])
def test_invalid_environment_value_is_a_usage_error(unrestricted, monkeypatch, value):
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", value)
    usage_error(
        invoke(SEARCH, "--jql", UNPROVABLE[0]),
        unrestricted,
        "JIRA_SCOPE_ENFORCEMENT must be enforcing or permissive",
    )


@pytest.mark.parametrize("value", [None, True, "Permissive", ["permissive"]])
def test_invalid_setting_is_a_usage_error(unrestricted, value):
    ConfigManager.get_instance().config["jira"]["scope_enforcement"] = value
    usage_error(
        invoke(SEARCH, "--jql", UNPROVABLE[0]),
        unrestricted,
        'jira.scope_enforcement must be "enforcing" or "permissive"',
    )


def test_unvalidated_policy_source_stays_a_usage_error(unrestricted, monkeypatch):
    # A replacement config source bypasses ConfigManager validation; the
    # engine's own check must still surface as exit 2, never a traceback.
    monkeypatch.setattr(ConfigManager, "get_scope_enforcement", lambda _: "sometimes")
    usage_error(
        invoke(SEARCH, "--jql", UNPROVABLE[0]),
        unrestricted,
        "scope_enforcement must be enforcing or permissive",
    )


@requires_scope_switch
def test_setting_enables_permissive_and_environment_overrides_it(
    unrestricted, monkeypatch
):
    config = ConfigManager.get_instance()
    assert config.get_scope_enforcement() == "enforcing"
    config.config["jira"]["scope_enforcement"] = "permissive"
    assert config.get_scope_enforcement() == "permissive"
    result = invoke(SEARCH, "--jql", UNPROVABLE[0])
    assert result.exit_code == 0, result.output
    assert WARNING in result.stderr
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "enforcing")
    assert config.get_scope_enforcement() == "enforcing"
    assert invoke(SEARCH, "--jql", UNPROVABLE[0]).exit_code == 4
    assert len(unrestricted) == 1


def test_older_engine_refuses_permissive_instead_of_silently_enforcing(
    unrestricted, monkeypatch
):
    # An engine without the switch must keep the default guard and refuse opt-out.
    has_scope_switch = isinstance(getattr(Surface, "scope_enforcement", None), property)
    monkeypatch.delattr(Surface, "scope_enforcement", raising=False)
    assert invoke(SEARCH, "--jql", PROVABLE[0]).exit_code == 0
    surface = create_surface(transport="responder")
    # A pre-loaded fixture may bypass configuration on an older engine, which
    # never created this attribute. The default must still be enforcing.
    if not has_scope_switch:
        surface.__dict__.pop("scope_enforcement", None)
    surface.scope_allowlist = None
    surface._scope_loaded = True
    assert surface.call(SEARCH, {"jql": PROVABLE[0]}).status == 200
    monkeypatch.setenv("JIRA_SCOPE_ENFORCEMENT", "permissive")
    result = invoke(SEARCH, "--jql", UNPROVABLE[0])
    assert result.exit_code == 2, result.output
    assert json.loads(result.stderr)["messages"] == [
        "JIRA_SCOPE_ENFORCEMENT=permissive requires an as-engine release "
        "with scope_enforcement support"
    ]
    assert len(unrestricted) == 2
