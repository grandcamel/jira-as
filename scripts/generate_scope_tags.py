#!/usr/bin/env python3
"""Generate conservative Jira project-scope tags from pinned Base Documents.

Only explicit, public identity forms are generated.  Ambiguous request bodies
are printed for the separate hand overlay; regeneration never edits that
overlay or a Base Document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

METHODS = ("get", "put", "post", "delete", "patch", "options", "head", "trace")
ORIGIN = "JAS-46; pinned Jira Base Documents"
EVIDENCE_DATE = "2026-09-07"
PROJECT_PARAMETERS = {
    "projectIdOrKey",
    "projectKey",
    "projectId",
    "projectKeyOrId",
    "projectKeys",
    "projectIds",
}
ISSUE_PARAMETERS = {
    "issueIdOrKey",
    "issueKey",
    "issueKeys",
    "issueIdsOrKeys",
    "epicIdOrKey",
}
NUMERIC_ROUTE_PARAMETERS = {"boardId", "sprintId", "serviceDeskId", "organizationId"}
FREE_MAP_OPERATIONS = {"createIssue", "editIssue", "doTransition", "createIssues"}
SITE_OPERATION_IDS = {
    "createDashboard",
    "bulkEditDashboards",
    "updateDashboard",
    "copyDashboard",
    "createFilter",
    "updateFilter",
}


def resolve(value, document, seen=()):
    """Resolve local references and merge the object shape used by allOf."""
    if not isinstance(value, dict):
        return {}
    if "$ref" in value:
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            raise ValueError(f"unsupported or cyclic local reference: {ref!r}")
        node = document
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return resolve(node, document, (*seen, ref))
    if "allOf" in value:
        merged = {**value, "properties": {}}
        for child in value["allOf"]:
            item = resolve(child, document, seen)
            merged["properties"].update(item.get("properties", {}))
            if "type" in item:
                merged["type"] = item["type"]
        merged["properties"].update(value.get("properties", {}))
        return merged
    return value


def pointer(name):
    return "/" + name.replace("~", "~0").replace("/", "~1")


def parameters(item, operation, document):
    result = {}
    for raw in [*item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = resolve(raw, document)
        if "in" in parameter and "name" in parameter:
            result[(parameter["in"], parameter["name"])] = parameter
    return result


def body_schema(operation, document):
    body = resolve(operation.get("requestBody", {}), document)
    return resolve(
        body.get("content", {}).get("application/json", {}).get("schema", {}), document
    )


def effective_operation_ids(spec_dir, entry):
    corrected = {}
    overlay = spec_dir / f"{entry['id']}.identity.overlay.json"
    if not overlay.exists():
        return corrected
    for action in json.loads(overlay.read_text())["actions"]:
        operation_id = action.get("update", {}).get("operationId")
        if operation_id:
            corrected[action["target"]] = operation_id
    return corrected


def schema_signals(schema, document, prefix="", seen=()):
    """Return explicit identity pointers and suspicious identity-like fields."""
    # The vendor documents contain recursive value schemas.  Project identity
    # lives near the request root; do not chase an arbitrary recursive graph.
    if prefix.count("/") > 12:
        return [], []
    schema = resolve(schema, document, seen)
    if not schema:
        return [], []
    explicit, suspicious = [], []
    properties = schema.get("properties", {})
    for name, raw in properties.items():
        path = prefix + pointer(name)
        lowered = name.lower()
        value = resolve(raw, document, seen)
        if name in {"projectId", "projectIds", "projectKey"}:
            if value.get("type") == "array":
                suspicious.append(path)
            else:
                explicit.append(path)
        elif name in ISSUE_PARAMETERS or name in {"issueId", "issueIds"}:
            suspicious.append(path)
        elif name == "project":
            # Component/version request schemas use a direct project string;
            # issue free-maps and project objects are not safe to guess.
            if value.get("type") == "string":
                explicit.append(path)
            elif prefix.endswith("/fields"):
                suspicious.append(path)
            else:
                child_paths, child_suspicious = schema_signals(
                    value, document, path, seen
                )
                key_or_id = [
                    p for p in child_paths if p in {path + "/key", path + "/id"}
                ]
                if key_or_id:
                    explicit.extend(key_or_id)
                else:
                    suspicious.append(path)
                suspicious.extend(child_suspicious)
        elif lowered.startswith("project") or lowered.endswith("project"):
            suspicious.append(path)
        if value.get("type") == "object" or "allOf" in value or "$ref" in value:
            child_paths, child_suspicious = schema_signals(value, document, path, seen)
            explicit.extend(child_paths)
            suspicious.extend(child_suspicious)
        elif value.get("type") == "array":
            items = resolve(value.get("items", {}), document, seen)
            if (
                items.get("type") == "object"
                or "properties" in items
                or "$ref" in items
            ):
                child_paths, child_suspicious = schema_signals(
                    items, document, path, seen
                )
                if child_paths or child_suspicious:
                    suspicious.append(path)
    if schema.get("additionalProperties") and prefix.endswith("/fields"):
        suspicious.append(prefix)
    return sorted(set(explicit)), sorted(set(suspicious))


def scope_tag(kind, **details):
    return {"in": kind, **details}


def classify(item, operation, document):
    params = parameters(item, operation, document)
    names = {name: location for location, name in params}
    operation_id = operation.get("operationId", "<unnamed>")
    path_names = {name for location, name in params if location == "path"}
    query_names = {name for location, name in params if location == "query"}

    if operation_id in FREE_MAP_OPERATIONS:
        return (
            None,
            "free-map issue fields or competing identity families require hand review",
        )

    # These ids identify a board/sprint/desk/org, never a Jira project.  A
    # later resolver may turn them into scoped calls; this classifier must not.
    if NUMERIC_ROUTE_PARAMETERS & path_names and operation_id != "getAllBoards":
        return scope_tag("site"), None

    # Saved filters and dashboards are site resources even though their
    # permission payloads may mention projects.
    if operation_id in SITE_OPERATION_IDS:
        return scope_tag("site"), None

    issue = sorted(ISSUE_PARAMETERS & set(names))
    required_path_issue = [
        name
        for name in issue
        if names[name] == "path" and params[(names[name], name)].get("required", False)
    ]
    project = sorted(PROJECT_PARAMETERS & set(names))
    if (
        len(issue) > 1
        or len(project) > 1
        or (issue and project and not required_path_issue)
    ):
        return None, "competing parameter identity families require hand review"
    if issue:
        note = None
        if required_path_issue and "jql" in query_names:
            note = "required issue identity takes precedence over optional JQL"
        return scope_tag(
            "key",
            name=required_path_issue[0] if required_path_issue else issue[0],
            separator="-",
        ), note

    if project:
        name = project[0]
        return scope_tag("path" if names[name] == "path" else "query", name=name), None

    if "jql" in query_names:
        return scope_tag("query", name="jql", clause="project", conjunction=True), None

    body = body_schema(operation, document)
    if body:
        paths, suspicious = schema_signals(body, document)
        if suspicious:
            return None, "unrecognized body project identity alias(es): " + ", ".join(
                suspicious
            )
        if paths:
            details = {"path": paths[0]} if len(paths) == 1 else {"paths": paths}
            return scope_tag("body", **details), None
        # JQL bodies are explicit even when their generic body schema has no
        # project field.
        if "jql" in body.get("properties", {}):
            return scope_tag(
                "body", path="/jql", clause="project", conjunction=True
            ), None
    return scope_tag("site"), None


def action_for(document_id, path, method, operation_id, tag, evidence_url):
    return {
        "target": f"$.paths[{json.dumps(path)}].{method}",
        "update": {"x-as-scope": tag},
        "description": f"Declare {tag['in']} project scope for {operation_id}.",
        "x-as-reason": "Pinned Base Document identity classification; hand decisions layer separately.",
        "x-as-evidence": {"url": evidence_url, "date": EVIDENCE_DATE},
        "x-as-origin": ORIGIN,
        "x-as-test": f"scope_{document_id}_{operation_id}",
    }


def generate(spec_dir):
    spec_dir = Path(spec_dir).resolve()
    manifest = json.loads((spec_dir / "manifest.json").read_text())
    pending = []
    for entry in manifest["documents"]:
        document_id = entry["id"]
        if document_id not in {"platform", "software", "servicedesk"}:
            raise ValueError(f"unsupported Jira document id: {document_id}")
        source = (spec_dir / entry["file"]).resolve()
        if not source.is_relative_to(spec_dir):
            raise ValueError("Base Document escapes spec directory")
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"{source.name}: sha256 mismatch")
        document = json.loads(raw)
        corrected = effective_operation_ids(spec_dir, entry)
        actions, review, notes = [], [], []
        for path, item in sorted(document["paths"].items()):
            for method in METHODS:
                operation = item.get(method)
                if not isinstance(operation, dict):
                    continue
                target = f"$.paths[{json.dumps(path)}].{method}"
                operation_id = corrected.get(
                    target, operation.get("operationId", "<unnamed>")
                )
                tag, finding = classify(item, operation, document)
                if tag is None:
                    review.append(f"{operation_id}: {finding}")
                else:
                    actions.append(
                        action_for(
                            document_id, path, method, operation_id, tag, entry["url"]
                        )
                    )
                    if finding:
                        notes.append(f"OPTIONAL CONFLICT: {operation_id}: {finding}")
        overlay = {
            "overlay": "1.0.0",
            "info": {
                "title": f"Jira {document_id} generated scope (do not edit)",
                "version": "1.0.0",
            },
            "actions": actions,
        }
        output = spec_dir / f"{document_id}.scope.overlay.json"
        if output.is_symlink():
            raise ValueError(f"refusing symlink output: {output.name}")
        pending.append(
            (
                output,
                json.dumps(overlay, indent=2, sort_keys=True) + "\n",
                review,
                notes,
            )
        )
    for output, content, review, notes in pending:
        output.write_text(content, encoding="utf-8")
        print(f"{output.name}: {len(json.loads(content)['actions'])} generated entries")
        for decision in review:
            print(f"HAND REVIEW: {decision}")
        for note in notes:
            print(note)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src/jira_as/specs",
    )
    generate(parser.parse_args().spec_dir)


if __name__ == "__main__":
    main()
