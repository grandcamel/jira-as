"""Release identity contracts, offline and independent of installed metadata."""

import importlib.metadata
import re
import runpy
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
from click.testing import CliRunner

from jira_as import __version__, _build
from jira_as.cli.main import cli, get_version

ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / "scripts/check_release_tag.py"))["check_release_tag"]


@pytest.fixture
def source_tree(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(
        ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    for name in ("pyproject.toml", "hatch_build.py", "CHANGELOG.md"):
        shutil.copyfile(ROOT / name, root / name)
    return root


def test_version_uses_package_even_with_stale_distribution(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.0.0")
    assert get_version().startswith(__version__ + " (")
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith(f"jira-as, version {__version__} (")
    # doctor's check_command extracts the first dotted number.
    assert re.search(r"[0-9]+(?:\.[0-9]+){1,3}", result.output)[0] == __version__


def test_real_worktree_identity_does_not_follow_cwd(tmp_path, monkeypatch):
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(
            "not a git checkout (e.g. a git archive export); "
            "worktree identity is asserted only in a real worktree"
        )
    monkeypatch.chdir(tmp_path)
    assert _build.checkout_identifier().startswith(f"git {commit}")


def test_real_worktree_identity_skips_without_git(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(subprocess, "check_output", fail)
    with pytest.raises(pytest.skip.Exception) as skipped:
        test_real_worktree_identity_does_not_follow_cwd(tmp_path, monkeypatch)
    assert str(skipped.value) == (
        "not a git checkout (e.g. a git archive export); "
        "worktree identity is asserted only in a real worktree"
    )


@pytest.mark.parametrize("dirty", ["", " M src/jira_as/__init__.py"])
def test_checkout_git_file_supported(monkeypatch, dirty):
    calls = []

    def git(args, **kwargs):
        calls.append(args)
        if "--show-toplevel" in args:
            return str(ROOT)
        if "HEAD" in args:
            return "0123456789ab"
        return dirty

    monkeypatch.setattr(_build.subprocess, "check_output", git)
    assert _build.checkout_identifier() == "git 0123456789ab" + (
        "-dirty" if dirty else ""
    )
    assert all(args[:3] == ["git", "-C", str(ROOT)] for args in calls)


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("git", 2),
        subprocess.CalledProcessError(128, "git"),
    ],
)
def test_git_unavailable_falls_back(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(_build.subprocess, "check_output", fail)
    monkeypatch.setitem(sys.modules, "jira_as._build_stamp", None)
    assert _build.get_build_identifier() == "build unknown"


def test_parent_repository_is_not_source_identity(source_tree, monkeypatch):
    monkeypatch.setattr(_build, "__file__", str(source_tree / "src/jira_as/_build.py"))
    monkeypatch.setattr(
        _build.subprocess, "check_output", lambda *a, **kw: str(source_tree.parent)
    )
    assert _build.checkout_identifier() is None


@pytest.mark.parametrize("stamp", [None, "", "sha256-not-a-digest", 123])
def test_invalid_stamp_is_explicit(monkeypatch, stamp):
    monkeypatch.setattr(_build, "checkout_identifier", lambda: None)
    module = types.ModuleType("jira_as._build_stamp")
    module.BUILD_STAMP = stamp
    monkeypatch.setitem(sys.modules, module.__name__, module)
    assert _build.get_build_identifier() == "build unknown"


def test_stamp_changes_with_source_but_not_location_or_generated_stamp(
    source_tree, tmp_path
):
    stamp = _build.source_stamp(source_tree)
    copy = tmp_path / "copy"
    shutil.copytree(source_tree, copy)
    (copy / "src/jira_as/_build_stamp.py").write_text("BUILD_STAMP = 'old'\n")
    assert _build.source_stamp(copy) == stamp
    with (copy / "src/jira_as/__init__.py").open("a") as file:
        file.write("\n# changed\n")
    assert _build.source_stamp(copy) != stamp


@pytest.mark.parametrize("target", ["wheel", "sdist"])
def test_hook_transports_stamp_without_modifying_source(
    source_tree, tmp_path, monkeypatch, target
):
    # Exercise our hook without requiring the build backend in runtime/test deps.
    interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")
    interface.BuildHookInterface = object
    monkeypatch.setitem(sys.modules, interface.__name__, interface)
    hook_class = runpy.run_path(str(ROOT / "hatch_build.py"))["CustomBuildHook"]
    hook = hook_class()
    hook.root = str(source_tree)
    hook.target_name = target
    data = {}
    hook.initialize("standard", data)
    [(filename, destination)] = data["force_include"].items()
    prefix = "src/" if target == "sdist" else ""
    assert destination == prefix + "jira_as/_build_stamp.py"
    stamp = runpy.run_path(filename)["BUILD_STAMP"]
    assert stamp == _build.source_stamp(source_tree)
    assert not (source_tree / "src/jira_as/_build_stamp.py").exists()
    # Transport package + generated stamp into a directory with no git metadata.
    installed = tmp_path / "installed"
    shutil.copytree(source_tree / "src/jira_as", installed / "jira_as")
    shutil.copyfile(filename, installed / "jira_as/_build_stamp.py")
    hook.finalize("standard", data, "unused")
    assert not Path(filename).exists()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from jira_as.cli.main import cli; cli(['--version'])",
            str(installed),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"jira-as, version {__version__} (build {stamp})\n"


def test_release_tag_agreement():
    CHECK(f"v{__version__}", ROOT)


@pytest.mark.parametrize("tag", ["1.2.0", "v1.1.3", "v1.2.0-extra", "", "v1.2.0\n"])
def test_wrong_tag_rejected(tag):
    with pytest.raises(ValueError, match="tag must be"):
        CHECK(tag, ROOT)


@pytest.mark.parametrize(
    "filename, old, new, reason",
    [
        (
            "pyproject.toml",
            f'version = "{__version__}"',
            'version = "9.9.9"',
            "__version__",
        ),
        (
            "src/jira_as/__init__.py",
            f'__version__ = "{__version__}"',
            '__version__ = "9.9.9"',
            "__version__",
        ),
        ("CHANGELOG.md", f"## [{__version__}]", "## [9.9.9]", "top CHANGELOG"),
    ],
)
def test_release_file_disagreement_rejected(source_tree, filename, old, new, reason):
    path = source_tree / filename
    path.write_text(path.read_text().replace(old, new, 1))
    with pytest.raises(ValueError, match=reason):
        CHECK(f"v{__version__}", source_tree)


def test_top_release_is_used_not_historical_duplicate(source_tree):
    path = source_tree / "CHANGELOG.md"
    path.write_text("## [9.9.9]\n\n" + path.read_text())
    with pytest.raises(ValueError, match="top CHANGELOG"):
        CHECK(f"v{__version__}", source_tree)


@pytest.mark.parametrize(
    "args, code", [([f"v{__version__}"], 0), (["v0.0.0"], 1), ([], 1)]
)
def test_release_check_public_cli(args, code, tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_release_tag.py"), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == code
    assert len((result.stdout + result.stderr).splitlines()) == 1


def test_no_metadata_directory_cli_never_crashes(source_tree):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from jira_as.cli.main import cli; cli(['--version'])",
            str(source_tree / "src"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"jira-as, version {__version__} (build unknown)\n"
