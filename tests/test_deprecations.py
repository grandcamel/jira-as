"""JAS-47 deprecated search operations at the public argv seam."""

from pathlib import Path

import pytest
from as_engine.build import compile_product
from as_engine.index import ProductIndexes
from as_engine.responder import Responder
from as_engine.surface import Surface
from click.testing import CliRunner

from jira_as.cli.commands import api_cmds
from jira_as.cli.main import cli

SPECS = Path(__file__).resolve().parents[1] / "src/jira_as/specs"


@pytest.fixture(scope="module")
def surface(tmp_path_factory):
    out = tmp_path_factory.mktemp("jas47-deprecations")
    compile_product(SPECS, out)
    indexes = ProductIndexes(out)
    # JAS-46 integration: an explicit allowlist admitting the sandbox project.
    return Surface(indexes, lambda _, index: Responder(index), scope_allowlist=("SBX",))


@pytest.fixture
def invoke(monkeypatch, surface):
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)

    def run(*args):
        return CliRunner().invoke(cli, ["api", *args])

    return run


@pytest.mark.parametrize(
    ("old", "replacement"),
    (
        ("searchForIssuesUsingJql", "searchAndReconsileIssuesUsingJql"),
        ("searchForIssuesUsingJqlPost", "searchAndReconsileIssuesUsingJqlPost"),
    ),
)
def test_describe_deprecated_search_shows_its_replacement(invoke, old, replacement):
    result = invoke("describe", old)
    assert result.exit_code == 0, result.output
    assert replacement in result.stdout


@pytest.mark.parametrize(
    "old", ("searchForIssuesUsingJql", "searchForIssuesUsingJqlPost")
)
def test_search_hides_deprecated_search_operations_without_opt_in(invoke, old):
    hidden = invoke("search", old, "--format", "json")
    assert hidden.exit_code == 0 and hidden.stdout.strip() == "[]", hidden.output
    included = invoke("search", old, "--include-deprecated", "--format", "json")
    assert included.exit_code == 0 and old in included.stdout, included.output


@pytest.mark.parametrize(
    "old", ("searchForIssuesUsingJql", "searchForIssuesUsingJqlPost")
)
def test_responder_calls_warn_for_deprecated_search_operations(invoke, old):
    # JAS-46 integration: the scope guard requires a project clause (GET) or a
    # matching --project for the body-only identity (POST).
    scope = (
        ("--jql", "project = SBX")
        if old == "searchForIssuesUsingJql"
        else ("--project", "SBX", "--field", "jql=project = SBX")
    )
    result = invoke("call", old, *scope)
    assert result.exit_code == 0, result.output
    assert "deprecated" in result.stderr and "replacement:" in result.stderr


def test_literal_search_description_still_finds_statuses_search(invoke):
    result = invoke("describe", "search")
    assert result.exit_code == 0, result.output
    assert "statuses/search" in result.stdout
