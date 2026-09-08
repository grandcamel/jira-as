#!/usr/bin/env python3
"""Record the shared CLI invocation inventory on disposable SBX issues.

Host-only: jira-dev-host <lane>/jira-as --suite .venv/bin/python
scripts/record_cassettes.py --out tests/cassettes/new.json

The invocation sidecar is deliberately not a Player cassette. Setup and cleanup
use a separate, non-recording surface. Never replace a reviewed fixture here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jira_as.engine import create_surface  # noqa: E402
from tests.live.sbx_profile import SbxSession, sbx_scope  # noqa: E402
from tests.live.scenarios import CASE_ARGV, CASES, SETUP_CLEANUP_ARGV  # noqa: E402

# The exact common cases drive synthetic and future host recordings. The live
# export additionally includes setup, cleanup and survivors; gating those is
# conservative and keeps every potentially emitted argv reviewable.
RECORDER_ARGV = CASE_ARGV + SETUP_CLEANUP_ARGV


def sidecar_path(path: Path) -> Path:
    return path.with_suffix(".argv.json")


def portable_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Capture only CLI inputs and expected shapes, never response/config data."""
    result = []
    for case in cases:
        row: dict[str, Any] = {"id": case["id"], "steps": [], "files": {}}
        for step in case["steps"]:
            argv = list(step["argv"])
            for index, token in enumerate(argv):
                path = Path(case.get("directory", ".")) / token.removeprefix("@")
                if (
                    token.startswith("@")
                    or (index and argv[index - 1] == "--body-file")
                ) and path.is_file():
                    row["files"][path.name] = path.read_text(encoding="utf-8")
                    argv[index] = "@" + path.name
            row["steps"].append({**step, "argv": argv})
        result.append(row)
    return result


def invocation_digest(cases: list[dict[str, Any]]) -> str:
    data = json.dumps(cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode()).hexdigest()


def record_session(path: Path, session: SbxSession) -> dict[str, Any]:
    """One measured session, with cleanup even after setup or recording failure."""
    from tests.test_devhost_argv import _check_gate

    sidecar = sidecar_path(path)
    if path.exists() or sidecar.exists():
        raise ValueError("recording refuses an existing cassette or argv sidecar")
    if not path.parent.is_dir():
        raise ValueError("recording destination directory must already exist")
    # Fail before setup sends: templates contain only SBX identities. The
    # profile checks each materialized invocation again before its own send.
    for row in RECORDER_ARGV:
        _check_gate(row["argv"])
    failure = False
    try:
        prepared = [session.prepare(case) for case in CASES]
        for case in prepared:
            for step in case["steps"]:
                _check_gate(step["argv"])
        settings = {"JIRA_AS_TRANSPORT": "http", "JIRA_AS_RECORD": str(path)}
        with patch.dict(os.environ, settings):
            surface = create_surface()
            with session.use_surface(surface):
                for case in prepared:
                    session.activate(case)
                    for step in case["steps"]:
                        outcome = session.invoke(step["argv"])
                        if outcome.exit_code != step.get("exit", 0):
                            print(
                                f"Failed case {case['id']}: argv={json.dumps(step['argv'])} exit={outcome.exit_code}\n"
                                f"Captured output:\n{outcome.output}\n"
                                f"Captured stderr:\n{outcome.stderr}",
                                file=sys.stderr,
                            )
                            raise RuntimeError(
                                f"recording failed: {case['id']} exited {outcome.exit_code}"
                            )
        rows = portable_cases(prepared)
        payload = {
            "source": "jira-as CLI invocation inventory",
            "invocations_sha256": invocation_digest(rows),
            "cases": rows,
        }
        # The sidecar has no responses, credentials or transport configuration.
        # Avoid accidental output clobbering even if the sidecar appeared late.
        with sidecar.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return payload
    except BaseException as error:
        failure = True
        print(str(error), file=sys.stderr)
        raise
    finally:
        try:
            print(session.cleanup())
        except BaseException as error:
            if not failure:
                failure = True
                raise
            print(f"SBX cleanup also failed: {error}", file=sys.stderr)
        finally:
            if failure:
                print(
                    "Recording incomplete; retain cassette for private review and use the SBX cleanup ledger below.",
                    file=sys.stderr,
                )
                print(session.ledger(), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # Resolve relative paths from the product, even under the host wrapper's
    # private CWD. No credential/config values are printed or copied.
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        if os.environ.get("JIRA_AS_RECORD") or os.environ.get("JIRA_AS_CASSETTE"):
            raise ValueError(
                "recorder requires unset JIRA_AS_RECORD and JIRA_AS_CASSETTE"
            )
        if os.environ.get("JIRA_AS_TRANSPORT", "http") != "http":
            raise ValueError("host recorder requires http transport")
        with (
            sbx_scope(),
            tempfile.TemporaryDirectory(prefix="jas-cassette-") as scratch,
        ):
            session = SbxSession(transport="http", cache_dir=Path(scratch))
            payload = record_session(output, session)
        print(f"Recorded {output}; invocation sha256={payload['invocations_sha256']}")
        print(
            "Review checklist: inspect scrubbed bytes and argv sidecar; diff against synthetic fixture; replay offline with sockets and credentials disabled; only then replace a committed fixture."
        )
        return 0
    except (AssertionError, OSError, ValueError, RuntimeError) as error:
        print(f"recording failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
