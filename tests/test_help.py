"""Help snapshots, budgets, and round trips through public Jira argv."""

import json
import os
from pathlib import Path

import pytest
import requests
from as_engine.help import (
    CAPS,
    TOPICS,
    examples_document,
    operation_document,
    render_help,
    token_estimate,
)
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.engine import create_surface


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("JIRA_AS_TRANSPORT", "responder")
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **kw: pytest.fail("help attempted HTTP")
    )


CASES = {
    "level0": ([], "level0"),
    "group": (["help", "api"], "group"),
    "topic": (["help", "search"], "topic"),
    "paging": (["help", "paging"], "topic"),
    "agile": (["help", "agile", "--tier", "software"], "topic"),
    "level2": (["api", "describe", "getIssue"], "level2"),
    "level3": (
        ["api", "describe", "searchAndReconsileIssuesUsingJql", "--examples"],
        "level3",
    ),
    "topics": (["help", "topics"], "topics"),
}


@pytest.mark.parametrize("name", CASES)
def test_golden_help_and_token_cap(name):
    argv, cap = CASES[name]
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert token_estimate(result.stdout) <= CAPS[cap]
    path = Path(__file__).parent / "golden/help" / (name + ".md")
    if os.environ.get("UPDATE_HELP_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.stdout)
    assert result.stdout == path.read_text()


@pytest.mark.parametrize(
    "name", ["group", "topic", "level2", "level3", "paging", "agile", "topics"]
)
def test_help_json_round_trips_to_exact_markdown(name):
    argv = CASES[name][0]
    runner = CliRunner()
    markdown = runner.invoke(cli, argv)
    structured = runner.invoke(cli, [*argv, "--format", "json"])
    assert structured.exit_code == 0, structured.output
    assert render_help(json.loads(structured.stdout)) + "\n" == markdown.stdout


def test_bare_help_and_json_have_identical_content():
    runner = CliRunner()
    bare = runner.invoke(cli, [])
    assert bare.stdout == runner.invoke(cli, ["help"]).stdout
    structured = runner.invoke(cli, ["help", "--format", "json"])
    assert render_help(json.loads(structured.stdout)) + "\n" == bare.stdout


def test_all_standard_topics_are_bounded_and_unseeded_topics_are_explicit():
    runner = CliRunner()
    for topic in TOPICS:
        result = runner.invoke(cli, ["help", topic])
        assert result.exit_code == 0, result.output
        assert token_estimate(result.stdout) <= CAPS["topic"]
        assert "No entries tagged" not in result.stdout
    assert "No entries tagged" not in runner.invoke(cli, ["help", "paging"]).stdout


def test_every_operation_detail_and_examples_fits_cap():
    for _, index in create_surface(transport="responder").indexes.primary():
        for operation in index.operations.values():
            assert (
                token_estimate(render_help(operation_document(operation, index)) + "\n")
                <= CAPS["level2"]
            ), operation.operationId
            assert (
                token_estimate(render_help(examples_document(operation)) + "\n")
                <= CAPS["level3"]
            ), operation.operationId


def test_paging_continuation_covers_each_tagged_entry_without_silent_truncation():
    surface = create_surface(transport="responder")
    expected = {
        op.operationId
        for _, index in surface.indexes.primary()
        for op in index.operations.values()
        if "paging" in op.extensions.get("x-as-topic", [])
    }
    runner = CliRunner()
    found = set()
    offset = 0
    while True:
        result = runner.invoke(
            cli, ["help", "paging", "--offset", str(offset), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        value = json.loads(result.stdout)
        titles = [
            section["title"] for section in value["sections"] if "title" in section
        ]
        assert not found.intersection(titles)
        found.update(titles)
        assert token_estimate(render_help(value) + "\n") <= CAPS["topic"]
        if not any(
            "Continue:" in section.get("text", "") for section in value["sections"]
        ):
            break
        assert titles
        offset += len(titles)
    assert found == expected


def test_tier_selection_and_examples():
    runner = CliRunner()
    result = runner.invoke(cli, ["help", "paging", "--tier", "servicedesk"])
    assert result.exit_code == 0 and "getServiceDesks" in result.stdout, result.output
    result = runner.invoke(cli, ["help", "api", "--examples"])
    assert result.exit_code == 0 and "jira-as api" in result.stdout, result.output
    assert token_estimate(result.stdout) <= CAPS["level3"]
    assert runner.invoke(cli, ["help", "--examples"]).stdout == result.stdout


def test_full_description_restores_vendor_text():
    runner = CliRunner()
    argv = ["api", "describe", "getIssue", "--format", "json"]
    default = json.loads(runner.invoke(cli, argv).stdout)
    full = json.loads(runner.invoke(cli, [*argv, "--full"]).stdout)
    source = json.loads(
        (
            Path(__file__).parents[1]
            / "src/jira_as/specs/jira-platform-swagger-v3.json"
        ).read_text()
    )
    description = source["paths"]["/rest/api/3/issue/{issueIdOrKey}"]["get"][
        "description"
    ]
    assert full["description"] == description
    assert len(default["description"]) < len(description)


def test_untagged_text_does_not_seed_topics(monkeypatch):
    from dataclasses import replace

    from jira_as import engine

    original = engine.ProductIndexes

    def no_topics(directory):
        indexes = original(directory)
        for _, index in indexes.primary():
            for name, op in list(index.operations.items()):
                index.operations[name] = replace(
                    op,
                    summary="paging search agile",
                    extensions={
                        key: value
                        for key, value in op.extensions.items()
                        if key != "x-as-topic"
                    },
                )
        return indexes

    monkeypatch.setattr(engine, "ProductIndexes", no_topics)
    assert "No entries tagged" in CliRunner().invoke(cli, ["help", "paging"]).stdout
