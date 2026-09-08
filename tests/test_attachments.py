"""JAS-65 attachments through public argv and genuine offline transports."""

import hashlib
import json
from pathlib import Path

import pytest
import requests
from as_engine.help import CAPS, token_estimate
from as_engine.responder import Responder
from click.testing import CliRunner

from jira_as.cli.commands import api_cmds
from jira_as.cli.main import cli
from jira_as.engine import create_surface


@pytest.fixture
def attachment_surface(monkeypatch):
    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **kw: pytest.fail("unexpected HTTP")
    )
    surface = create_surface(transport="responder")
    surface.scope_allowlist = ("SBX",)
    surface.scope_allow_site = True
    responders = []

    def factory(document, index):
        responder = Responder(index)
        responders.append(responder)
        return responder

    surface.transport_factory = factory
    monkeypatch.setattr(api_cmds, "create_surface", lambda **_: surface)
    return surface, responders


def invoke(*args):
    return CliRunner().invoke(cli, ["api", "--transport", "responder", *args])


def test_add_attachment_uses_multipart_without_request_tag(
    attachment_surface, tmp_path
):
    surface, responders = attachment_surface
    upload = tmp_path / "sample.txt"
    upload.write_bytes(b"JAS-65 synthetic upload\n")
    result = invoke(
        "call", "addAttachment", "--issueIdOrKey", "SBX-1", "--field", f"file=@{upload}"
    )
    assert result.exit_code == 0, result.output
    _, _, operation = surface.resolve("addAttachment")
    assert operation.request_media_types == ["multipart/form-data"]
    assert "x-as-response" not in operation.extensions
    assert len(responders) == 1 and len(responders[0].requests) == 1
    wire = responders[0].wire_requests[0]
    assert wire["operationId"] == "addAttachment"
    assert wire["headers"] == {"X-Atlassian-Token": "nocheck"}
    assert wire["parts"] == [
        {
            "name": "file",
            "filename": upload.name,
            "size": len(upload.read_bytes()),
            "content_type": "text/plain",
            "sha256": hashlib.sha256(upload.read_bytes()).hexdigest(),
        }
    ]


@pytest.mark.parametrize(
    "operation", ["getAttachmentContent", "getAttachmentThumbnail"]
)
@pytest.mark.parametrize("equals", [False, True])
def test_binary_download_to_explicit_output(
    attachment_surface, tmp_path, operation, equals
):
    destination = tmp_path / "download with spaces.bin"
    flags = [f"--output={destination}"] if equals else ["--output", str(destination)]
    result = invoke("call", operation, "--id", "10000", *flags)
    assert result.exit_code == 0, result.output
    expected = f"as-engine responder binary {operation}\n".encode()
    assert destination.read_bytes() == expected
    assert json.loads(result.output) == {
        "path": str(destination),
        "bytes": len(expected),
        "content_type": "application/octet-stream",
    }
    assert len(attachment_surface[1][0].requests) == 1


@pytest.mark.parametrize(
    "operation", ["getAttachmentContent", "getAttachmentThumbnail"]
)
def test_binary_tag_selects_default_filename(
    attachment_surface, monkeypatch, tmp_path, operation
):
    monkeypatch.chdir(tmp_path)
    result = invoke("call", operation, "--id", "10000")
    assert result.exit_code == 0, result.output
    assert Path(json.loads(result.output)["path"]).read_bytes() == (
        f"as-engine responder binary {operation}\n".encode()
    )


@pytest.mark.parametrize(
    "flags,message",
    [
        (["--output"], "Missing value for --output"),
        (["--output="], "Missing value for --output"),
        (["--output", "--confirm"], "Missing value for --output"),
        (["--output=a", "--output=b"], "Duplicate flag: --output"),
        (["--output", "a", "--output", "b"], "Duplicate flag: --output"),
        (["--output=a", "--bogus"], "Unknown flag: --bogus"),
        (["--output=a", "--body"], "Missing value for --body"),
    ],
)
def test_output_flag_usage_errors_send_nothing(attachment_surface, flags, message):
    result = invoke("call", "getAttachmentContent", "--id", "10000", *flags)
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["messages"] == [message]
    assert attachment_surface[1] == []


def test_attachment_id_does_not_authorize_site_scope(
    attachment_surface, monkeypatch, tmp_path
):
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "false")
    surface, responders = attachment_surface
    surface.scope_allow_site = False
    destination = tmp_path / "refused.bin"
    result = invoke(
        "call", "getAttachmentContent", "--id", "10000", "--output", str(destination)
    )
    assert result.exit_code == 4, result.output
    assert responders == []
    assert not destination.exists()


def test_binary_output_help_and_caps(attachment_surface):
    result = invoke("call", "--help")
    assert result.exit_code == 0 and "--output PATH" in result.output
    for operation in ("getAttachmentContent", "getAttachmentThumbnail"):
        for args in (("describe", operation), ("call", operation, "--help")):
            result = invoke(*args)
            assert result.exit_code == 0, result.output
            assert "--output PATH" in result.output
            assert "same-origin redirect" in result.output
            assert token_estimate(result.stdout) <= CAPS["level2"]
