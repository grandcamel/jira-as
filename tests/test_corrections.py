"""JAS-47 correction contracts through the compiled product seam."""

import json
from pathlib import Path

import pytest
from as_engine.build import compile_product
from as_engine.index import ProductIndexes
from as_engine.responder import Responder
from as_engine.surface import Surface

SPECS = Path(__file__).resolve().parents[1] / "src/jira_as/specs"


def _mismatched_enum_defaults(value):
    if isinstance(value, dict):
        if "enum" in value and "default" in value:
            yield value
        for child in value.values():
            yield from _mismatched_enum_defaults(child)
    elif isinstance(value, list):
        for child in value:
            yield from _mismatched_enum_defaults(child)


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    out = tmp_path_factory.mktemp("jas47-corrections")
    compile_product(SPECS, out)
    return {
        name: json.loads((out / f"{name}.index.json").read_bytes())
        for name in ("platform", "software", "servicedesk")
    }, ProductIndexes(out)


def test_compiled_indexes_have_no_enum_default_mismatch(compiled):
    indexes, _ = compiled
    for name, index in indexes.items():
        for schema in _mismatched_enum_defaults(index):
            assert schema["default"] in schema["enum"], name


def test_corrected_descriptions_do_not_expose_invalid_defaults(compiled):
    _, indexes = compiled
    surface = Surface(indexes, lambda _, index: Responder(index))
    for operation_id, parameter_name in (
        ("getAllUserDataClassificationLevels", "status"),
        ("getFieldsPaginated", "type"),
        ("getScreens", "scope"),
        ("getWorkflowTransitionRuleConfigurations", "types"),
    ):
        described = surface.describe(operation_id)
        parameter = next(
            item for item in described["parameters"] if item["name"] == parameter_name
        )
        assert "default" not in parameter.get("schema", {}).get("items", {})


def test_imported_adf_definitions_match_the_vendor_pin():
    """The copy is mechanically relocated, never a weakened hand-edited schema."""
    from importlib.resources import files

    vendor = json.loads(
        files("as_engine.converters").joinpath("schema/full-57.3.4.json").read_text()
    )["definitions"]

    def relocate(value):
        if isinstance(value, dict):
            return {
                key: "#/components/schemas/Adf_" + child.removeprefix("#/definitions/")
                if key == "$ref"
                and isinstance(child, str)
                and child.startswith("#/definitions/")
                else relocate(child)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [relocate(child) for child in value]
        return value

    overlay = json.loads((SPECS / "platform.overlay.json").read_text())
    action = next(
        a for a in overlay["actions"] if a["x-as-test"] == "jas47_adf_schema_import"
    )
    assert action["update"] == {
        "Adf_" + name: relocate(schema) for name, schema in vendor.items()
    }


@pytest.mark.parametrize("method", ["get", "post"])
def test_search_examples_correct_only_plain_adf_fields(compiled, method):
    from as_engine.converters import convert, validate_adf

    source = json.loads((SPECS / "jira-platform-swagger-v3.json").read_text())
    operation = source["paths"]["/rest/api/3/search/jql"][method]
    expected = json.loads(
        operation["responses"]["200"]["content"]["application/json"]["example"]
    )
    for issue in expected["issues"]:
        for name in ("description", "environment"):
            if isinstance(issue.get("fields", {}).get(name), str):
                issue["fields"][name] = convert(issue["fields"][name])
                assert validate_adf(issue["fields"][name])
    _, indexes = compiled
    actual = json.loads(
        indexes.get("platform").operations[operation["operationId"]].response_example
    )
    assert actual == expected
