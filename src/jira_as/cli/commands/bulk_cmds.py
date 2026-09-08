"""
Bulk operation commands for jira-as CLI.

Commands:
- transition: Bulk transition issues to a new status
- assign: Bulk assign/unassign issues
- set-priority: Bulk set priority on issues
- clone: Bulk clone issues
- delete: Bulk delete issues (destructive)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import click

from jira_as import (
    JiraError,
    ValidationError,
    get_jira_client,
    text_to_adf,
    validate_issue_key,
    validate_jql,
    validate_project_key,
)

from ..cli_utils import (
    format_json,
    handle_jira_errors,
    parse_comma_list,
)

if TYPE_CHECKING:
    from jira_as import JiraClient

# =============================================================================
# Constants
# =============================================================================

# Standard JIRA priorities
STANDARD_PRIORITIES = [
    "Highest",
    "High",
    "Medium",
    "Low",
    "Lowest",
    "Blocker",
    "Critical",
    "Major",
    "Minor",
    "Trivial",
]

# Fields to copy when cloning
CLONE_FIELDS = [
    "summary",
    "description",
    "issuetype",
    "priority",
    "labels",
    "components",
    "fixVersions",
    "duedate",
    "environment",
]


# =============================================================================
# Helper Functions
# =============================================================================


def _get_issues_to_process(
    client,
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    max_issues: int = 100,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve issues to process from either issue keys or JQL query.

    Args:
        client: JiraClient instance
        issue_keys: List of issue keys to process
        jql: JQL query to find issues (alternative to issue_keys)
        max_issues: Maximum number of issues to retrieve
        fields: List of fields to retrieve

    Returns:
        List of issue dictionaries
    """
    if fields is None:
        fields = ["key", "summary"]

    if issue_keys:
        validated_keys = [validate_issue_key(k) for k in issue_keys[:max_issues]]
        return [{"key": key} for key in validated_keys]
    elif jql:
        validated_jql = validate_jql(jql)
        result = client.search_issues(
            validated_jql, fields=fields, max_results=max_issues
        )
        return result.get("issues", [])
    else:
        raise ValidationError("Either --issues or --jql must be provided")


def _find_transition(transitions: list[dict], target_status: str) -> dict | None:
    """Find a transition that leads to the target status."""
    target_lower = target_status.lower()

    # First try exact match on transition name
    for t in transitions:
        if t["name"].lower() == target_lower:
            return t

    # Then try matching target status name
    for t in transitions:
        to_status = t.get("to", {}).get("name", "").lower()
        if to_status == target_lower:
            return t

    # Finally try partial match
    for t in transitions:
        if (
            target_lower in t["name"].lower()
            or target_lower in t.get("to", {}).get("name", "").lower()
        ):
            return t

    return None


def _resolve_user_id(client, user_identifier: str) -> str | None:
    """Resolve a user identifier to an account ID."""
    if user_identifier is None:
        return None

    if user_identifier.lower() == "self":
        return client.get_current_user_id()

    # Check if it looks like an email
    if "@" in user_identifier:
        try:
            users = client.get(
                "/rest/api/3/user/search",
                params={"query": user_identifier},
                operation="search users",
            )
            if users and len(users) > 0:
                for user in users:
                    if user.get("emailAddress", "").lower() == user_identifier.lower():
                        return user["accountId"]
                return users[0]["accountId"]
        except JiraError:
            pass

    return user_identifier


def _validate_priority(priority: str) -> str:
    """Validate and normalize priority name."""
    for std in STANDARD_PRIORITIES:
        if std.lower() == priority.lower():
            return std

    raise ValidationError(
        f"Invalid priority: '{priority}'. "
        f"Valid priorities: {', '.join(STANDARD_PRIORITIES)}"
    )


# =============================================================================
# Implementation Functions
# =============================================================================


