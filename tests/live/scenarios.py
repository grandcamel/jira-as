"""Contract-derived, materializable SBX scenarios shared by live and replay runs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).parents[2] / "src/jira_as/compat/contract.json"
COMMENT_TEXT = "A markdown comment: **bold** and a list"


def _contract_cases() -> list[dict[str, Any]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for operation in contract["operations"]:
        for number, variant in enumerate(operation["variants"]):
            output = variant["output"]
            tokens = list(variant["argv"])
            steps = (
                [
                    {
                        "argv": tokens[: tokens.index("=>")],
                        "output": output["first"],
                        "exit": 0,
                    },
                    {
                        "argv": tokens[tokens.index("=>") + 1 :],
                        "output": output["second"],
                        "exit": 0,
                    },
                ]
                if output["kind"] == "pair"
                else [{"argv": tokens, "output": output, "exit": 0}]
            )
            cases.append(
                {
                    "id": f"contract:{operation['host_op']}:{number}",
                    "host_op": operation["host_op"],
                    "variant": number,
                    "steps": steps,
                    "setup": {
                        "issue": operation["host_op"] != "create",
                        "comment": variant["capture"] == "comments-after",
                        "other": operation["host_op"] in {"link", "unlink"}
                        or variant["capture"] == "get-links-after",
                        "link": operation["host_op"] == "unlink"
                        or variant["capture"] == "get-links-after",
                    },
                }
            )
            preflight = variant.get("preflight")
            if preflight:
                cases.append(
                    {
                        "id": f"preflight:{operation['host_op']}:{number}",
                        "host_op": operation["host_op"],
                        "variant": number,
                        "steps": [
                            {
                                "argv": list(preflight["argv"]),
                                "output": preflight["output"],
                                "exit": 0,
                            }
                        ],
                        "setup": {
                            "issue": False,
                            "comment": False,
                            "other": False,
                            "link": False,
                        },
                    }
                )
    return cases


_GENERIC_OUTPUT = {"kind": "json", "required": {}}
GENERIC_CASES: list[dict[str, Any]] = [
    {
        "id": "generic:getIssue",
        "host_op": "generic",
        "variant": "getIssue",
        "steps": [
            {
                "argv": [
                    "api",
                    "call",
                    "getIssue",
                    "--issueIdOrKey",
                    "SBX-1",
                    "--format",
                    "json",
                ],
                "output": _GENERIC_OUTPUT,
                "exit": 0,
            }
        ],
        "setup": {"issue": True},
    },
    {
        "id": "generic:createIssue",
        "host_op": "generic",
        "variant": "createIssue",
        "steps": [
            {
                "argv": [
                    "api",
                    "call",
                    "createIssue",
                    "--project",
                    "SBX",
                    "--body",
                    "@create.json",
                    "--format",
                    "json",
                ],
                "output": _GENERIC_OUTPUT,
                "exit": 0,
            }
        ],
        "setup": {"issue": False},
    },
    {
        "id": "generic:editIssue",
        "host_op": "generic",
        "variant": "editIssue",
        "steps": [
            {
                "argv": [
                    "api",
                    "call",
                    "editIssue",
                    "--issueIdOrKey",
                    "SBX-1",
                    "--body",
                    "@edit.json",
                    "--format",
                    "json",
                ],
                "output": {"kind": "none"},
                "exit": 0,
            }
        ],
        "setup": {"issue": True},
    },
    {
        "id": "generic:searchAndReconsileIssuesUsingJql",
        "host_op": "generic",
        "variant": "searchAndReconsileIssuesUsingJql",
        "steps": [
            {
                "argv": [
                    "api",
                    "call",
                    "searchAndReconsileIssuesUsingJql",
                    "--jql",
                    "project = SBX",
                    "--format",
                    "json",
                ],
                "output": _GENERIC_OUTPUT,
                "exit": 0,
            }
        ],
        "setup": {"issue": True},
    },
    {
        "id": "generic:owned-deleted-key404",
        "host_op": "generic",
        "variant": "owned-deleted-key404",
        "steps": [
            {
                "argv": [
                    "api",
                    "call",
                    "getIssue",
                    "--issueIdOrKey",
                    "SBX-404",
                    "--format",
                    "json",
                ],
                "output": {"kind": "error"},
                "exit": 5,
            }
        ],
        "setup": {"deleted": True},
    },
    {
        "id": "generic:api-search",
        "host_op": "generic",
        "variant": "api-search",
        "steps": [
            {
                "argv": ["api", "search", "issue", "--format", "json"],
                "output": {"kind": "array"},
                "exit": 0,
            }
        ],
        "setup": {},
    },
    {
        "id": "generic:api-describe",
        "host_op": "generic",
        "variant": "api-describe",
        "steps": [
            {
                "argv": ["api", "describe", "getIssue", "--format", "json"],
                "output": _GENERIC_OUTPUT,
                "exit": 0,
            }
        ],
        "setup": {},
    },
    {
        "id": "generic:api-topics",
        "host_op": "generic",
        "variant": "api-topics",
        "steps": [
            {
                "argv": ["api", "topics", "--format", "json"],
                "output": {"kind": "array"},
                "exit": 0,
            }
        ],
        "setup": {},
    },
]


for case in GENERIC_CASES:
    required = {
        "getIssue": {"key": "string", "fields": "object"},
        "createIssue": {"key": "string", "id": "string"},
        "searchAndReconsileIssuesUsingJql": {"issues": "array"},
        "api-describe": {"operationId": "string"},
    }.get(case["variant"])
    if required:
        case["steps"][0]["output"] = {"kind": "json", "required": required}

CASES = _contract_cases() + GENERIC_CASES


def materialize(
    case: dict[str, Any], key: str, other_key: str, prefix: str, directory: Path
) -> dict[str, Any]:
    """Return a disposable SBX invocation and write only its private bodies.

    ``prefix`` is the issue-summary prefix and the final label.  Keeping it
    separate from labels in the source contract preserves captured text while
    ensuring every mutable host action stays recoverable during cleanup.
    """
    directory.mkdir(parents=True, exist_ok=True)
    value = copy.deepcopy(case)
    files: dict[str, Path] = {}
    comment = directory / "comment.md"
    comment.write_text(COMMENT_TEXT, encoding="utf-8")
    files["comment.md"] = comment
    create = directory / "create.json"
    create.write_text(
        json.dumps(
            {
                "fields": {
                    "project": {"key": "SBX"},
                    "issuetype": {"name": "Task"},
                    "summary": f"{prefix} generic create",
                    "labels": [prefix],
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    files["create.json"] = create
    edit = directory / "edit.json"
    edit.write_text(
        json.dumps(
            {"fields": {"summary": f"{prefix} generic edit", "labels": [prefix]}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    files["edit.json"] = edit
    substitutions = {"K": key, "SBX-1": key, "SBX-17": other_key, "SBX-404": key}
    for step in value["steps"]:
        argv = [substitutions.get(item, item) for item in step["argv"]]
        if "--body-file" in argv:
            position = argv.index("--body-file") + 1
            if argv[position] == "@comment.md":
                argv[position] = "comment.md"
        if argv[:2] == ["search", "query"]:
            argv[2] = f'project = SBX AND labels = "{prefix}" ORDER BY key ASC'
        if "--jql" in argv:
            argv[argv.index("--jql") + 1] = f'project = SBX AND labels = "{prefix}"'
        if argv[:3] == ["issue", "create", "--project"]:
            argv.extend(["--labels", prefix])
            for index, item in enumerate(argv):
                if item == "--summary":
                    argv[index + 1] = f"{prefix} {argv[index + 1]}"
                elif item == "--description":
                    argv[index + 1] = f"{prefix} {argv[index + 1]}"
        if argv[:3] == ["issue", "update", other_key] or argv[:3] == [
            "issue",
            "update",
            key,
        ]:
            for index, item in enumerate(argv):
                if item in {"--summary", "--description"}:
                    argv[index + 1] = f"{prefix} {argv[index + 1]}"
                if item == "--labels":
                    argv[index + 1] = f"{argv[index + 1]},{prefix}"
        if argv[:2] == ["time", "log"]:
            argv.extend(["--started", "2026-09-01T00:00:00Z"])
        step["argv"] = argv
    value["files"] = files
    value["directory"] = directory
    return value


CASE_ARGV = [
    {
        "id": case["id"],
        "argv": step["argv"],
        "files": {
            "comment.md": COMMENT_TEXT,
            "create.json": {"fields": {"project": {"key": "SBX"}}},
            "edit.json": {"fields": {}},
        },
    }
    for case in CASES
    for step in case["steps"]
]

SETUP_CLEANUP_ARGV = [
    {
        "id": "setup:create",
        "argv": [
            "api",
            "call",
            "createIssue",
            "--project",
            "SBX",
            "--body",
            "@setup.json",
            "--format",
            "json",
        ],
        "files": {"setup.json": {"fields": {"project": {"key": "SBX"}}}},
    },
    {
        "id": "setup:comment",
        "argv": [
            "collaborate",
            "comment",
            "add",
            "SBX-1",
            "--body",
            "seed comment",
            "--format",
            "markdown",
        ],
        "files": {},
    },
    {
        "id": "setup:link",
        "argv": ["relationships", "link", "SBX-1", "--type", "Blocks", "--to", "SBX-2"],
        "files": {},
    },
    {
        "id": "cleanup:delete",
        "argv": [
            "api",
            "call",
            "deleteIssue",
            "--issueIdOrKey",
            "SBX-1",
            "--confirm",
            "--format",
            "json",
        ],
        "files": {},
    },
    {
        "id": "cleanup:get404",
        "argv": [
            "api",
            "call",
            "getIssue",
            "--issueIdOrKey",
            "SBX-1",
            "--format",
            "json",
        ],
        "files": {},
    },
    {
        "id": "cleanup:label-search",
        "argv": [
            "api",
            "call",
            "searchAndReconsileIssuesUsingJql",
            "--jql",
            'project = SBX AND labels = "jas-cassette-xrun"',
            "--all",
            "--format",
            "json",
        ],
        "files": {},
    },
]

_SURVIVOR_ARGV = [
    {
        "id": "risk:preview",
        "argv": [
            "api",
            "call",
            "deleteIssue",
            "--issueIdOrKey",
            "SBX-1",
            "--format",
            "json",
        ],
        "files": {},
    },
    {
        "id": "risk:confirm",
        "argv": [
            "api",
            "call",
            "deleteIssue",
            "--issueIdOrKey",
            "SBX-1",
            "--confirm",
            "--format",
            "json",
        ],
        "files": {},
    },
    {
        "id": "survivor:bulk-update",
        "argv": [
            "search",
            "bulk-update",
            'project = SBX AND labels = "jas-cassette-xrun"',
            "--add-labels",
            "dry-run-probe",
            "--dry-run",
            "--output",
            "json",
        ],
        "files": {},
    },
    {"id": "survivor:fields-warm", "argv": ["fields", "cache", "warm"], "files": {}},
]

LIVE_ARGV = CASE_ARGV + SETUP_CLEANUP_ARGV + _SURVIVOR_ARGV
