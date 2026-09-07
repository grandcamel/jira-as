"""Embed a deterministic source stamp without modifying the source checkout."""

import runpy
from pathlib import Path
from tempfile import TemporaryDirectory

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        helpers = runpy.run_path(str(root / "src" / "jira_as" / "_build.py"))
        stamp = helpers["source_stamp"](root)
        self._stamp_dir = TemporaryDirectory(prefix="jira-as-build-")
        stamp_file = Path(self._stamp_dir.name) / "_build_stamp.py"
        stamp_file.write_text(
            f'"""Generated source-content identity; do not edit."""\nBUILD_STAMP = {stamp!r}\n',
            encoding="utf-8",
        )
        destination = "jira_as/_build_stamp.py"
        if self.target_name == "sdist":
            destination = "src/" + destination
        build_data.setdefault("force_include", {})[str(stamp_file)] = destination

        if self.target_name == "wheel":
            from as_engine.build import compile_product

            package = root / "src" / "jira_as"
            generated = package / "_generated"
            catalog = compile_product(package / "specs", generated)
            names = ["catalog.json", *(entry["file"] for entry in catalog["documents"])]
            for name in sorted(names):
                path = generated / name
                build_data["force_include"][str(path)] = f"jira_as/_generated/{name}"

    def finalize(self, version, build_data, artifact_path):
        self._stamp_dir.cleanup()