def _bulk_transition_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    target_status: str | None = None,
    resolution: str | None = None,
    comment: str | None = None,
    dry_run: bool = False,
    max_issues: int = 100,
    delay: float = 0.1,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """Transition multiple issues to a new status."""
    if not target_status:
        raise ValidationError("Target status is required")

    def _do_transition(c: JiraClient) -> dict[str, Any]:
        issues = _get_issues_to_process(
            c,
            issue_keys=issue_keys,
            jql=jql,
            max_issues=max_issues,
            fields=["key", "summary", "status"],
        )

        total = len(issues)

        if total == 0:
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": {},
                "processed": [],
            }

        if dry_run:
            preview = []
            for issue in issues:
                key = issue["key"]
                current_status = (
                    issue.get("fields", {}).get("status", {}).get("name", "Unknown")
                )
                preview.append(
                    {
                        "key": key,
                        "from": current_status,
                        "to": target_status,
                    }
                )

            return {
                "dry_run": True,
                "success": 0,
                "failed": 0,
                "would_process": total,
                "total": total,
                "issues": preview,
                "errors": {},
                "processed": [],
            }

        success = 0
        failed = 0
        errors: dict[str, str] = {}
        processed: list[str] = []

        for i, issue in enumerate(issues, 1):
            issue_key = issue["key"]

            try:
                transitions = c.get_transitions(issue_key)
                transition = _find_transition(transitions, target_status)

                if not transition:
                    available = [t["name"] for t in transitions]
                    raise ValidationError(
                        f"Transition to '{target_status}' not available. "
                        f"Available: {', '.join(available)}"
                    )

                fields: dict[str, Any] = {}
                if resolution:
                    fields["resolution"] = {"name": resolution}

                c.transition_issue(
                    issue_key, transition["id"], fields=fields if fields else None
                )

                if comment:
                    c.add_comment(issue_key, text_to_adf(comment))

                success += 1
                processed.append(issue_key)

            except Exception as e:
                failed += 1
                errors[issue_key] = str(e)

            if i < total and delay > 0:
                time.sleep(delay)

        return {
            "success": success,
            "failed": failed,
            "total": total,
            "errors": errors,
            "processed": processed,
        }

    if client is not None:
        return _do_transition(client)

    with get_jira_client() as c:
        return _do_transition(c)


def _bulk_assign_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    assignee: str | None = None,
    unassign: bool = False,
    dry_run: bool = False,
    max_issues: int = 100,
    delay: float = 0.1,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """Assign or unassign multiple issues."""
    if not assignee and not unassign:
        raise ValidationError("Either --assignee or --unassign must be provided")

    def _do_assign(c: JiraClient) -> dict[str, Any]:
        account_id = None
        action = "unassign"
        if not unassign:
            # assignee must be set since we checked above
            assert assignee is not None
            account_id = _resolve_user_id(c, assignee)
            if account_id is None and assignee.lower() != "self":
                raise ValidationError(f"Could not resolve user: {assignee}")
            action = f"assign to {assignee}"

        issues = _get_issues_to_process(
            c,
            issue_keys=issue_keys,
            jql=jql,
            max_issues=max_issues,
            fields=["key", "summary", "assignee"],
        )

        total = len(issues)

        if total == 0:
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": {},
                "processed": [],
            }

        if dry_run:
            preview = []
            for issue in issues:
                key = issue["key"]
                current = issue.get("fields", {}).get("assignee")
                current_name = (
                    current.get("displayName", "Unassigned")
                    if current
                    else "Unassigned"
                )
                preview.append(
                    {
                        "key": key,
                        "current": current_name,
                        "action": action,
                    }
                )

            return {
                "dry_run": True,
                "success": 0,
                "failed": 0,
                "would_process": total,
                "total": total,
                "issues": preview,
                "errors": {},
                "processed": [],
            }

        success = 0
        failed = 0
        errors: dict[str, str] = {}
        processed: list[str] = []

        for i, issue in enumerate(issues, 1):
            issue_key = issue["key"]

            try:
                c.assign_issue(issue_key, account_id)
                success += 1
                processed.append(issue_key)

            except Exception as e:
                failed += 1
                errors[issue_key] = str(e)

            if i < total and delay > 0:
                time.sleep(delay)

        return {
            "success": success,
            "failed": failed,
            "total": total,
            "errors": errors,
            "processed": processed,
            "action": action,
        }

    if client is not None:
        return _do_assign(client)

    with get_jira_client() as c:
        return _do_assign(c)


