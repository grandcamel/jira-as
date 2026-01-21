"""
Agile/Scrum commands for jira-as CLI.

Commands:
Epic Group:
- epic create: Create a new epic
- epic get: Get epic details
- epic add-issues: Add issues to an epic

Sprint Group:
- sprint list: List sprints for a board
- sprint create: Create a new sprint
- sprint get: Get sprint details
- sprint manage: Start/close/update sprint
- sprint move-issues: Move issues to sprint/backlog

Other Commands:
- backlog: Get backlog issues
- rank: Rank issues in backlog
- estimate: Set story points
- estimates: Get estimation summaries
- velocity: Calculate velocity
- subtask: Create a subtask
"""

import json
from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from jira_as import JiraClient

from jira_as import (
    JiraError,
    ValidationError,
    get_agile_field,
    get_agile_fields,
    get_jira_client,
    markdown_to_adf,
    parse_date_to_iso,
    text_to_adf,
    validate_issue_key,
    validate_project_key,
)

from ..cli_utils import (
    format_json,
    get_client_from_context,
    handle_jira_errors,
    parse_comma_list,
    parse_json_arg,
)

# =============================================================================
# Constants
# =============================================================================

VALID_EPIC_COLORS = [
    "blue",
    "cyan",
    "green",
    "yellow",
    "orange",
    "red",
    "magenta",
    "purple",
    "lime",
    "pink",
    "teal",
]

FIBONACCI_SEQUENCE = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


# =============================================================================
# Helper Functions
# =============================================================================


def _get_board_for_project(
    project_key: str, client: "JiraClient | None" = None
) -> dict | None:
    """Find the first Scrum board for a project."""

    def _do_work(c: "JiraClient") -> dict | None:
        result = c.get_all_boards(project_key=project_key)
        boards = result.get("values", [])
        scrum_boards = [b for b in boards if b.get("type") == "scrum"]
        return scrum_boards[0] if scrum_boards else (boards[0] if boards else None)

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_board_id_for_project(
    project_key: str, client: "JiraClient | None" = None
) -> int:
    """Get board ID for a project, raising error if not found."""
    validate_project_key(project_key)
    board = _get_board_for_project(project_key, client=client)
    if not board:
        raise ValidationError(
            f"No board found for project {project_key}. "
            "Ensure the project has a Scrum or Kanban board configured."
        )
    return board["id"]


def _parse_date_safe(date_str: str | None) -> str | None:
    """Parse date string into ISO format, converting ValueError to ValidationError."""
    if not date_str:
        return None
    try:
        return parse_date_to_iso(date_str)
    except ValueError as e:
        raise ValidationError(str(e))


def _convert_description_to_adf(description: str) -> dict:
    """Convert description to ADF format."""
    if description.strip().startswith("{"):
        return json.loads(description)
    elif "\n" in description or any(
        md in description for md in ["**", "*", "#", "`", "["]
    ):
        return markdown_to_adf(description)
    else:
        return text_to_adf(description)


# =============================================================================
# Epic Implementation Functions
# =============================================================================


