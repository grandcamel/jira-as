"""Jira rich text through public argv and the recorded transport boundary."""

import json
from copy import deepcopy

import pytest
import requests
from as_engine.converters import convert, validate_adf
from as_engine.responder import Responder
from as_engine.transport import Response
from click.testing import CliRunner

from jira_as.cli.main import cli


@pytest.fixture
def wire(monkeypatch):
    """Observe the final request, with an explicitly controlled response body."""
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **k: pytest.fail("unexpected HTTP")
    )
    # JAS-46 integration: the scope guard needs an allowlist and the site
    # opt-in for the bulk and collection operations exercised here.
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    recorded = []
    response = [{}]

    def call(self, operation, parameters, body):
        recorded.append((operation.operationId, deepcopy(parameters), deepcopy(body)))
        return Response(200, deepcopy(response[0]), {"X-Test": "preserved"})

    monkeypatch.setattr(Responder, "call", call)
    return recorded, response


def invoke(*args, input=None):
    return CliRunner().invoke(
        cli, ["api", "--transport", "responder", "call", *args], input=input
    )


def create_args():
    return (
        "createIssue",
        "--project",
        "SBX",
        "--field",
        "fields.project.key=SBX",
        "--field",
        "fields.summary=x",
        "--field",
        "fields.issuetype.name=Task",
    )


def test_create_issue_markdown_file_sends_schema_valid_adf(wire, tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(
        "# Notes\n\nHello **world**\n\n1. First\n2. Second", encoding="utf-8"
    )
    result = invoke(*create_args(), "--field", f"fields.description=@{path}")
    assert result.exit_code == 0 and result.stderr == "", result.output
    fields = wire[0][-1][2]["fields"]
    assert fields["project"] == {"key": "SBX"}
    assert validate_adf(fields["description"])
    assert [n["type"] for n in fields["description"]["content"]] == [
        "heading",
        "paragraph",
        "orderedList",
    ]


@pytest.mark.parametrize(
    "name,path,extra",
    [
        ("addComment", "body", ()),
        ("updateComment", "body", ("--id", "1")),
        ("addWorklog", "comment", ("--field", "timeSpentSeconds=60")),
        ("updateWorklog", "comment", ("--id", "1", "--field", "timeSpentSeconds=60")),
        ("editIssue", "fields.environment", ()),
    ],
)
def test_comment_worklog_and_issue_paths_convert_files(
    wire, tmp_path, name, path, extra
):
    notes = tmp_path / "notes.md"
    notes.write_text("A **bold** note\n\nNext paragraph", encoding="utf-8")
    result = invoke(
        name,
        "--issueIdOrKey",
        "SBX-1",
        *extra,
        "--field",
        f"{path}=@{notes}",
        *(("--validate-body",) if name != "editIssue" else ()),
    )
    assert result.exit_code == 0, result.output
    sent = wire[0][-1][2]
    for part in path.split("."):
        sent = sent[part]
    assert validate_adf(sent) and len(sent["content"]) == 2


@pytest.mark.parametrize(
    "text", ["", "#", "null", "123", '{"looks":"json"}', r"first\nsecond"]
)
def test_tagged_field_is_literal_markdown(wire, text):
    result = invoke(*create_args(), "--field", "fields.description=" + text)
    assert result.exit_code == 0, result.output
    document = wire[0][-1][2]["fields"]["description"]
    assert validate_adf(document)
    if text == r"first\nsecond":
        assert len(document["content"]) == 1
        assert "\n" not in document["content"][0]["content"][0]["text"]
    if text not in ("", "#", r"first\nsecond"):
        assert document["content"][0]["content"][0]["text"] == text


@pytest.mark.parametrize("name", ["createIssue", "editIssue"])
def test_custom_fields_remain_verbatim_and_encoded_adf_passes_through(wire, name):
    encoded = convert("already ADF")
    body = {
        "fields": {
            "project": {"key": "SBX"},
            "description": "**convert**",
            "customfield_10010": "**unchanged**",
            "customfield_10011": encoded,
        }
    }
    # JAS-46 integration: createIssue's identity lives in the body and needs
    # a matching --project; editIssue is keyed by --issueIdOrKey.
    extra = ("--issueIdOrKey", "SBX-1") if name == "editIssue" else ("--project", "SBX")
    result = invoke(name, *extra, "--body", "-", input=json.dumps(body))
    assert result.exit_code == 0, result.output
    fields = wire[0][-1][2]["fields"]
    assert validate_adf(fields["description"])
    assert fields["customfield_10010"] == "**unchanged**"
    assert fields["customfield_10011"] == encoded


@pytest.mark.parametrize("source", ["stdin", "field"])
def test_bulk_issue_paths_convert_only_within_each_item(wire, source):
    items = [
        {"fields": {"description": "# One", "customfield_10010": "plain"}},
        {"fields": {"environment": "Two", "description": None}},
        {"fields": {"summary": "Three"}},
    ]
    result = (
        invoke("createIssues", "--body", "-", input=json.dumps({"issueUpdates": items}))
        if source == "stdin"
        else invoke("createIssues", "--field", "issueUpdates=" + json.dumps(items))
    )
    assert result.exit_code == 0, result.output
    sent = wire[0][-1][2]["issueUpdates"]
    assert validate_adf(sent[0]["fields"]["description"])
    assert validate_adf(sent[1]["fields"]["environment"])
    assert sent[0]["fields"]["customfield_10010"] == "plain"
    assert sent[1]["fields"]["description"] is None
    assert sent[2] == items[2]


def test_missing_markdown_file_refuses_before_transport(wire, tmp_path):
    result = invoke(
        *create_args(), "--field", f"fields.description=@{tmp_path / 'missing'}"
    )
    assert result.exit_code == 2 and "cannot read rich-text file" in result.stderr
    assert wire[0] == []


def test_read_mention_round_trip_and_raw_preserve_metadata(wire, tmp_path):
    document = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "mention", "attrs": {"id": "account-7", "text": "@Ada"}}
                ],
            }
        ],
    }
    wire[1][0] = {"id": "1", "body": document, "author": {"accountId": "account-8"}}
    result = invoke("getComment", "--issueIdOrKey", "SBX-1", "--id", "1")
    assert result.exit_code == 0, result.output
    rendered = json.loads(result.stdout)
    assert rendered["author"] == {"accountId": "account-8"}
    assert "{{as:1:adf:inline:mention:" in rendered["body"]
    notes = tmp_path / "read.md"
    notes.write_text(rendered["body"])
    result = invoke(
        "updateComment",
        "--issueIdOrKey",
        "SBX-1",
        "--id",
        "1",
        "--field",
        f"body=@{notes}",
        "--raw",
    )
    assert result.exit_code == 0, result.output
    assert wire[0][-1][2]["body"] == document
    assert validate_adf(document) and json.loads(result.stdout) == wire[1][0]


