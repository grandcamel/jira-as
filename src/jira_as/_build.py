"""Build identity helpers; also loaded directly by the dependency-free build hook."""

import hashlib
import re
import subprocess
from pathlib import Path


def source_stamp(root: Path) -> str:
    """Hash shipped Python sources and build configuration, independent of paths."""
    paths = [root / "pyproject.toml", root / "hatch_build.py"]
    paths.extend(sorted((root / "src" / "jira_as").rglob("*.py")))
    digest = hashlib.sha256()
    for path in paths:
        if path.name == "_build_stamp.py":
            continue
        name = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        for part in (name, content):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return "sha256-" + digest.hexdigest()


def checkout_identifier() -> str | None:
    """Only consult the checkout containing this source, never the caller's cwd."""
    module = Path(__file__).resolve()
    root = module.parents[2]
    if root / "src" / "jira_as" / "_build.py" != module:
        return None

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()

    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
            return None
        commit = git("rev-parse", "--short=12", "HEAD")
        if not re.fullmatch(r"[0-9a-f]{7,64}", commit):
            return None
        dirty = git(
            "status",
            "--porcelain",
            "--untracked-files=normal",
            "--",
            "src",
            "pyproject.toml",
            "hatch_build.py",
        )
        return f"git {commit}" + ("-dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def get_build_identifier() -> str:
    """Prefer a live source checkout; installed artifacts carry a frozen stamp."""
    checkout = checkout_identifier()
    if checkout:
        return checkout
    try:
        from ._build_stamp import BUILD_STAMP

        if isinstance(BUILD_STAMP, str) and re.fullmatch(
            r"sha256-[0-9a-f]{64}", BUILD_STAMP
        ):
            return f"build {BUILD_STAMP}"
    except ImportError:
        pass
    return "build unknown"
