"""
Output formatting utilities for JIRA data.

Provides functions to format JIRA API responses as tables, JSON,
CSV, and human-readable text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Import generic formatters from the base library
from assistant_skills_lib.formatters import (
    export_csv,
    format_json,
    format_table,
    format_timestamp,
    get_csv_string,
    print_info,
    print_success,
    print_warning,
)

from .adf_helper import adf_to_text
from .constants import EPIC_LINK_FIELD, STORY_POINTS_FIELD
from .validators import safe_get_nested


@dataclass
class IssueFields:
    """Extracted issue fields for display formatting."""

    key: str
    summary: str
    status: str
    issue_type: str
    priority: str
    assignee: str
    reporter: str
    created: str
    updated: str
    epic_link: str | None = None
    story_points: float | None = None
    sprint: str | None = None
    parent_key: str | None = None
    parent_summary: str | None = None


def extract_issue_fields(issue: dict[str, Any]) -> IssueFields:
    """
    Extract and normalize issue fields for display.

    Centralizes nested dict access patterns used across formatting functions.

    Args:
        issue: Issue data from JIRA API

    Returns:
        IssueFields dataclass with normalized values
    """
    fields = issue.get("fields", {})

    # Extract sprint name from various formats
    sprint = fields.get("sprint")
    sprint_name = None
    if sprint:
        if isinstance(sprint, dict):
            sprint_name = sprint.get("name", str(sprint))
        elif isinstance(sprint, list) and sprint:
            first = sprint[0]
            sprint_name = (
                first.get("name", str(first)) if isinstance(first, dict) else str(first)
            )
        else:
            sprint_name = str(sprint)

    # Extract parent info
    parent = fields.get("parent")
    parent_key = safe_get_nested(parent, "key") if parent else None
    parent_summary = safe_get_nested(parent, "fields.summary", "") if parent else None

    return IssueFields(
        key=issue.get("key", "N/A"),
        summary=fields.get("summary", "N/A"),
        status=safe_get_nested(fields, "status.name", "N/A"),
        issue_type=safe_get_nested(fields, "issuetype.name", "N/A"),
        priority=(
            safe_get_nested(fields, "priority.name", "None")
            if fields.get("priority")
            else "None"
        ),
        assignee=(
            safe_get_nested(fields, "assignee.displayName", "Unassigned")
            if fields.get("assignee")
            else "Unassigned"
        ),
        reporter=(
            safe_get_nested(fields, "reporter.displayName", "N/A")
            if fields.get("reporter")
            else "N/A"
        ),
        created=fields.get("created", "N/A"),
        updated=fields.get("updated", "N/A"),
        epic_link=fields.get(EPIC_LINK_FIELD),
        story_points=fields.get(STORY_POINTS_FIELD),
        sprint=sprint_name,
        parent_key=parent_key,
        parent_summary=parent_summary,
    )


def format_issue(issue: dict[str, Any], detailed: bool = False) -> str:
    """
    Format a JIRA issue for display.

    Args:
        issue: Issue data from JIRA API
        detailed: If True, include all fields

    Returns:
        Formatted issue string
    """
    f = extract_issue_fields(issue)
    fields = issue.get("fields", {})

    output = []
    output.append(f"Key:      {f.key}")
    output.append(f"Type:     {f.issue_type}")
    output.append(f"Summary:  {f.summary}")
    output.append(f"Status:   {f.status}")
    output.append(f"Priority: {f.priority}")
    output.append(f"Assignee: {f.assignee}")

    # Agile fields
    if f.epic_link:
        output.append(f"Epic:     {f.epic_link}")

    if f.story_points is not None:
        output.append(f"Points:   {f.story_points}")

    if f.sprint:
        output.append(f"Sprint:   {f.sprint}")

    # Parent (for subtasks)
    if f.parent_key:
        output.append(f"Parent:   {f.parent_key} - {f.parent_summary}")

    if detailed:
        output.append(f"Reporter: {f.reporter}")
        output.append(f"Created:  {format_timestamp(f.created)}")
        output.append(f"Updated:  {format_timestamp(f.updated)}")

        description = fields.get("description")
        if description:
            if isinstance(description, dict):
                desc_text = adf_to_text(description)
            else:
                desc_text = str(description)

            if desc_text:
                output.append("\nDescription:")
                for line in desc_text.split("\n"):
                    output.append(f"  {line}")

        labels = fields.get("labels", [])
        if labels:
            output.append(f"\nLabels: {', '.join(labels)}")

        components = fields.get("components", [])
        if components:
            comp_names = [c.get("name", "") for c in components]
            output.append(f"Components: {', '.join(comp_names)}")

        # Subtasks
        subtasks = fields.get("subtasks", [])
        if subtasks:
            output.append(f"\nSubtasks ({len(subtasks)}):")
            for st in subtasks:
                st_key = st.get("key", "")
                st_summary = st.get("fields", {}).get("summary", "")
                st_status = st.get("fields", {}).get("status", {}).get("name", "")
                output.append(f"  [{st_status}] {st_key} - {st_summary}")

        # Issue links
        issue_links = fields.get("issuelinks", [])
        if issue_links:
            output.append(f"\nLinks ({len(issue_links)}):")
            for link in issue_links:
                link.get("type", {}).get("name", "Unknown")
                if "outwardIssue" in link:
                    direction = link.get("type", {}).get("outward", "links to")
                    linked = link["outwardIssue"]
                else:
                    direction = link.get("type", {}).get("inward", "linked from")
                    linked = link.get("inwardIssue", {})
                linked_key = linked.get("key", "")
                linked_summary = linked.get("fields", {}).get("summary", "")[:40]
                linked_status = (
                    linked.get("fields", {}).get("status", {}).get("name", "")
                )
                output.append(
                    f"  {direction} {linked_key} [{linked_status}] {linked_summary}"
                )

    return "\n".join(output)


def format_transitions(transitions: list[dict[str, Any]]) -> str:
    """
    Format available transitions for display.

    Args:
        transitions: List of transition objects from JIRA API

    Returns:
        Formatted transitions string
    """
    if not transitions:
        return "No transitions available"

    data = []
    for t in transitions:
        data.append(
            {
                "ID": t.get("id", ""),
                "Name": t.get("name", ""),
                "To Status": t.get("to", {}).get("name", ""),
            }
        )

    return format_table(data, columns=["ID", "Name", "To Status"])


def format_comments(comments: list[dict[str, Any]], limit: int | None = None) -> str:
    """
    Format issue comments for display.

    Args:
        comments: List of comment objects from JIRA API
        limit: Maximum number of comments to display

    Returns:
        Formatted comments string
    """
    if not comments:
        return "No comments"

    if limit:
        comments = comments[:limit]

    output = []
    for i, comment in enumerate(comments, 1):
        author = comment.get("author", {}).get("displayName", "Unknown")
        created = comment.get("created", "N/A")
        body = comment.get("body")

        if isinstance(body, dict):
            body_text = adf_to_text(body)
        else:
            body_text = str(body) if body else ""

        output.append(f"Comment #{i} by {author} at {format_timestamp(created)}:")
        for line in body_text.split("\n"):
            output.append(f"  {line}")
        output.append("")

    return "\n".join(output)


def format_search_results(
    issues: list[dict[str, Any]],
    show_agile: bool = False,
    show_links: bool = False,
    show_time: bool = False,
) -> str:
    """
    Format search results as a table.

    Args:
        issues: List of issue objects from JIRA API
        show_agile: If True, include epic and story points columns
        show_links: If True, include links summary column
        show_time: If True, include time tracking columns

    Returns:
        Formatted table string
    """
    if not issues:
        return "No issues found"

    data = []
    for issue in issues:
        fields = issue.get("fields", {})
        row = {
            "Key": issue.get("key", ""),
            "Type": safe_get_nested(fields, "issuetype.name", ""),
            "Status": safe_get_nested(fields, "status.name", ""),
            "Priority": (
                safe_get_nested(fields, "priority.name", "")
                if fields.get("priority")
                else ""
            ),
            "Assignee": (
                safe_get_nested(fields, "assignee.displayName", "")
                if fields.get("assignee")
                else ""
            ),
            "Reporter": (
                safe_get_nested(fields, "reporter.displayName", "")
                if fields.get("reporter")
                else ""
            ),
            "Summary": fields.get("summary", "")[:50],
        }

        if show_agile:
            epic = fields.get(EPIC_LINK_FIELD, "")
            points = fields.get(STORY_POINTS_FIELD, "")
            row["Epic"] = epic if epic else ""
            row["Pts"] = str(points) if points else ""

        if show_links:
            links = fields.get("issuelinks", [])
            link_count = len(links)
            if link_count > 0:
                link_types = {safe_get_nested(link, "type.name", "") for link in links}
                row["Links"] = f"{link_count} ({', '.join(link_types)})"
            else:
                row["Links"] = ""

        if show_time:
            tt = fields.get("timetracking", {})
            row["Est"] = tt.get("originalEstimate", "")
            row["Rem"] = tt.get("remainingEstimate", "")
            row["Spent"] = tt.get("timeSpent", "")

        data.append(row)

    if show_agile:
        columns = [
            "Key",
            "Type",
            "Status",
            "Pts",
            "Epic",
            "Assignee",
            "Reporter",
            "Summary",
        ]
    elif show_links:
        columns = ["Key", "Type", "Status", "Links", "Assignee", "Reporter", "Summary"]
    elif show_time:
        columns = [
            "Key",
            "Type",
            "Status",
            "Est",
            "Rem",
            "Spent",
            "Assignee",
            "Reporter",
            "Summary",
        ]
    else:
        columns = [
            "Key",
            "Type",
            "Status",
            "Priority",
            "Assignee",
            "Reporter",
            "Summary",
        ]

    return format_table(data, columns=columns)
