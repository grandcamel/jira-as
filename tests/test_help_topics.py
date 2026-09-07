"""Source-backed Jira topic content and continuation at the public help seam."""

import json
from pathlib import Path

import pytest
from as_engine.help import CAPS, TOPICS, render_help, token_estimate
from click.testing import CliRunner

from jira_as.cli.main import cli

SPECS = Path(__file__).resolve().parents[1] / "src/jira_as/specs"


def invoke(*args):
    return CliRunner().invoke(cli, list(args))


@pytest.mark.parametrize("topic", TOPICS)
def test_seeded_topics_are_nonempty_and_json_round_trips(topic):
    markdown = invoke("help", topic)
    structured = invoke("help", topic, "--format", "json")
    assert markdown.exit_code == structured.exit_code == 0, markdown.output
    assert "No entries tagged" not in markdown.stdout
    assert token_estimate(markdown.stdout) <= CAPS["topic"]
    assert render_help(json.loads(structured.stdout)) + "\n" == markdown.stdout


@pytest.mark.parametrize(
    "topic,phrases",
    [
        (
            "project-types",
            (
                "team-managed",
                "company-managed",
                "gh-scrum-template",
                "classic",
                "next-gen",
            ),
        ),
        ("adf", ("ADF", "Markdown")),
        ("fields", ("custom",)),
        ("rate-limits", ("Retry-After",)),
        ("search", ("searchAndReconsileIssuesUsingJql",)),
    ],
)
def test_required_gotchas_are_rendered_from_entries(topic, phrases):
    result = invoke("help", topic)
    assert result.exit_code == 0, result.output
    for phrase in phrases:
        assert phrase in result.stdout


def test_every_seeded_note_has_provenance_and_a_generated_entry_id():
    from tests.test_enrichment_entries import entry_case_ids

    ids = entry_case_ids()
    notes = []
    for path in SPECS.glob("*.overlay.json"):
        for action in json.loads(path.read_text())["actions"]:
            if action["x-as-test"].startswith("jas47_note_"):
                notes.append(action)
                assert ids.count(action["x-as-test"]) == 1
                assert action["x-as-evidence"]["url"].startswith("https://")
                assert action["x-as-evidence"]["date"] in {"2026-09-06", "2026-09-07"}
                assert "JAS-47" in action["x-as-origin"]
    assert len(notes) == 31


def test_custom_field_and_jsm_deferrals_are_visible_in_describe():
    for operation in ("createIssue", "editIssue", "createCustomerRequest"):
        result = invoke("api", "describe", operation)
        assert result.exit_code == 0, result.output
        assert "JAS-49" in result.stdout
    assert "isAdfRequest" in invoke("api", "describe", "createCustomerRequest").stdout


def test_all_topic_pages_fit_cap_without_silent_entry_loss():
    runner = CliRunner()
    for topic in TOPICS:
        offset = 0
        seen = set()
        while True:
            result = runner.invoke(
                cli, ["help", topic, "--offset", str(offset), "--format", "json"]
            )
            assert result.exit_code == 0, result.output
            value = json.loads(result.stdout)
            assert token_estimate(render_help(value) + "\n") <= CAPS["topic"]
            titles = [
                section["title"] for section in value["sections"] if "title" in section
            ]
            assert not seen.intersection(titles)
            seen.update(titles)
            if not any(
                "Continue:" in section.get("text", "") for section in value["sections"]
            ):
                break
            assert titles
            offset += len(titles)
        assert seen, topic
