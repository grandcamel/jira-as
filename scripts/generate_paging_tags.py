#!/usr/bin/env python3
"""Generate conservative Jira paging tags from the pinned Base Documents.

The generated overlay is deliberately limited to schemas whose request and
response paging vocabulary is structurally explicit.  Bespoke and unfamiliar
signals are reported for the hand overlay; regeneration never changes it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

METHODS = ("get", "put", "post", "delete", "patch", "options", "head", "trace")
ORIGIN = "JAS-45; research/atlassian-paging-styles-2026-09.md"
EVIDENCE_DATE = "2026-09-07"
SIGNALS = {
    "after",
    "cursor",
    "isLast",
    "isLastPage",
    "limit",
    "maxResults",
    "next",
    "nextPageToken",
    "offset",
    "start",
    "startAt",
    "total",
}
ONE_SHOT = {
    "getCommentsByIds",
    "getChangeLogsByIds",
    "addRequestParticipants",
    "removeRequestParticipants",
    "findGroups",
    "findUsersForPicker",
}
ONE_SHOT_REASONS = {
    "getCommentsByIds": "The body supplies explicit comment IDs; response envelope fields do not declare a continuation input.",
    "getChangeLogsByIds": "The body supplies explicit changelog IDs; response envelope fields do not declare a continuation input.",
    "addRequestParticipants": "Participant mutation response is a one-shot result; it has no pagination request input.",
    "removeRequestParticipants": "Participant mutation response is a one-shot result; it has no pagination request input.",
    "findGroups": "Group picker accepts a result cap only, with no offset or continuation input.",
    "findUsersForPicker": "User picker accepts a result cap only, with no offset or continuation input.",
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
        param = resolve(raw, document)
        if "in" in param and "name" in param:
            result[(param["in"], param["name"])] = param
    return result


def body_schema(operation, document):
    body = resolve(operation.get("requestBody", {}), document)
    return resolve(
        body.get("content", {}).get("application/json", {}).get("schema", {}), document
    )


def response_schema(operation, document):
    response = resolve(operation.get("responses", {}).get("200", {}), document)
    return resolve(
        response.get("content", {}).get("application/json", {}).get("schema", {}),
        document,
    )


def collection_path(schema, document):
    schema = resolve(schema, document)
    if schema.get("type") == "array":
        return ""
    arrays = [
        name
        for name, value in schema.get("properties", {}).items()
        if resolve(value, document).get("type") == "array"
        and not resolve(value, document).get("writeOnly")
    ]
    props = schema.get("properties", {})
    links = resolve(props.get("_links", {}), document).get("properties", {})
    # A lone nested array in an otherwise rich resource is not a collection
    # response (for example, issue fields).  This is the pinned research
    # heuristic: accept wrappers with paging signals, a next link, or a bare
    # one/two-property list envelope.
    if not (SIGNALS & set(props) or "next" in links or len(props) <= 2):
        return None
    # Jira's search replies carry ancillary warning arrays and JSM carries
    # `_expands`; neither is the page collection.  The stable names below are
    # the collection fields used by the three pinned Jira documents.
    for name in ("issues", "values", "results", "records", "issueChangeLogs"):
        if name in arrays:
            return pointer(name)
    arrays = [
        name
        for name in arrays
        if name not in {"_expands", "warnings", "warningMessages"}
    ]
    return pointer(arrays[0]) if len(arrays) == 1 else None


def request_target(name, query, body, document):
    if name in query:
        return {"in": "query", "name": name}
    if name in body.get("properties", {}):
        return {"in": "body", "path": pointer(name)}
    return None


def classify(item, operation, document):
    op_id = operation.get("operationId", "<unnamed>")
    if op_id in {"getAuditRecords", "getFailedWebhooks"}:
        return None, "bespoke Jira paging is owned by the hand override"
    response = response_schema(operation, document)
    props = response.get("properties", {})
    items_path = collection_path(response, document)
    if items_path is None:
        if SIGNALS & set(props):
            return (
                None,
                "multiple or indeterminate collection arrays require hand review",
            )
        return None, None
    query = {
        name
        for location, name in parameters(item, operation, document)
        if location == "query"
    }
    body = body_schema(operation, document)
    if op_id in ONE_SHOT:
        return {"style": "none", "request": {}, "itemsPath": items_path}, None

    # Continuation tokens take precedence over isLast: all eleven named Jira
    # operations use this contract, including the two POST body variants.
    if "nextPageToken" in props:
        token = request_target("nextPageToken", query, body, document)
        if token is None:
            return None, "nextPageToken response has no declared request target"
        tag = {
            "style": "nextPageToken",
            "request": {"token": token},
            "itemsPath": items_path,
            "next": {"kind": "token", "path": "/nextPageToken"},
        }
        limit = request_target("maxResults", query, body, document)
        if limit is not None:
            tag["request"]["limit"] = limit
        if "isLast" in props:
            tag["response"] = {"isLastPath": "/isLast"}
        return tag, None

    offset = request_target("startAt", query, body, document)
    limit = request_target("maxResults", query, body, document)
    if offset is not None and limit is not None and ({"total", "isLast"} & set(props)):
        response = {}
        if "total" in props:
            response["totalPath"] = "/total"
        elif "isLast" in props:
            response["isLastPath"] = "/isLast"
        return {
            "style": "offset/limit",
            "request": {
                "offset": offset,
                "limit": limit,
            },
            "itemsPath": items_path,
            "response": response,
        }, None

    if (
        op_id == "findUserKeysByQuery"
        and {"startAt", "maxResult"} <= query
        and "total" in props
    ):
        return {
            "style": "offset/limit",
            "request": {
                "offset": {"in": "query", "name": "startAt"},
                "limit": {"in": "query", "name": "maxResult"},
            },
            "itemsPath": items_path,
            "response": {"totalPath": "/total"},
        }, None

    if {"start", "limit"} <= query and "isLastPage" in props:
        return {
            "style": "offset/limit",
            "request": {
                "offset": {"in": "query", "name": "start"},
                "limit": {"in": "query", "name": "limit"},
            },
            "itemsPath": items_path,
            "response": {"isLastPath": "/isLastPage"},
        }, None

    links = resolve(props.get("_links", {}), document).get("properties", {})
    if "cursor" in query and (
        "next" in props or "next" in links or "nextPageCursor" in props
    ):
        tag = {
            "style": "cursor",
            "request": {"token": {"in": "query", "name": "cursor"}},
            "itemsPath": items_path,
            "next": {
                "kind": "token" if "nextPageCursor" in props else "link",
                "path": "/nextPageCursor"
                if "nextPageCursor" in props
                else "/next"
                if "next" in props
                else "/_links/next",
            },
        }
        if "maxResults" in query:
            tag["request"]["limit"] = {"in": "query", "name": "maxResults"}
        return tag, None

    if SIGNALS & (set(props) | query | set(body.get("properties", {}))):
        return None, "unrecognized paging vocabulary requires hand review"
    return {"style": "none", "request": {}, "itemsPath": items_path}, None


def effective_operation_ids(spec_dir, entry):
    """Read identity corrections so generated test ids name compiled operations."""
    corrected = {}
    overlay = spec_dir / f"{entry['id']}.identity.overlay.json"
    if not overlay.exists():
        return corrected
    for action in json.loads(overlay.read_text())["actions"]:
        op_id = action.get("update", {}).get("operationId")
        if op_id:
            corrected[action["target"]] = op_id
    return corrected


def action_for(document_id, path, method, operation_id, tag, evidence_url):
    return {
        "target": f"$.paths[{json.dumps(path)}].{method}",
        "update": {"x-as-paging": tag},
        "description": f"Declare {tag['style']} paging for {operation_id}.",
        "x-as-reason": ONE_SHOT_REASONS.get(
            operation_id,
            "Pinned Base Document request and response schema classification; hand decisions layer separately.",
        ),
        "x-as-evidence": {"url": evidence_url, "date": EVIDENCE_DATE},
        "x-as-origin": ORIGIN,
        "x-as-test": f"paging_{document_id}_{operation_id}",
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
        actions, review = [], []
        for path, item in sorted(document["paths"].items()):
            for method in METHODS:
                operation = item.get(method)
                if not isinstance(operation, dict):
                    continue
                tag, reason = classify(item, operation, document)
                target = f"$.paths[{json.dumps(path)}].{method}"
                operation_id = corrected.get(
                    target, operation.get("operationId", "<unnamed>")
                )
                if reason:
                    review.append(f"{operation_id}: {reason}")
                elif tag is not None:
                    actions.append(
                        action_for(
                            document_id, path, method, operation_id, tag, entry["url"]
                        )
                    )
        overlay = {
            "overlay": "1.0.0",
            "info": {
                "title": f"Jira {document_id} generated paging (do not edit)",
                "version": "1.0.0",
            },
            "actions": actions,
        }
        output = spec_dir / f"{document_id}.paging.overlay.json"
        if output.is_symlink():
            raise ValueError(f"refusing symlink output: {output.name}")
        pending.append(
            (output, json.dumps(overlay, indent=2, sort_keys=True) + "\n", review)
        )
    for output, content, review in pending:
        output.write_text(content, encoding="utf-8")
        print(f"{output.name}: {len(json.loads(content)['actions'])} generated entries")
        for decision in review:
            print(f"HAND REVIEW: {decision}")


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