def _bulk_set_priority_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    priority: str | None = None,
    dry_run: bool = False,
    max_issues: int = 100,
    delay: float = 0.1,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """Set priority on multiple issues."""
    if not priority:
        raise ValidationError("Priority is required")

    priority = _validate_priority(priority)

    def _do_set_priority(c: JiraClient) -> dict[str, Any]:
        issues = _get_issues_to_process(
            c,
            issue_keys=issue_keys,
            jql=jql,
            max_issues=max_issues,
            fields=["key", "summary", "priority"],
        )

        total = len(issues)

        if total == 0:
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": {},
                "processed": [],
            }

        if dry_run:
            preview = []
            for issue in issues:
                key = issue["key"]
                current = issue.get("fields", {}).get("priority")
                current_name = current.get("name", "None") if current else "None"
                preview.append(
                    {
                        "key": key,
                        "from": current_name,
                        "to": priority,
                    }
                )

            return {
                "dry_run": True,
                "success": 0,
                "failed": 0,
                "would_process": total,
                "total": total,
                "issues": preview,
                "errors": {},
                "processed": [],
            }

        success = 0
        failed = 0
        errors: dict[str, str] = {}
        processed: list[str] = []

        for i, issue in enumerate(issues, 1):
            issue_key = issue["key"]

            try:
                c.update_issue(
                    issue_key,
                    fields={"priority": {"name": priority}},
                    notify_users=False,
                )
                success += 1
                processed.append(issue_key)

            except Exception as e:
                failed += 1
                errors[issue_key] = str(e)

            if i < total and delay > 0:
                time.sleep(delay)

        return {
            "success": success,
            "failed": failed,
            "total": total,
            "errors": errors,
            "processed": processed,
        }

    if client is not None:
        return _do_set_priority(client)

    with get_jira_client() as c:
        return _do_set_priority(c)


