"""Development helpers exercise argv and indexed issue reads without git actions."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as import engine
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
    factory = engine.create_surface
    responder = Responder(factory(transport="responder").indexes.get("platform"))

    def surface(**kwargs):
        result = factory(transport="responder")
        result.scope_allowlist = ("SBX",)
        result.transport_factory = lambda *_: responder
        return result

    monkeypatch.setattr(engine, "create_surface", surface)
    yield responder
    ConfigManager.reset_instance()


def invoke(*args, input=None, expected=0):
    result = CliRunner().invoke(cli, ["dev", *args], input=input)
    assert result.exit_code == expected, (result.output, result.exception)
    return result


@pytest.mark.parametrize(
    "summary,flags,prefix",
    [
        ("", [], "feature"),
        ("!!!", ["--auto-prefix"], "bugfix"),
        ("A" * 150, ["--prefix", "docs"], "docs"),
        ("word " * 40, ["--auto-prefix"], "bugfix"),
    ],
)
def test_branch_names_bound_length_and_handle_empty_sanitized_titles(
    wire, summary, flags, prefix
):
    wire.seed(
        "getIssue",
        [
            {
                "key": "SBX-1",
                "fields": {"summary": summary, "issuetype": {"name": "Bug"}},
            }
        ],
    )
    result = json.loads(
        invoke("branch-name", "SBX-1", *flags, "--output", "json").output
    )
    branch = result["branch_name"]
    assert branch.startswith(prefix + "/sbx-1")
    assert len(branch) <= 80 and not branch.endswith("-")
    assert " " not in branch
    if summary in ("", "!!!"):
        assert branch == prefix + "/sbx-1"
    assert result["git_command"] == "git checkout -b " + branch
    assert [r[0] for r in wire.requests] == ["getIssue"]


@pytest.mark.parametrize("copy_mode", ["absent", "available", "missing"])
@pytest.mark.parametrize("output", ["text", "json"])
def test_pr_description_includes_selected_metadata_criteria_and_clipboard_seam(
    wire, monkeypatch, copy_mode, output
):
    details = ("Details " * 100).rstrip()
    description = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Acceptance Criteria"}],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Saves the report"}
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Background"}],
            },
            {"type": "paragraph", "content": [{"type": "text", "text": details}]},
        ],
    }
    wire.seed(
        "getIssue",
        [
            {
                "key": "SBX-1",
                "self": "https://example.test/rest/api/3/issue/1",
                "fields": {
                    "summary": "Report export",
                    "description": description,
                    "issuetype": {"name": "Task"},
                    "priority": {"name": "High"},
                    "labels": ["reporting"],
                    "components": [{"name": "Core"}],
                },
            }
        ],
    )
    copied = []
    if copy_mode != "absent":
        monkeypatch.setitem(
            sys.modules,
            "pyperclip",
            None if copy_mode == "missing" else SimpleNamespace(copy=copied.append),
        )
    result = invoke(
        "pr-description",
        "SBX-1",
        "--include-checklist",
        "--include-labels",
        "--include-components",
        "--output",
        output,
        *(["--copy"] if copy_mode != "absent" else []),
    )
    markdown = (
        json.loads(result.stdout)["description"] if output == "json" else result.stdout
    )
    for text in (
        "[SBX-1](https://example.test/browse/SBX-1)",
        "**Priority:** High",
        "## Labels",
        "`reporting`",
        "## Components",
        "Core",
        "- [ ] Saves the report",
        "## Testing Checklist",
    ):
        assert text in markdown
    assert details not in markdown
    rendered_description = markdown.split("## Description\n\n", 1)[1].split(
        "\n\n## Labels", 1
    )[0]
    assert len(rendered_description) == 503
    assert rendered_description.endswith("...")
    assert rendered_description.count("Details") > 10
    if copy_mode == "available":
        assert len(copied) == 1
        assert copied[0].rstrip("\n") == markdown.rstrip("\n")
        assert "copied to clipboard" in result.stderr
    elif copy_mode == "missing":
        assert "pyperclip not installed" in result.stderr
        assert copied == []
    assert [r[0] for r in wire.requests] == ["getIssue"]


def test_pr_description_omits_missing_optional_fields(wire):
    wire.seed(
        "getIssue",
        [{"key": "SBX-1", "fields": {"summary": "Minimal", "priority": None}}],
    )
    result = invoke(
        "pr-description", "SBX-1", "--include-labels", "--include-components"
    )
    assert "Minimal" in result.output
    for heading in (
        "## Description",
        "## Labels",
        "## Components",
        "## Acceptance Criteria",
        "## Testing Checklist",
    ):
        assert heading not in result.output


@pytest.mark.parametrize("output", ["text", "json", "csv"])
@pytest.mark.parametrize("project", [None, "sbx"])
def test_commit_stdin_deduplicates_and_filters_without_requests(wire, output, project):
    result = invoke(
        "parse-commits",
        "--from-stdin",
        "--output",
        output,
        *(["--project", project] if project else []),
        input="SBX-1 initial\nOTHER-2 next SBX-1\nSBX-3 follow-up\n",
    )
    keys = ["SBX-1", "SBX-3"] if project else ["SBX-1", "OTHER-2", "SBX-3"]
    if output == "json":
        assert json.loads(result.output) == {"issue_keys": keys, "count": len(keys)}
    else:
        assert result.output.strip() == ("," if output == "csv" else "\n").join(keys)
    assert wire.requests == []


def test_commit_stdin_without_references_is_empty(wire):
    assert (
        invoke("parse-commits", "--from-stdin", input="documentation only\n").output
        == ""
    )
    assert "Must provide message" in invoke("parse-commits", expected=1).output
    assert wire.requests == []