def _create_epic_impl(
    project: str,
    summary: str,
    description: str | None = None,
    epic_name: str | None = None,
    color: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    custom_fields: dict | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Create a new Epic in JIRA."""
    if not project:
        raise ValidationError("Project key is required")
    if not summary:
        raise ValidationError("Summary is required")

    project = validate_project_key(project)

    if color and color.lower() not in VALID_EPIC_COLORS:
        raise ValidationError(
            f"Invalid epic color: {color}. Valid colors: {', '.join(VALID_EPIC_COLORS)}"
        )

    fields: dict[str, Any] = {
        "project": {"key": project},
        "issuetype": {"name": "Epic"},
        "summary": summary,
    }

    if description:
        fields["description"] = _convert_description_to_adf(description)

    if priority:
        fields["priority"] = {"name": priority}

    if labels:
        fields["labels"] = labels

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        nonlocal fields
        if assignee:
            if assignee.lower() == "self":
                account_id = c.get_current_user_id()
                fields["assignee"] = {"accountId": account_id}
            elif "@" in assignee:
                fields["assignee"] = {"emailAddress": assignee}
            else:
                fields["assignee"] = {"accountId": assignee}

        agile_fields = get_agile_fields()

        if epic_name:
            fields[agile_fields["epic_name"]] = epic_name

        if color:
            fields[agile_fields["epic_color"]] = color.lower()

        if custom_fields:
            fields.update(custom_fields)

        return c.create_issue(fields)

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_epic_impl(
    epic_key: str,
    with_children: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Get epic details and optionally calculate progress."""
    epic_key = validate_issue_key(epic_key)

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        agile_fields = get_agile_fields()
        story_points_field = agile_fields["story_points"]

        epic = c.get_issue(epic_key)

        result: dict[str, Any] = {
            "key": epic["key"],
            "fields": epic["fields"],
            "_agile_fields": agile_fields,
        }

        if with_children:
            jql = f'"Epic Link" = {epic_key} OR parent = {epic_key}'
            search_results = c.search_issues(
                jql,
                fields=["key", "summary", "status", "issuetype", story_points_field],
                max_results=1000,
            )

            children = search_results.get("issues", [])
            result["children"] = children

            total_issues = len(children)
            done_issues = sum(
                1
                for issue in children
                if issue["fields"]["status"]["name"].lower()
                in ["done", "closed", "resolved"]
            )

            result["progress"] = {
                "total": total_issues,
                "done": done_issues,
                "percentage": int(
                    (done_issues / total_issues * 100) if total_issues > 0 else 0
                ),
            }

            total_points = 0
            done_points = 0

            for issue in children:
                points = issue["fields"].get(story_points_field)
                if points is not None:
                    total_points += points
                    if issue["fields"]["status"]["name"].lower() in [
                        "done",
                        "closed",
                        "resolved",
                    ]:
                        done_points += points

            if total_points > 0:
                result["story_points"] = {
                    "total": total_points,
                    "done": done_points,
                    "percentage": int(done_points / total_points * 100),
                }

        return result

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _add_to_epic_impl(
    epic_key: str,
    issue_keys: list[str],
    dry_run: bool = False,
    remove: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Add issues to an epic or remove them from epics."""
    if not remove and not epic_key:
        raise ValidationError("Epic key is required (or use remove=True)")

    if not issue_keys:
        raise ValidationError("At least one issue key is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        nonlocal epic_key
        result: dict[str, Any] = {"added": 0, "removed": 0, "failed": 0, "failures": []}

        if not remove:
            epic_key = validate_issue_key(epic_key)
            epic = c.get_issue(epic_key)

            if epic["fields"]["issuetype"]["name"] != "Epic":
                raise ValidationError(
                    f"{epic_key} is not an Epic (type: {epic['fields']['issuetype']['name']})"
                )

        if dry_run:
            result["would_add"] = len(issue_keys)
            return result

        epic_link_field = get_agile_field("epic_link")

        for iss_key in issue_keys:
            try:
                validated_key = validate_issue_key(iss_key)
                fields = {epic_link_field: epic_key if not remove else None}
                c.update_issue(validated_key, fields)

                if remove:
                    result["removed"] += 1
                else:
                    result["added"] += 1

            except (JiraError, ValidationError) as e:
                result["failed"] += 1
                result["failures"].append({"issue": iss_key, "error": str(e)})

        return result

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


# =============================================================================
# Sprint Implementation Functions
# =============================================================================


def _list_sprints_impl(
    board_id: int | None = None,
    project_key: str | None = None,
    state: str | None = None,
    max_results: int = 50,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """List sprints for a board or project."""
    if not board_id and not project_key:
        raise ValidationError("Either board_id or project_key is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        board = None
        actual_board_id = board_id

        if project_key and not board_id:
            validate_project_key(project_key)
            board = _get_board_for_project(project_key, client=c)
            if not board:
                raise ValidationError(
                    f"No board found for project {project_key}. "
                    "Ensure the project has a Scrum or Kanban board configured."
                )
            actual_board_id = board["id"]

        result = c.get_board_sprints(
            actual_board_id, state=state, max_results=max_results
        )
        sprints = result.get("values", [])

        return {
            "board": board or {"id": actual_board_id},
            "sprints": sprints,
            "state_filter": state,
            "total": len(sprints),
        }

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _create_sprint_impl(
    board_id: int,
    name: str,
    goal: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Create a new Sprint in JIRA."""
    if not board_id:
        raise ValidationError("Board ID is required")
    if not name:
        raise ValidationError("Sprint name is required")

    parsed_start = _parse_date_safe(start_date)
    parsed_end = _parse_date_safe(end_date)

    if parsed_start and parsed_end:
        start_dt = datetime.fromisoformat(parsed_start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(parsed_end.replace("Z", "+00:00"))
        if end_dt <= start_dt:
            raise ValidationError("End date must be after start date")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        return c.create_sprint(
            board_id=board_id,
            name=name,
            goal=goal,
            start_date=parsed_start,
            end_date=parsed_end,
        )

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_sprint_impl(
    sprint_id: int,
    with_issues: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Get sprint details and optionally calculate progress."""
    if not sprint_id:
        raise ValidationError("Sprint ID is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        story_points_field = get_agile_field("story_points")

        sprint = c.get_sprint(sprint_id)
        result = dict(sprint)
        result["_story_points_field"] = story_points_field

        if with_issues:
            issues_response = c.get_sprint_issues(sprint_id)
            issues = issues_response.get("issues", [])
            result["issues"] = issues

            total_issues = len(issues)
            done_issues = sum(
                1
                for issue in issues
                if issue["fields"]["status"]["name"].lower()
                in ["done", "closed", "resolved"]
            )

            result["progress"] = {
                "total": total_issues,
                "done": done_issues,
                "percentage": int(
                    (done_issues / total_issues * 100) if total_issues > 0 else 0
                ),
            }

            total_points = 0
            done_points = 0

            for issue in issues:
                points = issue["fields"].get(story_points_field)
                if points is not None:
                    total_points += points
                    if issue["fields"]["status"]["name"].lower() in [
                        "done",
                        "closed",
                        "resolved",
                    ]:
                        done_points += points

            if total_points > 0:
                result["story_points"] = {
                    "total": total_points,
                    "done": done_points,
                    "percentage": int(done_points / total_points * 100),
                }

        return result

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_active_sprint_impl(
    board_id: int,
    client: "JiraClient | None" = None,
) -> dict[str, Any] | None:
    """Get the currently active sprint for a board."""
    if not board_id:
        raise ValidationError("Board ID is required")

    def _do_work(c: "JiraClient") -> dict[str, Any] | None:
        result = c.get_board_sprints(board_id, state="active")
        sprints = result.get("values", [])
        return sprints[0] if sprints else None

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _start_sprint_impl(
    sprint_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Start a sprint."""
    if not sprint_id:
        raise ValidationError("Sprint ID is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        update_data: dict[str, Any] = {"state": "active"}
        if start_date:
            update_data["start_date"] = _parse_date_safe(start_date)
        if end_date:
            update_data["end_date"] = _parse_date_safe(end_date)

        return c.update_sprint(sprint_id, **update_data)

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _close_sprint_impl(
    sprint_id: int,
    move_incomplete_to: int | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Close a sprint."""
    if not sprint_id:
        raise ValidationError("Sprint ID is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        result: dict[str, Any] = {}

        if move_incomplete_to:
            move_result = c.move_issues_to_sprint(sprint_id, move_incomplete_to)
            result["moved_issues"] = move_result.get("movedIssues", 0)

        update_data = {"state": "closed"}
        sprint_result = c.update_sprint(sprint_id, **update_data)
        result.update(sprint_result)

        return result

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _update_sprint_impl(
    sprint_id: int,
    name: str | None = None,
    goal: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Update sprint metadata."""
    if not sprint_id:
        raise ValidationError("Sprint ID is required")

    update_data: dict[str, Any] = {}
    if name:
        update_data["name"] = name
    if goal:
        update_data["goal"] = goal
    if start_date:
        update_data["start_date"] = _parse_date_safe(start_date)
    if end_date:
        update_data["end_date"] = _parse_date_safe(end_date)

    if not update_data:
        raise ValidationError("At least one field to update is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        return c.update_sprint(sprint_id, **update_data)

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _move_to_sprint_impl(
    sprint_id: int,
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    dry_run: bool = False,
    rank_position: str | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Move issues to a sprint."""
    if not sprint_id:
        raise ValidationError("Sprint ID is required")

    if not issue_keys and not jql:
        raise ValidationError("Either issue_keys or jql is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        issues_to_move = []

        if issue_keys:
            issues_to_move.extend([validate_issue_key(k) for k in issue_keys])

        if jql:
            search_result = c.search_issues(jql, max_results=1000)
            jql_issues = [issue["key"] for issue in search_result.get("issues", [])]
            issues_to_move.extend(jql_issues)

        if not issues_to_move:
            return {"moved": 0, "failed": 0, "message": "No issues to move"}

        if dry_run:
            return {"would_move": len(issues_to_move), "issues": issues_to_move}

        c.move_issues_to_sprint(sprint_id, issues_to_move, rank=rank_position)

        return {"moved": len(issues_to_move), "failed": 0}

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _move_to_backlog_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    dry_run: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Move issues to backlog."""
    if not issue_keys and not jql:
        raise ValidationError("Either issue_keys or jql is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        issues_to_move = []

        if issue_keys:
            issues_to_move.extend([validate_issue_key(k) for k in issue_keys])

        if jql:
            search_result = c.search_issues(jql, max_results=1000)
            jql_issues = [issue["key"] for issue in search_result.get("issues", [])]
            issues_to_move.extend(jql_issues)

        if not issues_to_move:
            return {"moved_to_backlog": 0, "message": "No issues to move"}

        if dry_run:
            return {
                "would_move_to_backlog": len(issues_to_move),
                "issues": issues_to_move,
            }

        c.move_issues_to_backlog(issues_to_move)

        return {"moved_to_backlog": len(issues_to_move)}

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


# =============================================================================
# Backlog/Rank Implementation Functions
# =============================================================================


def _get_backlog_impl(
    board_id: int | None = None,
    project_key: str | None = None,
    jql_filter: str | None = None,
    max_results: int = 100,
    group_by_epic: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Get backlog issues for a board."""
    if not board_id and not project_key:
        raise ValidationError("Either board_id or project_key is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        actual_board_id = board_id
        if not actual_board_id and project_key:
            actual_board_id = _get_board_id_for_project(project_key, client=c)

        agile_fields = get_agile_fields()
        epic_link_field = agile_fields["epic_link"]

        result = c.get_board_backlog(
            actual_board_id, jql=jql_filter, max_results=max_results
        )
        result["_agile_fields"] = agile_fields

        if group_by_epic:
            by_epic: dict[str, list] = {}
            no_epic: list = []
            for issue in result.get("issues", []):
                epic_key = issue["fields"].get(epic_link_field)
                if epic_key:
                    if epic_key not in by_epic:
                        by_epic[epic_key] = []
                    by_epic[epic_key].append(issue)
                else:
                    no_epic.append(issue)
            result["by_epic"] = by_epic
            result["no_epic"] = no_epic

        return result

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _rank_issue_impl(
    issue_keys: list[str],
    before_key: str | None = None,
    after_key: str | None = None,
    position: str | None = None,
    board_id: int | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Rank issues in the backlog."""
    if not issue_keys:
        raise ValidationError("At least one issue key is required")

    if not before_key and not after_key and not position:
        raise ValidationError(
            "Must specify before_key, after_key, or position (top/bottom)"
        )

    validated_keys = [validate_issue_key(k) for k in issue_keys]

    validated_before = validate_issue_key(before_key) if before_key else None
    validated_after = validate_issue_key(after_key) if after_key else None

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        if validated_before:
            c.rank_issues(validated_keys, rank_before=validated_before)
        elif validated_after:
            c.rank_issues(validated_keys, rank_after=validated_after)
        elif position in ("top", "bottom"):
            raise ValidationError(
                "Top/bottom ranking requires implementation with board context"
            )

        return {"ranked": len(validated_keys), "issues": validated_keys}

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


# =============================================================================
# Estimation Implementation Functions
# =============================================================================


def _estimate_issue_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    points: float | None = None,
    validate_fibonacci: bool = False,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Set story points on issues."""
    if not issue_keys and not jql:
        raise ValidationError("Either issue keys or JQL query is required")

    if points is None:
        raise ValidationError("Story points value is required")

    if validate_fibonacci and points not in FIBONACCI_SEQUENCE:
        raise ValidationError(
            f"Points {points} is not a valid Fibonacci value. Valid values: {FIBONACCI_SEQUENCE}"
        )

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        keys_to_update = issue_keys
        if jql and not keys_to_update:
            search_result = c.search_issues(jql)
            keys_to_update = [issue["key"] for issue in search_result.get("issues", [])]

        if not keys_to_update:
            return {"updated": 0, "issues": []}

        validated_keys = [validate_issue_key(k) for k in keys_to_update]
        story_points_field = get_agile_field("story_points")
        points_value = None if points == 0 else points

        updated = 0
        for key in validated_keys:
            c.update_issue(key, {story_points_field: points_value})
            updated += 1

        return {"updated": updated, "issues": validated_keys, "points": points}

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_estimates_impl(
    sprint_id: int | None = None,
    project_key: str | None = None,
    epic_key: str | None = None,
    group_by: str | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Get story point estimation summary."""
    if not sprint_id and not project_key and not epic_key:
        raise ValidationError("Either sprint_id, project_key, or epic_key is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        nonlocal sprint_id, epic_key
        sprint_name = None

        if project_key and not sprint_id:
            validate_project_key(project_key)
            result = c.get_all_boards(project_key=project_key, max_results=10)
            boards = result.get("values", [])
            if not boards:
                raise ValidationError(f"No boards found for project {project_key}")

            scrum_boards = [b for b in boards if b.get("type") == "scrum"]
            board_id = scrum_boards[0]["id"] if scrum_boards else boards[0]["id"]

            sprints_result = c.get_board_sprints(board_id, state="active")
            sprints = sprints_result.get("values", [])
            if not sprints:
                raise ValidationError(
                    f"No active sprints found for project {project_key}"
                )

            sprint = sprints[0]
            sprint_id = sprint["id"]
            sprint_name = sprint["name"]

        agile_fields = get_agile_fields()
        story_points_field = agile_fields["story_points"]

        if sprint_id:
            result = c.get_sprint_issues(sprint_id)
            issues = result.get("issues", [])
        else:
            # epic_key must be set since we checked above
            assert epic_key is not None
            epic_key = validate_issue_key(epic_key)
            jql = f'"Epic Link" = {epic_key}'
            result = c.search_issues(
                jql, fields=["summary", "status", "assignee", story_points_field]
            )
            issues = result.get("issues", [])

        total_points = 0
        by_status: dict[str, float] = defaultdict(float)
        by_assignee: dict[str, float] = defaultdict(float)

        for issue in issues:
            fields = issue.get("fields", {})
            pts = fields.get(story_points_field) or 0
            total_points += pts

            status = fields.get("status", {}).get("name", "Unknown")
            by_status[status] += pts

            assignee = fields.get("assignee")
            assignee_name = (
                assignee.get("displayName", "Unknown") if assignee else "Unassigned"
            )
            by_assignee[assignee_name] += pts

        response: dict[str, Any] = {
            "total_points": total_points,
            "issue_count": len(issues),
            "by_status": dict(by_status),
            "by_assignee": dict(by_assignee),
        }

        if sprint_id:
            response["sprint_id"] = sprint_id
        if sprint_name:
            response["sprint_name"] = sprint_name
        if project_key:
            response["project_key"] = project_key
        if epic_key:
            response["epic_key"] = epic_key

        return response

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _get_velocity_impl(
    board_id: int | None = None,
    project_key: str | None = None,
    num_sprints: int = 3,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Calculate velocity from completed sprints."""
    if not board_id and not project_key:
        raise ValidationError("Either board_id or project_key is required")

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        actual_board_id = board_id
        board_name = None

        if project_key and not board_id:
            validate_project_key(project_key)
            board = _get_board_for_project(project_key, client=c)
            if not board:
                raise ValidationError(
                    f"No board found for project {project_key}. "
                    "Ensure the project has a Scrum board configured."
                )
            actual_board_id = board["id"]
            board_name = board.get("name")

        result = c.get_board_sprints(
            actual_board_id, state="closed", max_results=num_sprints
        )
        sprints = result.get("values", [])

        if not sprints:
            raise ValidationError(
                "No closed sprints found. Velocity requires completed sprints."
            )

        sorted_sprints = sorted(
            sprints, key=lambda s: s.get("endDate", ""), reverse=True
        )[:num_sprints]

        agile_fields = get_agile_fields()
        story_points_field = agile_fields["story_points"]

        sprint_data = []
        for sprint in sorted_sprints:
            sp_id = sprint["id"]
            sprint_name_val = sprint.get("name", f"Sprint {sp_id}")

            jql = f"sprint = {sp_id} AND status = Done"
            search_result = c.search_issues(
                jql, fields=["summary", "status", story_points_field], max_results=200
            )
            issues = search_result.get("issues", [])

            completed_points = 0
            completed_count = 0
            for issue in issues:
                fields = issue.get("fields", {})
                points = fields.get(story_points_field) or 0
                completed_points += points
                completed_count += 1

            sprint_data.append(
                {
                    "sprint_id": sp_id,
                    "sprint_name": sprint_name_val,
                    "completed_points": completed_points,
                    "completed_issues": completed_count,
                    "start_date": (
                        sprint.get("startDate", "")[:10]
                        if sprint.get("startDate")
                        else None
                    ),
                    "end_date": (
                        sprint.get("endDate", "")[:10]
                        if sprint.get("endDate")
                        else None
                    ),
                }
            )

        velocities = [s["completed_points"] for s in sprint_data]
        avg_velocity = mean(velocities) if velocities else 0
        velocity_stdev = stdev(velocities) if len(velocities) > 1 else 0
        min_velocity = min(velocities) if velocities else 0
        max_velocity = max(velocities) if velocities else 0
        total_pts = sum(velocities)

        return {
            "project_key": project_key,
            "board_id": actual_board_id,
            "board_name": board_name,
            "sprints_analyzed": len(sprint_data),
            "average_velocity": round(avg_velocity, 1),
            "velocity_stdev": round(velocity_stdev, 1),
            "min_velocity": min_velocity,
            "max_velocity": max_velocity,
            "total_points": total_pts,
            "sprints": sprint_data,
        }

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


def _create_subtask_impl(
    parent_key: str,
    summary: str,
    description: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    time_estimate: str | None = None,
    custom_fields: dict | None = None,
    client: "JiraClient | None" = None,
) -> dict[str, Any]:
    """Create a subtask under a parent issue."""
    if not parent_key:
        raise ValidationError("Parent key is required")
    if not summary:
        raise ValidationError("Summary is required")

    validated_parent_key = validate_issue_key(parent_key)

    def _do_work(c: "JiraClient") -> dict[str, Any]:
        parent = c.get_issue(validated_parent_key)

        if parent["fields"]["issuetype"].get("subtask", False):
            raise ValidationError(
                f"{validated_parent_key} is a subtask and cannot have subtasks"
            )

        project_key = parent["fields"]["project"]["key"]

        issue_types = c.get("/rest/api/3/issuetype")
        subtask_type = None
        for itype in issue_types:
            if itype.get("subtask", False):
                subtask_type = itype["name"]
                break

        if not subtask_type:
            raise ValidationError("No subtask issue type found in JIRA instance")

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "parent": {"key": validated_parent_key},
            "issuetype": {"name": subtask_type},
            "summary": summary,
        }

        if description:
            fields["description"] = _convert_description_to_adf(description)

        if priority:
            fields["priority"] = {"name": priority}

        if assignee:
            if assignee.lower() == "self":
                account_id = c.get_current_user_id()
                fields["assignee"] = {"accountId": account_id}
            elif "@" in assignee:
                fields["assignee"] = {"emailAddress": assignee}
            else:
                fields["assignee"] = {"accountId": assignee}

        if labels:
            fields["labels"] = labels

        if time_estimate:
            fields["timetracking"] = {"originalEstimate": time_estimate}

        if custom_fields:
            fields.update(custom_fields)

        return c.create_issue(fields)

    if client is not None:
        return _do_work(client)

    with get_jira_client() as c:
        return _do_work(c)


# =============================================================================
# Formatting Functions
# =============================================================================


def _format_epic_created(result: dict, epic_name: str | None) -> str:
    """Format epic creation result."""
    lines = [f"Created epic: {result.get('key')}"]
    if epic_name:
        lines.append(f"Epic Name: {epic_name}")
    base_url = result.get("self", "").split("/rest/api/")[0]
    if base_url:
        lines.append(f"URL: {base_url}/browse/{result.get('key')}")
    return "\n".join(lines)


def _format_epic_details(epic_data: dict) -> str:
    """Format epic details."""
    agile_fields = epic_data.get("_agile_fields", {})
    epic_name_field = agile_fields.get("epic_name", "customfield_10011")

    lines = [f"Epic: {epic_data['key']}"]
    lines.append(f"Summary: {epic_data['fields']['summary']}")

    epic_name = epic_data["fields"].get(epic_name_field)
    if epic_name:
        lines.append(f"Epic Name: {epic_name}")

    status = epic_data["fields"]["status"]["name"]
    lines.append(f"Status: {status}")

    if "progress" in epic_data:
        prog = epic_data["progress"]
        lines.append(
            f"Progress: {prog['done']}/{prog['total']} issues ({prog['percentage']}%)"
        )

    if "story_points" in epic_data:
        sp = epic_data["story_points"]
        lines.append(f"Story Points: {sp['done']}/{sp['total']} ({sp['percentage']}%)")

    if epic_data.get("children"):
        lines.append("")
        lines.append("Children:")
        for child in epic_data["children"]:
            status = child["fields"]["status"]["name"]
            summary = child["fields"]["summary"]
            lines.append(f"  {child['key']} [{status}] - {summary}")

    return "\n".join(lines)


def _format_sprint_list(data: dict) -> str:
    """Format sprint list."""
    sprints = data.get("sprints", [])
    board = data.get("board", {})
    state_filter = data.get("state_filter")

    lines = []
    board_name = board.get("name", f"Board {board.get('id', 'Unknown')}")
    if state_filter:
        lines.append(f"Sprints for {board_name} (state: {state_filter}):")
    else:
        lines.append(f"Sprints for {board_name}:")
    lines.append("")

    if not sprints:
        lines.append("  No sprints found.")
        return "\n".join(lines)

    lines.append(f"{'ID':<8} {'State':<10} {'Name':<30} {'Dates'}")
    lines.append("-" * 80)

    for sprint in sprints:
        sprint_id = sprint.get("id", "")
        state = sprint.get("state", "unknown")
        name = sprint.get("name", "Unnamed")
        if len(name) > 28:
            name = name[:25] + "..."

        start_date = sprint.get("startDate", "")
        end_date = sprint.get("endDate", "")
        dates = ""
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                dates = f"{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
            except (ValueError, TypeError):
                dates = f"{start_date[:10]} → {end_date[:10]}"

        lines.append(f"{sprint_id:<8} {state:<10} {name:<30} {dates}")

    lines.append("")
    lines.append(f"Total: {len(sprints)} sprint(s)")

    return "\n".join(lines)


def _format_sprint_details(sprint_data: dict) -> str:
    """Format sprint details."""
    story_points_field = sprint_data.get("_story_points_field", "customfield_10016")

    lines = [f"Sprint: {sprint_data.get('name', 'Unknown')}"]
    lines.append(f"State: {sprint_data.get('state', 'unknown')}")

    start_date = sprint_data.get("startDate")
    end_date = sprint_data.get("endDate")
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            now = datetime.now(start.tzinfo)

            if end > now:
                days_remaining = (end - now).days
                lines.append(
                    f"Dates: {start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')} ({days_remaining} days remaining)"
                )
            else:
                lines.append(
                    f"Dates: {start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')}"
                )
        except (ValueError, TypeError):
            lines.append(f"Dates: {start_date} -> {end_date}")

    goal = sprint_data.get("goal")
    if goal:
        lines.append(f"Goal: {goal}")

    if "progress" in sprint_data:
        prog = sprint_data["progress"]
        lines.append(
            f"Progress: {prog['done']}/{prog['total']} issues ({prog['percentage']}%)"
        )

    if "story_points" in sprint_data:
        sp = sprint_data["story_points"]
        lines.append(f"Story Points: {sp['done']}/{sp['total']} ({sp['percentage']}%)")

    if sprint_data.get("issues"):
        lines.append("")
        lines.append("Issues:")
        for issue in sprint_data["issues"]:
            status = issue["fields"]["status"]["name"]
            summary = issue["fields"]["summary"]
            points = issue["fields"].get(story_points_field)
            points_str = f" ({points} pts)" if points else ""
            lines.append(f"  [{status}] {issue['key']} - {summary}{points_str}")

    return "\n".join(lines)


def _format_velocity(data: dict) -> str:
    """Format velocity report."""
    lines = []
    project = data.get("project_key") or f"Board {data.get('board_id')}"
    lines.append(f"Velocity Report: {project}")
    lines.append("=" * 60)
    lines.append("")

    lines.append("Summary:")
    lines.append(f"  Average Velocity: {data['average_velocity']} points/sprint")
    lines.append(f"  Range: {data['min_velocity']} - {data['max_velocity']} points")
    if data["velocity_stdev"] > 0:
        lines.append(f"  Std Dev: {data['velocity_stdev']} points")
    lines.append(f"  Sprints Analyzed: {data['sprints_analyzed']}")
    lines.append("")

    lines.append("Sprint Breakdown:")
    lines.append(f"{'Sprint':<30} {'Points':>8} {'Issues':>8} {'Dates'}")
    lines.append("-" * 70)

    for sprint in data["sprints"]:
        name = sprint["sprint_name"]
        if len(name) > 28:
            name = name[:25] + "..."
        points = sprint["completed_points"]
        issues = sprint["completed_issues"]
        dates = ""
        if sprint.get("start_date") and sprint.get("end_date"):
            dates = f"{sprint['start_date']} → {sprint['end_date']}"
        lines.append(f"{name:<30} {points:>8} {issues:>8} {dates}")

    lines.append("-" * 70)
    lines.append(f"{'Total':<30} {data['total_points']:>8}")

    return "\n".join(lines)


# =============================================================================
# Click Commands
# =============================================================================


@click.group()
def agile():
    """Commands for Agile/Scrum workflows (epics, sprints, backlog)."""
    pass


# --- Epic Commands ---


@agile.group()
def epic():
    """Manage epics."""
    pass


@epic.command(name="create")
@click.option("--project", "-p", required=True, help="Project key")
@click.option("--summary", "-s", required=True, help="Epic summary (title)")
@click.option("--epic-name", "-n", help="Epic Name field value")
@click.option("--description", "-d", help="Epic description")
@click.option("--priority", help="Priority")
@click.option("--assignee", "-a", help="Assignee (account ID, email, or 'self')")
@click.option("--labels", "-l", help="Comma-separated labels")
@click.option("--color", "-c", type=click.Choice(VALID_EPIC_COLORS), help="Epic color")
@click.option("--custom-fields", help="Custom fields as JSON string")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def epic_create(
    ctx,
    project,
    summary,
    epic_name,
    description,
    priority,
    assignee,
    labels,
    color,
    custom_fields,
    output,
):
    """Create a new epic."""
    labels_list = parse_comma_list(labels)
    custom = parse_json_arg(custom_fields)

    client = get_client_from_context(ctx)
    result = _create_epic_impl(
        project=project,
        summary=summary,
        description=description,
        epic_name=epic_name,
        color=color,
        priority=priority,
        assignee=assignee,
        labels=labels_list,
        custom_fields=custom,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_epic_created(result, epic_name))


@epic.command(name="get")
@click.argument("epic_key")
@click.option(
    "--with-children",
    "-c",
    is_flag=True,
    help="Fetch child issues and calculate progress",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def epic_get(ctx, epic_key, with_children, output):
    """Get epic details."""
    client = get_client_from_context(ctx)
    result = _get_epic_impl(epic_key, with_children=with_children, client=client)

    if output == "json":
        output_data = {k: v for k, v in result.items() if not k.startswith("_")}
        click.echo(format_json(output_data))
    else:
        click.echo(_format_epic_details(result))


@epic.command(name="add-issues")
@click.option(
    "--epic", "-e", "epic_key", required=True, help="Epic key (e.g., PROJ-100)"
)
@click.option("--issues", "-i", help="Comma-separated issue keys")
@click.option("--jql", "-j", help="JQL query to find issues")
@click.option("--dry-run", "-n", is_flag=True, help="Preview without making changes")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def epic_add_issues(ctx, epic_key, issues, jql, dry_run, output):
    """Add issues to an epic."""
    if not issues and not jql:
        raise click.UsageError("Either --issues or --jql is required")
    if issues and jql:
        raise click.UsageError("--issues and --jql are mutually exclusive")

    issue_list = parse_comma_list(issues) or []

    client = get_client_from_context(ctx)
    if jql:
        jql_results = client.search_issues(jql)
        jql_keys = [issue["key"] for issue in jql_results.get("issues", [])]
        issue_list.extend(jql_keys)

    result = _add_to_epic_impl(
        epic_key=epic_key, issue_keys=issue_list, dry_run=dry_run, client=client
    )

    if output == "json":
        click.echo(format_json(result))
    elif dry_run:
        click.echo(f"Would add {result.get('would_add', 0)} issues to epic {epic_key}")
    else:
        click.echo(f"Added {result['added']} issues to epic {epic_key}")
        if result["failed"] > 0:
            click.echo(f"Failed: {result['failed']}")
            for failure in result["failures"]:
                click.echo(f"  - {failure['issue']}: {failure['error']}")


# --- Sprint Commands ---


@agile.group()
def sprint():
    """Manage sprints."""
    pass


@sprint.command(name="list")
@click.option("--board", "-b", type=int, help="Board ID")
@click.option("--project", "-p", help="Project key (will find board automatically)")
@click.option(
    "--state",
    "-s",
    type=click.Choice(["active", "closed", "future"]),
    help="Filter by sprint state",
)
@click.option("--max-results", "-m", type=int, default=50, help="Maximum sprints")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def sprint_list(ctx, board, project, state, max_results, output):
    """List sprints for a board or project."""
    if not board and not project:
        raise click.UsageError("Either --board or --project is required")
    if board and project:
        raise click.UsageError("--board and --project are mutually exclusive")

    client = get_client_from_context(ctx)
    result = _list_sprints_impl(
        board_id=board,
        project_key=project,
        state=state,
        max_results=max_results,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_sprint_list(result))


@sprint.command(name="create")
@click.option("--board", "-b", "board_id", type=int, required=True, help="Board ID")
@click.option("--name", "-n", required=True, help="Sprint name")
@click.option("--goal", "-g", help="Sprint goal")
@click.option("--start-date", "-s", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", "-e", help="End date (YYYY-MM-DD)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def sprint_create(ctx, board_id, name, goal, start_date, end_date, output):
    """Create a new sprint."""
    client = get_client_from_context(ctx)
    result = _create_sprint_impl(
        board_id=board_id,
        name=name,
        goal=goal,
        start_date=start_date,
        end_date=end_date,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"Created sprint: {result.get('name')} (ID: {result.get('id')})")
        if goal:
            click.echo(f"Goal: {goal}")
        if start_date and end_date:
            click.echo(f"Duration: {start_date} to {end_date}")
        click.echo(f"State: {result.get('state', 'future')}")


@sprint.command(name="get")
@click.argument("sprint_id", type=int, required=False)
@click.option("--board", "-b", type=int, help="Board ID (use with --active)")
@click.option("--active", "-a", is_flag=True, help="Get active sprint for board")
@click.option("--include-issues", "-i", is_flag=True, help="Include issues in sprint")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def sprint_get(ctx, sprint_id, board, active, include_issues, output):
    """Get sprint details."""
    client = get_client_from_context(ctx)
    if active:
        if not board:
            raise click.UsageError("--board is required with --active")
        if sprint_id:
            raise click.UsageError("Cannot specify both SPRINT_ID and --active")
        result = _get_active_sprint_impl(board, client=client)
        if not result:
            click.echo("No active sprint found for this board")
            return
    elif not sprint_id:
        raise click.UsageError("SPRINT_ID is required (or use --board with --active)")
    else:
        result = _get_sprint_impl(sprint_id, with_issues=include_issues, client=client)

    if output == "json":
        output_data = {k: v for k, v in result.items() if not k.startswith("_")}
        click.echo(format_json(output_data))
    else:
        click.echo(_format_sprint_details(result))


@sprint.command(name="manage")
@click.option(
    "--sprint", "-s", "sprint_id", type=int, required=True, help="Sprint ID to manage"
)
@click.option("--start", "do_start", is_flag=True, help="Start the sprint")
@click.option("--close", "do_close", is_flag=True, help="Close the sprint")
@click.option("--name", "-n", help="Update sprint name")
@click.option("--goal", "-g", help="Update sprint goal")
@click.option(
    "--move-incomplete-to",
    type=int,
    help="Sprint ID to move incomplete issues to (with --close)",
)
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def sprint_manage(
    ctx,
    sprint_id,
    do_start,
    do_close,
    name,
    goal,
    move_incomplete_to,
    start_date,
    end_date,
    output,
):
    """Manage sprint lifecycle (start, close, update)."""
    client = get_client_from_context(ctx)
    if do_start:
        result = _start_sprint_impl(
            sprint_id, start_date=start_date, end_date=end_date, client=client
        )
        if output == "json":
            click.echo(format_json(result))
        else:
            click.echo(f"Started sprint: {result['name']}")
    elif do_close:
        result = _close_sprint_impl(
            sprint_id, move_incomplete_to=move_incomplete_to, client=client
        )
        if output == "json":
            click.echo(format_json(result))
        else:
            click.echo(f"Closed sprint: {result['name']}")
            if "moved_issues" in result:
                click.echo(
                    f"Moved {result['moved_issues']} incomplete issues to next sprint"
                )
    elif name or goal or start_date or end_date:
        result = _update_sprint_impl(
            sprint_id,
            name=name,
            goal=goal,
            start_date=start_date,
            end_date=end_date,
            client=client,
        )
        if output == "json":
            click.echo(format_json(result))
        else:
            click.echo(f"Updated sprint: {result['name']}")
    else:
        raise click.UsageError(
            "No action specified. Use --start, --close, or update options."
        )


@sprint.command(name="move-issues")
@click.option("--sprint", "-s", type=int, help="Target sprint ID")
@click.option("--backlog", "-b", is_flag=True, help="Move to backlog instead of sprint")
@click.option("--issues", "-i", help="Comma-separated issue keys")
@click.option("--jql", "-j", help="JQL query to find issues")
@click.option("--dry-run", "-n", is_flag=True, help="Preview without making changes")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def sprint_move_issues(ctx, sprint, backlog, issues, jql, dry_run, output):
    """Move issues to a sprint or backlog."""
    if not sprint and not backlog:
        raise click.UsageError("Either --sprint or --backlog is required")
    if sprint and backlog:
        raise click.UsageError("--sprint and --backlog are mutually exclusive")
    if not issues and not jql:
        raise click.UsageError("Either --issues or --jql is required")
    if issues and jql:
        raise click.UsageError("--issues and --jql are mutually exclusive")

    issue_list = parse_comma_list(issues)

    client = get_client_from_context(ctx)
    if backlog:
        result = _move_to_backlog_impl(
            issue_keys=issue_list, jql=jql, dry_run=dry_run, client=client
        )
        if output == "json":
            click.echo(format_json(result))
        elif dry_run:
            click.echo(
                f"Would move {result.get('would_move_to_backlog', 0)} issues to backlog"
            )
        else:
            click.echo(f"Moved {result['moved_to_backlog']} issues to backlog")
    else:
        result = _move_to_sprint_impl(
            sprint_id=sprint,
            issue_keys=issue_list,
            jql=jql,
            dry_run=dry_run,
            client=client,
        )
        if output == "json":
            click.echo(format_json(result))
        elif dry_run:
            click.echo(
                f"Would move {result.get('would_move', 0)} issues to sprint {sprint}"
            )
        else:
            click.echo(f"Moved {result['moved']} issues to sprint {sprint}")


# --- Other Agile Commands ---


@agile.command(name="backlog")
@click.option("--board", "-b", type=int, help="Board ID")
@click.option("--project", "-p", help="Project key (alternative to --board)")
@click.option("--filter", "-f", "jql_filter", help="JQL filter")
@click.option("--max-results", "-m", type=int, default=100, help="Maximum results")
@click.option("--group-by", type=click.Choice(["epic"]), help="Group results")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_backlog(ctx, board, project, jql_filter, max_results, group_by, output):
    """Get backlog issues for a board."""
    if not board and not project:
        raise click.UsageError("Either --board or --project is required")
    if board and project:
        raise click.UsageError("--board and --project are mutually exclusive")

    client = get_client_from_context(ctx)
    result = _get_backlog_impl(
        board_id=board,
        project_key=project,
        jql_filter=jql_filter,
        max_results=max_results,
        group_by_epic=(group_by == "epic"),
        client=client,
    )

    if output == "json":
        output_data = {k: v for k, v in result.items() if not k.startswith("_")}
        click.echo(format_json(output_data))
    else:
        issues = result.get("issues", [])
        story_points_field = result.get("_agile_fields", {}).get(
            "story_points", "customfield_10016"
        )
        click.echo(f"Backlog: {len(issues)}/{result.get('total', len(issues))} issues")

        if group_by == "epic" and "by_epic" in result:
            for epic_key, epic_issues in result["by_epic"].items():
                click.echo(f"\n[{epic_key}] ({len(epic_issues)} issues)")
                for issue in epic_issues:
                    points = issue["fields"].get(story_points_field, "")
                    pts_str = f" ({points} pts)" if points else ""
                    click.echo(
                        f"  {issue['key']} - {issue['fields']['summary']}{pts_str}"
                    )
            if result.get("no_epic"):
                click.echo(f"\n[No Epic] ({len(result['no_epic'])} issues)")
                for issue in result["no_epic"]:
                    click.echo(f"  {issue['key']} - {issue['fields']['summary']}")
        else:
            for issue in issues:
                status = issue["fields"]["status"]["name"]
                summary = issue["fields"]["summary"]
                points = issue["fields"].get(story_points_field, "")
                pts_str = f" ({points} pts)" if points else ""
                click.echo(f"  [{status}] {issue['key']} - {summary}{pts_str}")


@agile.command(name="rank")
@click.argument("issue_key")
@click.option("--before", "-b", help="Rank before this issue")
@click.option("--after", "-a", help="Rank after this issue")
@click.option("--top", is_flag=True, help="Move to top of backlog")
@click.option("--bottom", is_flag=True, help="Move to bottom of backlog")
@click.option("--board", type=int, help="Board ID (required for --top/--bottom)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_rank(ctx, issue_key, before, after, top, bottom, board, output):
    """Rank an issue in the backlog."""
    position_count = sum([bool(before), bool(after), top, bottom])
    if position_count == 0:
        raise click.UsageError(
            "Must specify one of: --before, --after, --top, or --bottom"
        )
    if position_count > 1:
        raise click.UsageError(
            "--before, --after, --top, and --bottom are mutually exclusive"
        )
    if (top or bottom) and not board:
        raise click.UsageError("--board is required with --top or --bottom")

    position = "top" if top else ("bottom" if bottom else None)

    client = get_client_from_context(ctx)
    result = _rank_issue_impl(
        issue_keys=[issue_key],
        before_key=before,
        after_key=after,
        position=position,
        board_id=board,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"Ranked {result['ranked']} issue(s)")
        if before:
            click.echo(f"Position: before {before}")
        elif after:
            click.echo(f"Position: after {after}")


@agile.command(name="estimate")
@click.argument("issue_key")
@click.option("--points", "-p", type=float, required=True, help="Story points value")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_estimate(ctx, issue_key, points, output):
    """Set story points for an issue."""
    client = get_client_from_context(ctx)
    result = _estimate_issue_impl(issue_keys=[issue_key], points=points, client=client)

    if output == "json":
        click.echo(format_json(result))
    else:
        pts_str = "cleared" if points == 0 else f"set to {points}"
        click.echo(f"Updated {result['updated']} issue(s)")
        click.echo(f"Story points: {pts_str}")


@agile.command(name="estimates")
@click.option("--sprint", "-s", type=int, help="Sprint ID")
@click.option("--project", "-p", help="Project key (finds active sprint)")
@click.option("--epic", "-e", help="Epic key")
@click.option(
    "--group-by", "-g", type=click.Choice(["assignee", "status"]), help="Group results"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_estimates(ctx, sprint, project, epic, group_by, output):
    """Get story point estimates for a sprint, project, or epic."""
    if not sprint and not project and not epic:
        raise click.UsageError("One of --sprint, --project, or --epic is required")

    provided = sum(1 for opt in [sprint, project, epic] if opt)
    if provided > 1:
        raise click.UsageError("--sprint, --project, and --epic are mutually exclusive")

    client = get_client_from_context(ctx)
    result = _get_estimates_impl(
        sprint_id=sprint,
        project_key=project,
        epic_key=epic,
        group_by=group_by,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        if project:
            sprint_name = result.get("sprint_name", f"Sprint {result.get('sprint_id')}")
            click.echo(f"Project {project} - {sprint_name} Estimates")
        elif sprint:
            click.echo(f"Sprint {sprint} Estimates")
        else:
            click.echo(f"Epic {epic} Estimates")

        click.echo(
            f"Total: {result['total_points']} points ({result['issue_count']} issues)"
        )

        if result["by_status"]:
            total = result["total_points"] or 1
            click.echo("\nBy Status:")
            for status, points in sorted(result["by_status"].items()):
                pct = (points / total) * 100 if total > 0 else 0
                click.echo(f"  {status}: {points} points ({pct:.0f}%)")

        if group_by == "assignee" and result["by_assignee"]:
            total = result["total_points"] or 1
            click.echo("\nBy Assignee:")
            for assignee, points in sorted(
                result["by_assignee"].items(), key=lambda x: -x[1]
            ):
                pct = (points / total) * 100 if total > 0 else 0
                click.echo(f"  {assignee}: {points} points ({pct:.0f}%)")


@agile.command(name="velocity")
@click.option("--board", "-b", type=int, help="Board ID")
@click.option("--project", "-p", help="Project key (will find board automatically)")
@click.option(
    "--sprints",
    "-n",
    type=int,
    default=3,
    help="Number of closed sprints to analyze (default: 3)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_velocity(ctx, board, project, sprints, output):
    """Calculate velocity from completed sprints."""
    if not board and not project:
        raise click.UsageError("Either --board or --project is required")
    if board and project:
        raise click.UsageError("--board and --project are mutually exclusive")

    client = get_client_from_context(ctx)
    result = _get_velocity_impl(
        board_id=board, project_key=project, num_sprints=sprints, client=client
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_velocity(result))
        click.echo(
            f"\nVelocity: {result['average_velocity']} points/sprint (based on {result['sprints_analyzed']} sprints)"
        )


@agile.command(name="subtask")
@click.option("--parent", "-p", required=True, help="Parent issue key (e.g., PROJ-101)")
@click.option("--summary", "-s", required=True, help="Subtask summary")
@click.option("--description", "-d", help="Subtask description")
@click.option("--assignee", "-a", help="Assignee (account ID, email, or 'self')")
@click.option("--estimate", "-e", help="Time estimate (e.g., 4h, 2d, 1w)")
@click.option("--priority", help="Priority (Highest, High, Medium, Low, Lowest)")
@click.option("--labels", "-l", help="Comma-separated labels")
@click.option("--custom-fields", help="Custom fields as JSON string")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@handle_jira_errors
def agile_subtask(
    ctx,
    parent,
    summary,
    description,
    assignee,
    estimate,
    priority,
    labels,
    custom_fields,
    output,
):
    """Create a subtask under a parent issue."""
    labels_list = parse_comma_list(labels)
    custom = parse_json_arg(custom_fields)

    client = get_client_from_context(ctx)
    result = _create_subtask_impl(
        parent_key=parent,
        summary=summary,
        description=description,
        assignee=assignee,
        priority=priority,
        labels=labels_list,
        time_estimate=estimate,
        custom_fields=custom,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"Created subtask: {result.get('key')}")
        click.echo(f"Parent: {parent}")
        if estimate:
            click.echo(f"Estimate: {estimate}")
        base_url = result.get("self", "").split("/rest/api/")[0]
        if base_url:
            click.echo(f"URL: {base_url}/browse/{result.get('key')}")
