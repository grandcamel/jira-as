"""Release migration coverage must survive missing rows and stale documents."""

import json
import re
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = runpy.run_path(str(ROOT / "scripts/generate_client_method_mapping.py"))


def test_method_mapping_covers_frozen_120_inventory():
    inventory = json.loads(GENERATOR["FIXTURE"].read_text())
    assert len(inventory["JiraClient"]) == 259
    assert len(inventory["AutomationClient"]) == 21
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", value) for value in inventory["blobs"].values()
    )
    rendered = GENERATOR["render"](inventory)
    assert GENERATOR["OUTPUT"].read_text() == rendered
    for class_name in ("JiraClient", "AutomationClient"):
        section = rendered.split(f"## {class_name}\n", 1)[1].split("\n## ", 1)[0]
        names = re.findall(r"^\| `([^`]+)` \|", section, re.MULTILINE)
        assert sorted(names) == inventory[class_name]
    missing = dict(inventory, JiraClient=inventory["JiraClient"][:-1])
    with pytest.raises(ValueError, match="exactly cover"):
        GENERATOR["render"](missing)


def test_capture_excludes_private_and_inherited_members():
    source = """
class Parent:
    def inherited(self): pass
class Client(Parent):
    def __init__(self): pass
    def _private(self): pass
    def public(self): pass
    @property
    def config(self): pass
    async def asynchronous(self): pass
"""
    assert GENERATOR["public_members"](source, "Client") == [
        "asynchronous",
        "config",
        "public",
    ]


def test_mapping_targets_exist_in_indexes_or_frozen_survivors():
    operations = {
        name
        for path in (ROOT / "src/jira_as/_generated").glob("*.index.json")
        for name in json.loads(path.read_text())["operations"]
    }
    rows = json.loads((ROOT / "tests/wrapper_verbs.json").read_text())
    survivors = {row["verb"] for row in rows if row["decision"] == "survivor"}
    for target in GENERATOR["TARGETS"].values():
        assert target
        if target.startswith("verb: "):
            assert target[6:] in survivors
        elif target.startswith("note: "):
            continue
        else:
            assert set(target.split(", ")) <= operations


def test_changelog_contains_every_frozen_verb_and_identity_rename():
    changelog = (ROOT / "CHANGELOG.md").read_text().split("## [1.2.0]", 1)[0]
    rows = json.loads((ROOT / "tests/wrapper_verbs.json").read_text())
    assert len(rows) == 208
    for row in rows:
        expected = (
            f"| `{row['verb']}` | `{row['replacement']}` |"
            if row["decision"] == "dropped"
            else f"- `{row['verb']}`"
        )
        assert expected in changelog
    renames = []
    for path in (ROOT / "src/jira_as/specs").glob("*.identity.overlay.json"):
        for action in json.loads(path.read_text())["actions"]:
            old = re.search(r"Atlassian operationId (\w+) at ", action["description"])[
                1
            ]
            new = action["update"]["operationId"]
            route, method = re.fullmatch(
                r'\$\.paths\["([^"]+)"\]\.(\w+)', action["target"]
            ).groups()
            expected = (
                f"| {path.name.split('.')[0]} | `{old}` | "
                f"`{method.upper()} {route}` | `{new}` |"
            )
            assert expected in changelog
            renames.append(new)
    assert len(renames) == 20
