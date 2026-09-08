"""Legacy ADF emission remains valid while library importers keep it alive."""

import json
from importlib.resources import files

import pytest
from jsonschema import Draft4Validator

from jira_as import adf_helper


@pytest.fixture(scope="module")
def validator():
    schema = files("as_engine.converters.schema").joinpath("full-57.3.4.json")
    return Draft4Validator(json.loads(schema.read_text(encoding="utf-8")))


@pytest.mark.parametrize("text", ["", " ", "plain text", "first\n\nsecond"])
@pytest.mark.parametrize(
    "function",
    ["text_to_adf", "markdown_to_adf", "wiki_markup_to_adf", "ensure_adf"],
)
def test_document_emitters_validate(validator, function, text):
    document = getattr(adf_helper, function)(text)
    # ensure_adf preserves an absent/empty optional value rather than emitting a doc.
    if function == "ensure_adf" and not document:
        return
    validator.validate(document)


@pytest.mark.parametrize("text", ["", " ", "plain text"])
@pytest.mark.parametrize(
    "function", ["create_adf_paragraph", "create_adf_heading", "create_adf_code_block"]
)
def test_node_emitters_validate_in_document(validator, function, text):
    node = getattr(adf_helper, function)(text)
    validator.validate({"type": "doc", "version": 1, "content": [node]})


@pytest.mark.parametrize(
    "text", ["", "plain", "**bold**", "[link|https://example.com]"]
)
@pytest.mark.parametrize("function", ["_parse_inline_formatting", "_parse_wiki_inline"])
def test_inline_emitters_validate_in_document(validator, function, text):
    nodes = getattr(adf_helper, function)(text)
    validator.validate(
        {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": nodes}],
        }
    )


def test_field_wrapper_and_preencoded_document_validate(validator):
    document = adf_helper.markdown_to_adf("**Ready**\n\nText")
    validator.validate(adf_helper.ensure_adf(document))
    wrapped = adf_helper.auto_wrap_adf_fields({"description": "Ready"})
    validator.validate(wrapped["description"])


@pytest.mark.parametrize(
    "text",
    ["```\n```", "```\n\n```", "# ", "## ", "### ", "- ", "* ", "1. "],
)
def test_empty_markdown_blocks_validate(validator, text):
    validator.validate(adf_helper.markdown_to_adf(text))