@pytest.mark.parametrize(
    "name,body,extra",
    [
        (
            "getIssue",
            {
                "fields": {
                    "description": convert("hello"),
                    "environment": None,
                    "summary": "keep",
                }
            },
            ("--issueIdOrKey", "SBX-1"),
        ),
        (
            "getComments",
            {"comments": [{"id": "1", "body": convert("hello")}], "total": 1},
            ("--issueIdOrKey", "SBX-1"),
        ),
        (
            "getWorklogsForIds",
            [{"id": "1", "comment": convert("hello")}, {"id": "2", "comment": None}],
            ("--field", "ids=[1,2]"),
        ),
        (
            "searchAndReconsileIssuesUsingJql",
            {"issues": [{"fields": {"description": convert("hello")}}], "isLast": True},
            ("--jql", "project = SBX"),
        ),
    ],
)
def test_read_collection_and_optional_null_rendering(wire, name, body, extra):
    wire[1][0] = body
    result = invoke(name, *extra)
    assert result.exit_code == 0, result.output
    assert '"hello"' in result.stdout and '"type": "doc"' not in result.stdout
    result = invoke(name, *extra, "--raw")
    assert result.exit_code == 0 and json.loads(result.stdout) == body, result.output


def test_jsm_plain_request_and_comment_modes_stay_unchanged(wire):
    body = {
        "serviceDeskId": "10",
        "requestTypeId": "25",
        "isAdfRequest": False,
        "requestFieldValues": {
            "description": "*plain wiki*",
            "customfield_10010": "unchanged",
        },
    }
    result = invoke("createCustomerRequest", "--body", "-", input=json.dumps(body))
    assert result.exit_code == 0 and wire[0][-1][2] == body, result.output
    result = invoke(
        "createRequestComment",
        "--issueIdOrKey",
        "SBX-1",
        "--field",
        "body=*plain wiki*",
        "--field",
        "public=false",
    )
    assert result.exit_code == 0, result.output
    assert wire[0][-1][2] == {"body": "*plain wiki*", "public": False}


def test_jira_single_representation_call_help_names_default(wire):
    result = invoke("addComment", "--help")
    assert result.exit_code == 0, result.output
    assert "default adf" in result.stdout and "--raw" in result.stdout
    assert wire[0] == []


def test_acceptance_transcripts(wire, tmp_path):
    """Printable argv, exits and final request bodies for offline acceptance."""
    notes = tmp_path / "notes.md"
    notes.write_text("# Notes\n\nHello **world**")
    for name, args, path in [
        (
            "createIssue",
            (*create_args(), "--field", f"fields.description=@{notes}"),
            ("fields", "description"),
        ),
        (
            "addComment",
            ("addComment", "--issueIdOrKey", "SBX-1", "--field", f"body=@{notes}"),
            ("body",),
        ),
    ]:
        result = invoke(*args)
        assert result.exit_code == 0, result.output
        document = wire[0][-1][2]
        for part in path:
            document = document[part]
        valid = validate_adf(document)
        print(
            "TRANSCRIPT "
            + json.dumps(
                {
                    "case": name,
                    "argv": [
                        "jira-as",
                        "api",
                        "--transport",
                        "responder",
                        "call",
                        *args,
                    ],
                    "exit": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "request": wire[0][-1],
                    "valid_adf": valid,
                }
            )
        )


def test_free_map_body_validation_is_a_documented_engine_limit(wire):
    result = invoke(
        *create_args(),
        "--field",
        "fields.description=valid Markdown",
        "--validate-body",
    )
    assert result.exit_code == 2, result.output
    assert (
        "body.fields: unsupported schema validator: additionalProperties"
        in result.stderr
    )
    assert wire[0] == []
