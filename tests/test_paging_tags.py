"""Generated Jira paging tags preserve hand decisions and resolve publicly."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from as_engine.build import compile_product

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "src/jira_as/specs"
IDS = ("platform", "software", "servicedesk")


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    out = tmp_path_factory.mktemp("jira-paging-indexes")
    compile_product(SPECS, out)
    return {name: json.loads((out / f"{name}.index.json").read_bytes()) for name in IDS}


def test_regeneration_is_stable_and_preserves_bases_and_hand_overrides(tmp_path):
    specs = tmp_path / "specs"
    shutil.copytree(SPECS, specs)
    before = {
        path.name: path.read_bytes() for path in specs.iterdir() if path.is_file()
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_paging_tags.py"),
            "--spec-dir",
            str(specs),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "HAND REVIEW: getAuditRecords" in result.stdout
    assert "HAND REVIEW: getFailedWebhooks" in result.stdout
    for name in (
        "findBulkAssignableUsers",
        "findAssignableUsers",
        "bulkGetUsersMigration",
        "findUsersWithAllPermissions",
        "findUsers",
        "findUsersWithBrowsePermission",
        "getAllUsersDefault",
        "getAllUsers",
    ):
        assert f"HAND REVIEW: {name}" in result.stdout
    assert {
        path.name: path.read_bytes() for path in specs.iterdir() if path.is_file()
    } == before


def test_generated_paging_is_complete_and_the_eleven_token_operations_are_exact(
    compiled,
):
    counts = {
        name: sum(
            "x-as-paging" in op["extensions"] for op in index["operations"].values()
        )
        for name, index in compiled.items()
    }
    # Six platform paging contracts come from hand review; four further
    # post-slice filters are deliberately note-only, with --all unsupported.
    assert counts == {"platform": 185, "software": 18, "servicedesk": 27}
    styles = {}
    for op in compiled["platform"]["operations"].values():
        style = op["extensions"].get("x-as-paging", {}).get("style")
        if style:
            styles[style] = styles.get(style, 0) + 1
    assert styles == {"offset/limit": 83, "none": 96, "nextPageToken": 3, "cursor": 3}
    tokens = [
        op
        for index in compiled.values()
        for op in index["operations"].values()
        if op["extensions"].get("x-as-paging", {}).get("style") == "nextPageToken"
    ]
    assert len(tokens) == 11
    assert {op["operationId"] for op in tokens} == {
        "searchAndReconsileIssuesUsingJql",
        "searchAndReconsileIssuesUsingJqlPost",
        "getBulkChangelogs",
        "getIssuesForBacklogJSIS",
        "getIssuesWithoutEpicForBoardJSIS",
        "getBoardIssuesForEpicJSIS",
        "getIssuesForBoardJSIS",
        "getBoardIssuesForSprintJSIS",
        "getIssuesWithoutEpicJSIS",
        "getIssuesForEpicJSIS",
        "getIssuesForSprintJSIS",
    }
    for op in tokens:
        tag = op["extensions"]["x-as-paging"]
        assert tag["next"] == {"kind": "token", "path": "/nextPageToken"}
        limit = tag["request"]["limit"]
        assert (
            limit["name"] == "maxResults"
            if limit["in"] == "query"
            else limit["path"] == "/maxResults"
        )
    for name in ("searchAndReconsileIssuesUsingJqlPost", "getBulkChangelogs"):
        tag = compiled["platform"]["operations"][name]["extensions"]["x-as-paging"]
        assert tag["request"]["token"] == {"in": "body", "path": "/nextPageToken"}
        assert tag["request"]["limit"] == {"in": "body", "path": "/maxResults"}
    assert (
        "response"
        not in compiled["platform"]["operations"]["getBulkChangelogs"]["extensions"][
            "x-as-paging"
        ]
    )
    assert compiled["servicedesk"]["operations"]["getServiceDesks"]["extensions"][
        "x-as-paging"
    ]["response"] == {"isLastPath": "/isLastPage"}
    for name in ("getPlans", "getTeams"):
        tag = compiled["platform"]["operations"][name]["extensions"]["x-as-paging"]
        assert tag["style"] == "cursor"
        assert tag["next"] == {"kind": "token", "path": "/nextPageCursor"}
    platform = compiled["platform"]["operations"]
    assert (
        platform["getCreateIssueMetaIssueTypes"]["extensions"]["x-as-paging"][
            "itemsPath"
        ]
        == "/issueTypes"
    )
    for name in ("suggestedPrioritiesForMappings", "searchForIssuesUsingJqlPost"):
        tag = platform[name]["extensions"]["x-as-paging"]
        assert tag["request"] == {
            "offset": {"in": "body", "path": "/startAt"},
            "limit": {"in": "body", "path": "/maxResults"},
        }
    assert platform["findUserKeysByQuery"]["extensions"]["x-as-paging"]["request"][
        "limit"
    ] == {"in": "query", "name": "maxResult"}
    for name in (
        "getCommentsByIds",
        "getChangeLogsByIds",
        "findGroups",
        "findUsersForPicker",
    ):
        assert platform[name]["extensions"]["x-as-paging"]["style"] == "none"
    for name in ("addRequestParticipants", "removeRequestParticipants"):
        assert (
            compiled["servicedesk"]["operations"][name]["extensions"]["x-as-paging"][
                "style"
            ]
            == "none"
        )
    generated = json.loads((SPECS / "platform.paging.overlay.json").read_bytes())[
        "actions"
    ]
    reasons = {action["x-as-test"]: action["x-as-reason"] for action in generated}
    assert "explicit comment IDs" in reasons["paging_platform_getCommentsByIds"]
    assert "result cap only" in reasons["paging_platform_findGroups"]


def resolve(schema, document):
    while "$ref" in schema:
        node = document
        for part in schema["$ref"][2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        schema = node
    if "allOf" in schema:
        props = {}
        for child in schema["allOf"]:
            props.update(resolve(child, document).get("properties", {}))
        schema = {**schema, "properties": {**props, **schema.get("properties", {})}}
    return schema


def schema_path(schema, path, document):
    schema = resolve(schema, document)
    for part in filter(None, path.split("/")):
        schema = resolve(schema, document)["properties"][
            part.replace("~1", "/").replace("~0", "~")
        ]
    return resolve(schema, document)


def test_all_generated_tag_parameters_and_paths_resolve(compiled):
    manifest = json.loads((SPECS / "manifest.json").read_bytes())
    for entry in manifest["documents"]:
        document = json.loads((SPECS / entry["file"]).read_bytes())
        for op in compiled[entry["id"]]["operations"].values():
            tag = op["extensions"].get("x-as-paging")
            if not tag:
                continue
            for target in tag["request"].values():
                if target["in"] == "body":
                    request = document["paths"][op["path"]][op["method"].lower()][
                        "requestBody"
                    ]
                    schema = resolve(request, document)["content"]["application/json"][
                        "schema"
                    ]
                    schema_path(schema, target["path"], document)
                else:
                    assert any(
                        p["in"] == target["in"] and p["name"] == target["name"]
                        for p in op["parameters"]
                    ), op["operationId"]
            vendor = document["paths"][op["path"]][op["method"].lower()]
            schema = resolve(vendor["responses"]["200"], document)["content"][
                "application/json"
            ]["schema"]
            assert schema_path(schema, tag["itemsPath"], document)["type"] == "array"
            for field, path in tag.get("response", {}).items():
                resolved = schema_path(schema, path, document)
                assert resolved["type"] == (
                    "boolean" if field == "isLastPath" else "integer"
                )
            if "next" in tag:
                assert (
                    schema_path(schema, tag["next"]["path"], document)["type"]
                    == "string"
                )


def test_hand_override_precedes_generated_paging(tmp_path):
    specs = tmp_path / "specs"
    shutil.copytree(SPECS, specs)
    override = specs / "platform.paging-override.overlay.json"
    hand = json.loads(override.read_bytes())
    generated = json.loads((specs / "platform.paging.overlay.json").read_bytes())
    action = next(
        item
        for item in generated["actions"]
        if item["x-as-test"] == "paging_platform_searchAndReconsileIssuesUsingJql"
    )
    action["x-as-test"] = "paging_hand_precedence_probe"
    action["update"] = {
        "x-as-paging": {"request": {"limit": {"in": "query", "name": "hand-wins"}}}
    }
    hand["actions"].append(action)
    override.write_text(json.dumps(hand))
    out = tmp_path / "out"
    compile_product(specs, out)
    index = json.loads((out / "platform.index.json").read_bytes())
    assert (
        index["operations"]["searchAndReconsileIssuesUsingJql"]["extensions"][
            "x-as-paging"
        ]["request"]["limit"]["name"]
        == "hand-wins"
    )


def test_user_list_hand_decisions_and_schema_caps_are_explicit(compiled):
    operations = compiled["platform"]["operations"]
    note_only = [
        "findBulkAssignableUsers",
        "findAssignableUsers",
        "findUsersWithAllPermissions",
        "findUsersWithBrowsePermission",
    ]
    for name in note_only:
        assert "x-as-paging" not in operations[name]["extensions"]
        assert (
            "empty page does not prove exhaustion"
            in operations[name]["extensions"]["x-as-note"]
        )
    for name in [
        "bulkGetUsersMigration",
        "findUsers",
        "getAllUsersDefault",
        "getAllUsers",
    ]:
        tag = operations[name]["extensions"]["x-as-paging"]
        assert tag["termination"] == "emptyPage" and tag["advance"] == "requested"
    for name in ["getAllUsers", "getAllUsersDefault"]:
        parameter = next(
            p for p in operations[name]["parameters"] if p["name"] == "maxResults"
        )
        assert parameter["schema"]["maximum"] == 1000