def _clone_issue(
    client,
    source_issue: dict[str, Any],
    target_project: str | None = None,
    prefix: str | None = None,
    include_subtasks: bool = False,
    include_links: bool = False,
    created_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Clone a single issue."""
    if created_mapping is None:
        created_mapping = {}

    source_key = source_issue.get("key")
    source_fields = source_issue.get("fields", {})

    # Build new issue fields
    fields: dict[str, Any] = {}

    # Project
    if target_project:
        fields["project"] = {"key": target_project}
    else:
        fields["project"] = {"key": source_fields.get("project", {}).get("key")}

    # Summary with optional prefix
    summary = source_fields.get("summary", "")
    if prefix:
        fields["summary"] = f"{prefix} {summary}"
    else:
        fields["summary"] = summary

    # Issue type
    if source_fields.get("issuetype"):
        fields["issuetype"] = {"name": source_fields["issuetype"].get("name")}

    # Description
    if source_fields.get("description"):
        fields["description"] = source_fields["description"]

    # Priority
    if source_fields.get("priority"):
        fields["priority"] = {"name": source_fields["priority"].get("name")}

    # Labels
    if source_fields.get("labels"):
        fields["labels"] = source_fields["labels"]

    # Components
    if source_fields.get("components"):
        fields["components"] = [
            {"name": c.get("name")} for c in source_fields["components"]
        ]

    # Fix versions
    if source_fields.get("fixVersions"):
        fields["fixVersions"] = [
            {"name": v.get("name")} for v in source_fields["fixVersions"]
        ]

    # Due date
    if source_fields.get("duedate"):
        fields["duedate"] = source_fields["duedate"]

    # Environment
    if source_fields.get("environment"):
        fields["environment"] = source_fields["environment"]

    # Create the issue
    created = client.create_issue(fields)
    new_key = created.get("key")

    # Track mapping
    if source_key and new_key:
        created_mapping[source_key] = new_key

    # Clone subtasks if requested
    cloned_subtasks = []
    if include_subtasks:
        subtasks = source_fields.get("subtasks", [])
        for subtask in subtasks:
            subtask_key = subtask.get("key")
            subtask_data = client.get_issue(subtask_key)
            subtask_fields = subtask_data.get("fields", {})

            subtask_new_fields = {
                "project": fields["project"],
                "parent": {"key": new_key},
                "summary": (
                    f"{prefix} {subtask_fields.get('summary', '')}"
                    if prefix
                    else subtask_fields.get("summary", "")
                ),
                "issuetype": {
                    "name": subtask_fields.get("issuetype", {}).get("name", "Sub-task")
                },
            }

            if subtask_fields.get("description"):
                subtask_new_fields["description"] = subtask_fields["description"]
            if subtask_fields.get("priority"):
                subtask_new_fields["priority"] = {
                    "name": subtask_fields["priority"].get("name")
                }

            subtask_created = client.create_issue(subtask_new_fields)
            cloned_subtasks.append(subtask_created.get("key"))
            created_mapping[subtask_key] = subtask_created.get("key")

    # Recreate links if requested
    cloned_links = []
    if include_links:
        issue_links = source_fields.get("issuelinks", [])
        for link in issue_links:
            link_type = link.get("type", {}).get("name")
            if not link_type:
                continue

            try:
                if "outwardIssue" in link:
                    linked_key = link["outwardIssue"].get("key")
                    link_data = {
                        "type": {"name": link_type},
                        "outwardIssue": {"key": linked_key},
                        "inwardIssue": {"key": new_key},
                    }
                elif "inwardIssue" in link:
                    linked_key = link["inwardIssue"].get("key")
                    link_data = {
                        "type": {"name": link_type},
                        "inwardIssue": {"key": linked_key},
                        "outwardIssue": {"key": new_key},
                    }
                else:
                    continue

                client.post(
                    "/rest/api/3/issueLink", data=link_data, operation="create link"
                )
                cloned_links.append(f"{link_type} -> {linked_key}")
            except Exception:
                pass  # Skip links that can't be created

    return {
        "key": new_key,
        "id": created.get("id"),
        "source": source_key,
        "subtasks": cloned_subtasks,
        "links": cloned_links,
    }


def _bulk_clone_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    target_project: str | None = None,
    prefix: str | None = None,
    include_subtasks: bool = False,
    include_links: bool = False,
    dry_run: bool = False,
    max_issues: int = 100,
    delay: float = 0.2,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """Clone multiple issues."""
    if target_project:
        target_project = validate_project_key(target_project)

    def _do_clone(c: JiraClient) -> dict[str, Any]:
        # Clone requires full issue data
        nonlocal issue_keys, jql
        retrieval_errors: dict[str, str] = {}

        if issue_keys:
            issue_keys = [validate_issue_key(k) for k in issue_keys[:max_issues]]
            issues: list[dict[str, Any]] = []
            for key in issue_keys:
                try:
                    issue = c.get_issue(key)
                    issues.append(issue)
                except JiraError as e:
                    retrieval_errors[key] = str(e)
        elif jql:
            jql = validate_jql(jql)
            result = c.search_issues(jql, fields=["*all"], max_results=max_issues)
            issues = result.get("issues", [])
        else:
            raise ValidationError("Either --issues or --jql must be provided")

        total = len(issues)

        if total == 0:
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": retrieval_errors,
                "created_issues": [],
                "retrieval_failed": len(retrieval_errors),
            }

        if dry_run:
            preview = []
            for issue in issues:
                key = issue["key"]
                summary = issue.get("fields", {}).get("summary", "")[:50]
                subtask_count = len(issue.get("fields", {}).get("subtasks", []))
                link_count = len(issue.get("fields", {}).get("issuelinks", []))
                preview.append(
                    {
                        "key": key,
                        "summary": summary,
                        "subtasks": subtask_count if include_subtasks else 0,
                        "links": link_count if include_links else 0,
                        "target_project": target_project
                        or issue.get("fields", {}).get("project", {}).get("key"),
                    }
                )

            return {
                "dry_run": True,
                "success": 0,
                "failed": 0,
                "would_create": total,
                "total": total,
                "issues": preview,
                "errors": retrieval_errors,
                "created_issues": [],
                "retrieval_failed": len(retrieval_errors),
            }

        success = 0
        failed = 0
        errors: dict[str, str] = {}
        created_issues: list[dict[str, Any]] = []
        created_mapping: dict[str, str] = {}

        for i, issue in enumerate(issues, 1):
            issue_key = issue["key"]

            try:
                result = _clone_issue(
                    client=c,
                    source_issue=issue,
                    target_project=target_project,
                    prefix=prefix,
                    include_subtasks=include_subtasks,
                    include_links=include_links,
                    created_mapping=created_mapping,
                )

                success += 1
                created_issues.append(result)

            except Exception as e:
                failed += 1
                errors[issue_key] = str(e)

            if i < total and delay > 0:
                time.sleep(delay)

        all_errors = {**retrieval_errors, **errors}
        return {
            "success": success,
            "failed": failed,
            "total": total,
            "errors": all_errors,
            "created_issues": created_issues,
            "retrieval_failed": len(retrieval_errors),
        }

    if client is not None:
        return _do_clone(client)

    with get_jira_client() as c:
        return _do_clone(c)


def _bulk_delete_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    dry_run: bool = False,
    max_issues: int = 100,
    delete_subtasks: bool = True,
    delay: float = 0.1,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """Delete multiple issues permanently."""

    def _do_delete(c: JiraClient) -> dict[str, Any]:
        issues = _get_issues_to_process(
            c,
            issue_keys=issue_keys,
            jql=jql,
            max_issues=max_issues,
            fields=["key", "summary", "issuetype", "status", "subtasks"],
        )

        total = len(issues)

        if total == 0:
            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": {},
                "processed": [],
            }

        # Count subtasks
        total_subtasks = 0
        for issue in issues:
            subtasks = issue.get("fields", {}).get("subtasks", [])
            if subtasks:
                total_subtasks += len(subtasks)

        if dry_run:
            preview = []
            for issue in issues:
                key = issue["key"]
                fields = issue.get("fields", {})
                summary = fields.get("summary", "")[:50]
                issue_type = fields.get("issuetype", {}).get("name", "")
                status = fields.get("status", {}).get("name", "")
                subtasks = fields.get("subtasks", [])
                preview.append(
                    {
                        "key": key,
                        "type": issue_type,
                        "status": status,
                        "summary": summary,
                        "subtasks": len(subtasks) if delete_subtasks else 0,
                    }
                )

            return {
                "dry_run": True,
                "success": 0,
                "failed": 0,
                "would_delete": total,
                "total": total,
                "total_subtasks": total_subtasks if delete_subtasks else 0,
                "issues": preview,
                "errors": {},
                "processed": [],
            }

        success = 0
        failed = 0
        errors: dict[str, str] = {}
        processed: list[str] = []

        for i, issue in enumerate(issues, 1):
            issue_key = issue["key"]

            try:
                c.delete_issue(issue_key, delete_subtasks=delete_subtasks)
                success += 1
                processed.append(issue_key)

            except Exception as e:
                failed += 1
                errors[issue_key] = str(e)

            if i < total and delay > 0:
                time.sleep(delay)

        return {
            "success": success,
            "failed": failed,
            "total": total,
            "errors": errors,
            "processed": processed,
        }

    if client is not None:
        return _do_delete(client)

    with get_jira_client() as c:
        return _do_delete(c)


# =============================================================================
# Formatting Functions
# =============================================================================


def _format_bulk_result(result: dict, operation: str) -> str:
    """Format bulk operation result for text output."""
    lines = []

    if result.get("dry_run"):
        count = result.get(
            "would_process", result.get("would_create", result.get("would_delete", 0))
        )
        lines.append(f"[DRY RUN] Would {operation} {count} issue(s)")

        issues = result.get("issues", [])
        if issues:
            lines.append("")
            for issue in issues[:20]:
                if isinstance(issue, dict):
                    key = issue.get("key", "")
                    if "from" in issue and "to" in issue:
                        lines.append(f"  - {key}: {issue['from']} -> {issue['to']}")
                    elif "current" in issue:
                        lines.append(
                            f"  - {key}: {issue['current']} -> {issue['action']}"
                        )
                    elif "summary" in issue:
                        lines.append(f"  - {key}: {issue['summary']}")
                    else:
                        lines.append(f"  - {key}")
                else:
                    lines.append(f"  - {issue}")

            if len(issues) > 20:
                lines.append(f"  ... and {len(issues) - 20} more")

        lines.append("")
        lines.append("Use --yes to apply changes")

    elif result.get("cancelled"):
        lines.append("Operation cancelled by user.")

    else:
        lines.append(f"{result['success']} succeeded, {result['failed']} failed")

        if result.get("retrieval_failed"):
            lines.append(f"  ({result['retrieval_failed']} could not be retrieved)")

        if result.get("created_issues"):
            lines.append("")
            lines.append("Created issues:")
            for item in result["created_issues"][:20]:
                lines.append(f"  {item['source']} -> {item['key']}")
            if len(result["created_issues"]) > 20:
                lines.append(f"  ... and {len(result['created_issues']) - 20} more")

        if result.get("errors"):
            lines.append("")
            lines.append("Errors:")
            for key, error in list(result["errors"].items())[:10]:
                error_short = error[:80] + "..." if len(error) > 80 else error
                lines.append(f"  {key}: {error_short}")
            if len(result["errors"]) > 10:
                lines.append(f"  ... and {len(result['errors']) - 10} more errors")

    return "\n".join(lines)


# =============================================================================
# Click Commands
# =============================================================================


# =============================================================================
# Generic Surface workflows (legacy helpers above remain for retained callers)
# =============================================================================


def workflow_surface(transport: str | None):
    """Construct the product Surface without the legacy client adapter."""
    from jira_as import engine

    return engine.create_surface(transport=transport)


def workflow_call(surface, operation: str, parameters=None, body=None, **options):
    """Keep every workflow request on the indexed, guarded transport path."""
    from as_engine.errors import SurfaceError

    try:
        return surface.call(operation, parameters or {}, body, **options).body
    except SurfaceError as exc:
        raise click.ClickException(str(exc)) from exc


def workflow_options(function):
    function = click.option(
        "--transport", type=click.Choice(["simulation", "responder", "http"])
    )(function)
    function = click.option(
        "--checkpoint",
        type=click.Path(dir_okay=False),
        help="Resume completed steps from this bound checkpoint file.",
    )(function)
    return function


class WorkflowCheckpoint:
    """Bind a resumable selection and each successful step to one invocation.

    The file is replaced atomically after each step. A checkpoint records the
    selected issue snapshots so a status-changing JQL run resumes that selection
    even when completed issues no longer match the original query.
    """

    def __init__(self, path, operation: str, selection: dict, options: dict):
        import json
        from pathlib import Path

        self.path = Path(path) if path else None
        self.binding = {
            "operation": operation,
            "selection": selection,
            "options": options,
        }
        self.data: dict[str, Any] = {"version": 1, "binding": self.binding, "steps": {}}
        if self.path and self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except (OSError, ValueError) as exc:
                raise click.ClickException("Cannot read workflow checkpoint") from exc
            if (
                not isinstance(self.data, dict)
                or self.data.get("version") != 1
                or self.data.get("binding") != self.binding
                or not isinstance(self.data.get("steps"), dict)
            ):
                raise click.ClickException(
                    "Checkpoint operation, selection or options mismatch"
                )

    def save(self):
        import json
        import os
        import tempfile

        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.data, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def step(self, name: str, action):
        if name in self.data["steps"]:
            return self.data["steps"][name]
        result = action()
        self.data["steps"][name] = result
        self.save()
        return result

    def select(self, surface, issues: str | None, jql: str | None, maximum: int):
        if not issues and not jql:
            raise click.UsageError("Either --jql or --issues is required")
        if issues and jql:
            raise click.UsageError("--jql and --issues are mutually exclusive")
        if maximum < 1:
            raise click.BadParameter("Must be positive", param_hint="--max-issues")
        if "selected" in self.data:
            selected = self.data["selected"]
            if not isinstance(selected, list) or any(
                not isinstance(item, dict) or not isinstance(item.get("key"), str)
                for item in selected
            ):
                raise click.ClickException("Invalid checkpoint selection")
            return selected
        if issues:
            keys = list(
                dict.fromkeys(
                    validate_issue_key(k) for k in parse_comma_list(issues) or []
                )
            )
            selected = [
                workflow_call(surface, "getIssue", {"issueIdOrKey": k}, raw=True)
                for k in keys[:maximum]
            ]
        else:
            selected = workflow_call(
                surface,
                "searchAndReconsileIssuesUsingJql",
                {"jql": jql, "fields": ["*all"], "maxResults": min(maximum, 100)},
                all_pages=True,
                limit=maximum,
                raw=True,
            )
        self.data["selected"] = selected
        self.save()
        return selected


def workflow_transition(transitions: list[dict], targets: list[str]):
    """Prefer exact names/statuses; refuse ambiguous fuzzy matches."""
    for target in targets:
        matches = [
            t
            for t in transitions
            if target.casefold()
            in {
                str(t.get("name", "")).casefold(),
                str(t.get("to", {}).get("name", "")).casefold(),
            }
        ]
        if matches:
            break
    else:
        matches = [
            t
            for t in transitions
            if any(
                target.casefold() in str(t.get("name", "")).casefold()
                or target.casefold() in str(t.get("to", {}).get("name", "")).casefold()
                for target in targets
            )
        ]
    if len(matches) != 1:
        reason = "Ambiguous" if matches else "No matching"
        raise click.ClickException(f"{reason} transition for {', '.join(targets)}")
    return matches[0]


def workflow_link(surface, link_type: str, inward: str, outward: str):
    return workflow_call(
        surface,
        "linkIssues",
        {},
        {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward},
            "outwardIssue": {"key": outward},
        },
        scope_argv_identity=outward.rsplit("-", 1)[0],
    )


def workflow_clone(
    surface,
    checkpoint,
    source,
    *,
    target_project=None,
    prefix=None,
    summary=None,
    include_subtasks=False,
    include_links=False,
    create_clone_link=False,
    mapping=None,
):
    """Persist parent, child and link successes independently for safe resume."""
    from copy import deepcopy

    source_key = source["key"]
    original = source.get("fields", {})
    project = target_project or original.get("project", {}).get("key")
    if not project:
        raise click.ClickException(f"Source {source_key} has no project key")
    fields = {
        name: deepcopy(original[name]) for name in CLONE_FIELDS if name in original
    }
    fields["project"] = {"key": project}
    fields["summary"] = (
        summary or f"{prefix or '[Clone]'} {original.get('summary', '')}"
    )
    if original.get("issuetype", {}).get("subtask") and original.get("parent"):
        fields["parent"] = deepcopy(original["parent"])
    created = checkpoint.step(
        f"{source_key}:parent",
        lambda: workflow_call(
            surface, "createIssue", {}, {"fields": fields}, scope_argv_identity=project
        ),
    )
    clone_key = created["key"]
    if mapping is not None:
        mapping[source_key] = clone_key
    result = {
        "source": source_key,
        "key": clone_key,
        "original_key": source_key,
        "clone_key": clone_key,
        "project": project,
        "subtasks_cloned": 0,
        "links_copied": 0,
        "clone_link_created": False,
    }
    if include_subtasks:
        for subtask in original.get("subtasks", []):
            child_key = subtask["key"]

            def create_child(child_key=child_key):
                child = workflow_call(
                    surface, "getIssue", {"issueIdOrKey": child_key}, raw=True
                )
                child_fields = {
                    name: deepcopy(child.get("fields", {})[name])
                    for name in CLONE_FIELDS
                    if name in child.get("fields", {})
                }
                child_fields.update(project={"key": project}, parent={"key": clone_key})
                return workflow_call(
                    surface,
                    "createIssue",
                    {},
                    {"fields": child_fields},
                    scope_argv_identity=project,
                )

            child = checkpoint.step(f"{source_key}:subtask:{child_key}", create_child)
            if mapping is not None:
                mapping[child_key] = child["key"]
            result["subtasks_cloned"] += 1
    if create_clone_link:
        checkpoint.step(
            f"{source_key}:clone-link",
            lambda: workflow_link(surface, "Cloners", clone_key, source_key),
        )
        result["clone_link_created"] = True
    if include_links:
        for index, link in enumerate(original.get("issuelinks", [])):
            inward, outward = clone_key, None
            if "outwardIssue" in link:
                outward = link["outwardIssue"]["key"]
            elif "inwardIssue" in link:
                inward, outward = link["inwardIssue"]["key"], clone_key
            if outward is None:
                continue
            if mapping:
                inward, outward = (
                    mapping.get(inward, inward),
                    mapping.get(outward, outward),
                )
            checkpoint.step(
                f"{source_key}:link:{link.get('id', index)}",
                lambda inward=inward, outward=outward, link=link: workflow_link(
                    surface, link["type"]["name"], inward, outward
                ),
            )
            result["links_copied"] += 1
    return result


def _run_bulk(
    operation,
    *,
    jql,
    issues,
    dry_run,
    max_issues,
    yes,
    transport,
    checkpoint,
    **options,
):
    surface = workflow_surface(transport)
    state = WorkflowCheckpoint(
        checkpoint,
        f"bulk {operation}",
        {"jql": jql, "issues": issues, "maximum": max_issues},
        options,
    )
    selected = state.select(surface, issues, jql, max_issues)
    preview = dry_run or (operation == "delete" and not yes)
    result: dict[str, Any] = {
        "dry_run": preview,
        "success": 0,
        "failed": 0,
        "total": len(selected),
        "errors": {},
        "processed": [],
        "issues": [],
        "created_issues": [],
        "would_process": len(selected),
    }
    account = None
    if operation == "assign" and selected and not options.get("unassign"):
        assignee = options["assignee"]

        def resolve_assignee():
            if assignee == "self":
                return workflow_call(surface, "getCurrentUser")["accountId"]
            if "@" in assignee:
                users = workflow_call(
                    surface,
                    "findAssignableUsers",
                    {"query": assignee, "issueKey": selected[0]["key"]},
                )
                exact = [
                    u
                    for u in users
                    if u.get("emailAddress", "").casefold() == assignee.casefold()
                ]
                if len(exact) != 1:
                    raise click.ClickException("Assignee did not resolve unambiguously")
                return exact[0]["accountId"]
            return assignee

        account = state.step("assignee", resolve_assignee)
    mapping: dict[str, str] = {}
    for issue in selected:
        key = issue["key"]
        try:
            if f"{key}:complete" in state.data["steps"]:
                saved = state.data["steps"][f"{key}:complete"]
                if operation == "clone":
                    result["created_issues"].append(saved)
                    mapping[key] = saved["key"]
                result["success"] += 1
                result["processed"].append(key)
                continue
            plan = {"key": key, "summary": issue.get("fields", {}).get("summary", "")}
            if operation == "transition":

                def choose():
                    transitions = workflow_call(
                        surface, "getTransitions", {"issueIdOrKey": key}
                    ).get("transitions", [])
                    return workflow_transition(transitions, [options["target_status"]])

                transition = state.step(f"{key}:choice", choose)
                plan.update(
                    {
                        "from": issue.get("fields", {}).get("status", {}).get("name"),
                        "to": transition.get("to", {}).get(
                            "name", transition.get("name")
                        ),
                    }
                )
            result["issues"].append(plan)
            if preview:
                continue
            saved = None
            if operation == "transition":
                body = {"transition": {"id": transition["id"]}}
                if options.get("resolution"):
                    body["fields"] = {"resolution": {"name": options["resolution"]}}
                state.step(
                    f"{key}:mutation",
                    lambda: workflow_call(
                        surface, "doTransition", {"issueIdOrKey": key}, body
                    ),
                )
                if options.get("comment"):
                    state.step(
                        f"{key}:comment",
                        lambda: workflow_call(
                            surface,
                            "addComment",
                            {"issueIdOrKey": key},
                            {"body": options["comment"]},
                        ),
                    )
            elif operation == "assign":
                state.step(
                    f"{key}:mutation",
                    lambda: workflow_call(
                        surface,
                        "assignIssue",
                        {"issueIdOrKey": key},
                        {"accountId": account},
                    ),
                )
            elif operation == "set-priority":
                state.step(
                    f"{key}:mutation",
                    lambda: workflow_call(
                        surface,
                        "editIssue",
                        {"issueIdOrKey": key},
                        {"fields": {"priority": {"name": options["priority"]}}},
                    ),
                )
            elif operation == "delete":
                state.step(
                    f"{key}:mutation",
                    lambda: workflow_call(
                        surface,
                        "deleteIssue",
                        {
                            "issueIdOrKey": key,
                            "deleteSubtasks": str(not options["no_subtasks"]).lower(),
                        },
                    ),
                )
            elif operation == "clone":
                saved = workflow_clone(
                    surface, state, issue, mapping=mapping, **options
                )
                result["created_issues"].append(saved)
            state.step(f"{key}:complete", lambda: saved)
            result["success"] += 1
            result["processed"].append(key)
        except click.ClickException as exc:
            result["failed"] += 1
            result["errors"][key] = str(exc)
    return result


def _bulk_options(function):
    for decorator in (
        click.option("--jql", "-q"),
        click.option("--issues", "-i"),
        click.option("--dry-run", "-n", is_flag=True),
        click.option("--max-issues", "-m", type=click.IntRange(min=1), default=100),
        click.option("--yes", "--confirm", "-y", is_flag=True),
        click.option(
            "--output", "-o", type=click.Choice(["text", "json"]), default="text"
        ),
        workflow_options,
    ):
        function = decorator(function)
    return function


def _emit_bulk(result, output, operation):
    rendered = (
        format_json(result)
        if output == "json"
        else _format_bulk_result(result, operation)
    )
    if output == "text" and result.get("dry_run"):
        rendered = rendered.replace(
            "Use --yes to apply changes",
            "Use --confirm or --yes to apply deletion"
            if operation == "delete"
            else "Omit --dry-run to apply changes",
        )
    click.echo(rendered)
    if result["failed"]:
        raise click.exceptions.Exit(1)


@click.group()
def bulk():
    """Commands for bulk operations on multiple issues."""


@bulk.command(name="transition")
@click.option("--to", "-t", "target_status", required=True)
@click.option("--comment", "-c")
@click.option("--resolution", "-r")
@_bulk_options
@handle_jira_errors
def bulk_transition(output, **options):
    """Preview with --dry-run; otherwise transition all selected issues."""
    _emit_bulk(_run_bulk("transition", **options), output, "transition")


@bulk.command(name="assign")
@click.option("--assignee", "-a")
@click.option("--unassign", is_flag=True)
@_bulk_options
@handle_jira_errors
def bulk_assign(output, **options):
    """Assign or unassign selected issues."""
    if bool(options["assignee"]) == bool(options["unassign"]):
        raise click.UsageError("Specify exactly one of --assignee or --unassign")
    _emit_bulk(_run_bulk("assign", **options), output, "assign")


@bulk.command(name="set-priority")
@click.option("--priority", "-p", required=True)
@_bulk_options
@handle_jira_errors
def bulk_set_priority(output, **options):
    """Set the priority of selected issues."""
    _emit_bulk(_run_bulk("set-priority", **options), output, "set priority")


@bulk.command(name="clone")
@click.option("--target-project", "-t")
@click.option("--prefix", "-P")
@click.option("--include-links", "-l", is_flag=True)
@click.option("--include-subtasks", "-s", is_flag=True)
@_bulk_options
@handle_jira_errors
def bulk_clone(output, **options):
    """Clone selected issues, optionally copying subtasks and links."""
    _emit_bulk(_run_bulk("clone", **options), output, "clone")


@bulk.command(name="delete")
@click.option("--no-subtasks", is_flag=True)
@_bulk_options
@handle_jira_errors
def bulk_delete(output, **options):
    """Preview permanent deletion; send only with --confirm or --yes."""
    _emit_bulk(_run_bulk("delete", **options), output, "delete")
