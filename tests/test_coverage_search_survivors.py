"""Search query validation and metadata filtering through local indexed calls."""

import json
from pathlib import Path

import pytest
from as_engine.responder import Responder
from assistant_skills_lib.cache import SkillCache
from click.testing import CliRunner

from jira_as import autocomplete_cache, engine
from jira_as.autocomplete_cache import AutocompleteCache
from jira_as.cli.main import cli
from jira_as.config_manager import ConfigManager


@pytest.fixture
def wire(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network and credential access are forbidden")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ConfigManager, "_find_claude_dir", lambda self: None)
    monkeypatch.setattr(ConfigManager, "get_credentials", denied)
    monkeypatch.setattr("requests.sessions.Session.request", denied)
    monkeypatch.setattr("socket.socket.connect", denied)
    for name in ("JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET", "JIRA_AS_CASSETTE"):
        monkeypatch.delenv(name, raising=False)
    ConfigManager.reset_instance()
    cache = SkillCache("coverage-search", cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        autocomplete_cache, "_autocomplete_cache", AutocompleteCache(cache)
    )
    factory = engine.create_surface
    responder = Responder(factory(transport="responder").indexes.get("platform"))

    def surface(**kwargs):
        result = factory(transport="responder")
        result.scope_allowlist = ("SBX",)
        result.scope_allow_site = True
        result.transport_factory = lambda *_: responder
        return result

    monkeypatch.setattr(engine, "create_surface", surface)
    yield responder
    cache.close()
    ConfigManager.reset_instance()


def invoke(*args, expected=0):
    result = CliRunner().invoke(cli, ["search", *args])
    assert result.exit_code == expected, (result.output, result.exception)
    return result


@pytest.mark.parametrize("valid", [False, True])
@pytest.mark.parametrize("output", ["text", "json"])
def test_built_query_validation_preserves_errors_and_exit_status(wire, valid, output):
    errors = [] if valid else ["Unknown field: missing"]
    wire.seed("parseJqlQueries", [{"queries": [{"errors": errors}]}])
    result = invoke(
        "build",
        "--clause",
        "project = SBX",
        "--clause",
        "status = Open",
        "--operator",
        "OR",
        "--order-by",
        "created",
        "--desc",
        "--validate",
        "--output",
        output,
        expected=0 if valid else 1,
    )
    jql = "project = SBX OR status = Open ORDER BY created DESC"
    assert wire.requests == [
        ("parseJqlQueries", {"validation": "strict"}, {"queries": [jql]})
    ]
    if output == "json":
        assert json.loads(result.output) == {
            "jql": jql,
            "valid": valid,
            "errors": errors,
        }
    else:
        assert jql in result.output
        assert (
            "Query validated successfully" if valid else "Validation FAILED:"
        ) in result.output
        if not valid:
            assert errors[0] in result.output


def test_local_query_assembly_refuses_missing_and_unknown_template(wire):
    assert "Provide --clause or --template" in invoke("build", expected=1).output
    assert (
        "Unknown template"
        in invoke("build", "--template", "does-not-exist", expected=2).output
    )
    assert "Available Templates:" in invoke("build", "--list-templates").output
    result = invoke("build", "--clause", "project = SBX", "--order-by", "created")
    assert "project = SBX ORDER BY created ASC" in result.output
    assert "Use --validate" in result.output
    assert wire.requests == []


@pytest.mark.parametrize("kind", ["custom", "system"])
def test_field_filters_use_cached_metadata_and_refresh_replaces_it(wire, kind):
    fields = [
        {"value": "summary", "displayName": "Summary", "operators": ["~"]},
        {
            "value": "cf[10016]",
            "displayName": "Story Points",
            "cfid": "customfield_10016",
            "operators": ["=", ">"],
        },
    ]
    wire.seed(
        "getAutoComplete", [{"visibleFieldNames": fields}, {"visibleFieldNames": []}]
    )
    chosen = fields[1 if kind == "custom" else 0]
    args = (
        "fields",
        f"--{kind}-only",
        "--filter",
        chosen["displayName"].upper(),
        "--output",
        "json",
    )
    assert json.loads(invoke(*args).output) == [chosen]
    assert json.loads(invoke(*args).output) == [chosen]
    assert len(wire.requests) == 1
    assert json.loads(invoke(*args, "--refresh").output) == []
    assert len(wire.requests) == 2


def test_mutually_exclusive_field_filters_send_nothing(wire):
    result = invoke("fields", "--custom-only", "--system-only", expected=1)
    assert "mutually exclusive" in result.output
    assert wire.requests == []


@pytest.mark.parametrize("output", ["text", "json"])
def test_function_filters_select_list_return_type_and_name(wire, output):
    selected = {
        "value": "membersOf()",
        "displayName": "Members",
        "isList": "true",
        "types": ["java.lang.String"],
    }
    wire.seed(
        "getAutoComplete",
        [
            {
                "visibleFunctionNames": [
                    selected,
                    {"value": "currentUser()", "isList": "false", "types": ["User"]},
                ]
            }
        ],
    )
    result = invoke(
        "functions",
        "--filter",
        "MEMBERS",
        "--list-only",
        "--type",
        "string",
        "--with-examples",
        "--no-cache",
        "--output",
        output,
    )
    if output == "json":
        assert json.loads(result.output) == [selected]
    else:
        assert "membersOf()" in result.output
        assert "currentUser()" not in result.output
        assert "Total: 1 functions" in result.output
    assert [r[0] for r in wire.requests] == ["getAutoComplete"]


@pytest.mark.parametrize("refresh_flag", ["--refresh", "--no-cache"])
def test_suggestion_cache_hit_refresh_and_bypass(wire, refresh_flag):
    values = [{"value": "Open", "displayName": "Open"}]
    wire.seed(
        "getFieldAutoCompleteForQueryString", [{"results": values}, {"results": []}]
    )
    args = ("suggest", "--field", "status", "--prefix", "O", "--output", "json")
    assert json.loads(invoke(*args).output) == values
    assert json.loads(invoke(*args).output) == values
    assert len(wire.requests) == 1
    assert json.loads(invoke(*args, refresh_flag).output) == []
    assert wire.requests[-1][1] == {"fieldName": "status", "fieldValue": "O"}
    assert len(wire.requests) == 2
