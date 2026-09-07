"""Pinned Jira inputs and actual backend artifacts, entirely offline."""

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
from as_engine.build import compile_product

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "src/jira_as/specs"
IDS = ("platform", "software", "servicedesk")
# Independent host fetch receipt, 2026-09-07T10:51:10Z.
PINNED_HASHES = {
    "platform": "713089acf94527c571cf0e8e7296e0ce6f886390e681c94a1f14c272881de6dd",
    "software": "4e108d54b99064475c6ba0f986cce46dcace81336e034b58a5400b93174b927a",
    "servicedesk": "7bc2b340a4a92fd5c79990be0bb93fc4659575bf7e310f92571b090d04581e6d",
}


def test_bases_match_recorded_pins_and_all_indexes_are_unique(tmp_path):
    manifest = json.loads((SPECS / "manifest.json").read_bytes())
    assert [entry["id"] for entry in manifest["documents"]] == list(IDS)
    for entry in manifest["documents"]:
        raw = (SPECS / entry["file"]).read_bytes()
        assert (
            hashlib.sha256(raw).hexdigest()
            == entry["sha256"]
            == PINNED_HASHES[entry["id"]]
        )
        assert entry["tier"] == "primary"
        assert entry["declared_version"] == json.loads(raw)["info"]["version"]
        assert entry["fetched_at"] == "2026-09-07T10:51:10Z"
        assert entry["strip_extensions"] == ["x-atlassian-narrative"]
    compile_product(SPECS, tmp_path)
    all_ids = []
    for doc, count in zip(IDS, (617, 105, 75)):
        value = json.loads((tmp_path / f"{doc}.index.json").read_bytes())
        assert len(value["operations"]) == count
        all_ids.extend(value["operations"])
        assert "x-atlassian-narrative" not in value
    assert len(all_ids) == len(set(all_ids)) == 797


@pytest.fixture(scope="module")
def built_product(tmp_path_factory):
    root = tmp_path_factory.mktemp("jira-build")
    for name in (
        "pyproject.toml",
        "hatch_build.py",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
    ):
        shutil.copyfile(ROOT / name, root / name)
    (root / "scripts").mkdir()
    shutil.copyfile(
        ROOT / "scripts/check_release_tag.py", root / "scripts/check_release_tag.py"
    )
    shutil.copytree(
        ROOT / "src",
        root / "src",
        ignore=shutil.ignore_patterns("__pycache__", "_generated"),
    )
    for kind in ("wheel", "editable", "sdist"):
        out = root / "dist" / kind
        out.mkdir(parents=True)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from hatchling.build import build_{kind}; print(build_{kind}({str(out)!r}))",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    return root


def test_wheel_ships_all_deterministic_indexes_and_stamp(built_product, tmp_path):
    compile_product(SPECS, tmp_path)
    wheel = next((built_product / "dist/wheel").glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        for name in ["catalog.json", *(f"{doc}.index.json" for doc in IDS)]:
            assert (
                archive.read(f"jira_as/_generated/{name}")
                == (tmp_path / name).read_bytes()
            )
        assert (
            "BUILD_STAMP = 'sha256-" in archive.read("jira_as/_build_stamp.py").decode()
        )
        assert all(
            f"jira_as/specs/jira-{doc}-swagger-v3.json" in archive.namelist()
            for doc in IDS
        )


def test_editable_backend_persists_loadable_indexes(built_product):
    with zipfile.ZipFile(
        next((built_product / "dist/editable").glob("*.whl"))
    ) as archive:
        pth = "\n".join(
            archive.read(name).decode()
            for name in archive.namelist()
            if name.endswith(".pth")
        )
    assert str(built_product / "src") in pth
    generated = built_product / "src/jira_as/_generated"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from as_engine.index import ProductIndexes; indexes=ProductIndexes({str(generated)!r}); assert sum(len(i.operations) for _,i in indexes.primary())==797",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_sdist_keeps_sources_hook_stamp_release_files_and_no_indexes(built_product):
    with tarfile.open(next((built_product / "dist/sdist").glob("*.tar.gz"))) as archive:
        names = archive.getnames()
    for suffix in (
        "/hatch_build.py",
        "/CHANGELOG.md",
        "/scripts/check_release_tag.py",
        "/src/jira_as/_build_stamp.py",
        "/specs/manifest.json",
    ):
        assert any(name.endswith(suffix) for name in names)
    assert not any("/_generated/" in name for name in names)
