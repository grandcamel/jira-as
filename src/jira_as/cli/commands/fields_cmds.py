"""
CLI commands for managing JIRA custom fields.

This module contains all logic for jira-fields operations.
All implementation functions are inlined for direct CLI usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from jira_as import JiraError, ValidationError, get_jira_client

from ..cli_utils import format_json, get_client_from_context, handle_jira_errors

if TYPE_CHECKING:
    from jira_as import JiraClient

# =============================================================================
# Constants
# =============================================================================

# Known Agile field name patterns
AGILE_PATTERNS = ["epic", "sprint", "story", "point", "rank", "velocity", "backlog"]

# Agile field patterns and expected fields
AGILE_FIELDS = {
    "sprint": ["sprint"],
    "story_points": ["story point", "story points", "story point estimate"],
    "epic_link": ["epic link"],
    "epic_name": ["epic name"],
    "rank": ["rank"],
}

# Field type mappings
FIELD_TYPES = {
    "text": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
    },
    "textarea": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
    },
    "number": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:float",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:exactnumber",
    },
    "date": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:datepicker",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:daterange",
    },
    "datetime": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:datetime",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:datetimerange",
    },
    "select": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:select",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
    },
    "multiselect": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:multiselect",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
    },
    "checkbox": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
    },
    "radio": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:radiobuttons",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
    },
    "url": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:url",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:exacttextsearcher",
    },
    "user": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:userpicker",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:userpickergroupsearcher",
    },
    "labels": {
        "type": "com.atlassian.jira.plugin.system.customfieldtypes:labels",
        "searcher": "com.atlassian.jira.plugin.system.customfieldtypes:labelsearcher",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================


def _find_agile_fields(client) -> dict[str, str | None]:
    """Find Agile field IDs in the instance."""
    fields = client.get("/rest/api/3/field")

    agile_fields: dict[str, str | None] = {
        "story_points": None,
        "epic_link": None,
        "sprint": None,
        "epic_name": None,
    }

    for field in fields:
        name = field.get("name", "").lower()
        fid = field.get("id", "")

        if "story point" in name and agile_fields["story_points"] is None:
            agile_fields["story_points"] = fid
        elif "epic link" in name and agile_fields["epic_link"] is None:
            agile_fields["epic_link"] = fid
        elif name == "sprint" and agile_fields["sprint"] is None:
            agile_fields["sprint"] = fid
        elif "epic name" in name and agile_fields["epic_name"] is None:
            agile_fields["epic_name"] = fid

    return agile_fields


def _find_project_screens(client, project_key: str) -> list[dict[str, Any]]:
    """Find screens used by a project."""
    project = client.get(f"/rest/api/3/project/{project_key}")
    project_id = project.get("id")

    schemes = client.get(
        "/rest/api/3/issuetypescreenscheme/project", params={"projectId": project_id}
    )

    screens = []

    if not schemes.get("values"):
        all_screens = client.get("/rest/api/3/screens")
        for screen in all_screens.get("values", []):
            if "Default" in screen.get("name", ""):
                screens.append({"id": screen.get("id"), "name": screen.get("name")})
        return screens

    for scheme_mapping in schemes.get("values", []):
        scheme = scheme_mapping.get("issueTypeScreenScheme", {})
        scheme_id = scheme.get("id")

        items = client.get(f"/rest/api/3/issuetypescreenscheme/{scheme_id}/mapping")

        for item in items.get("values", []):
            screen_scheme_id = item.get("screenSchemeId")
            if screen_scheme_id:
                screen_scheme = client.get(
                    f"/rest/api/3/screenscheme/{screen_scheme_id}"
                )

                for operation, screen_id in screen_scheme.get("screens", {}).items():
                    if screen_id:
                        try:
                            screen = client.get(f"/rest/api/3/screens/{screen_id}")
                            screens.append(
                                {
                                    "id": screen.get("id"),
                                    "name": screen.get("name"),
                                    "operation": operation,
                                }
                            )
                        except JiraError:
                            pass

    return screens


def _add_field_to_screen(
    client, screen_id: int, field_id: str, dry_run: bool = False
) -> bool:
    """Add a field to a screen."""
    if dry_run:
        return True

    tabs = client.get(f"/rest/api/3/screens/{screen_id}/tabs")
    if not tabs:
        return False

    tab_id = tabs[0].get("id")

    fields = client.get(f"/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields")
    for f in fields:
        if f.get("id") == field_id:
            return True  # Already present

    try:
        client.post(
            f"/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields",
            data={"fieldId": field_id},
        )
        return True
    except JiraError:
        return False


# =============================================================================
# Implementation Functions
# =============================================================================


def _list_fields_impl(
    filter_pattern: str | None = None,
    agile_only: bool = False,
    custom_only: bool = True,
    client: JiraClient | None = None,
) -> list[dict[str, Any]]:
    """
    List fields from JIRA instance.

    Args:
        filter_pattern: Filter fields by name pattern (case-insensitive)
        agile_only: If True, only show Agile-related fields
        custom_only: If True, only show custom fields (default: True)
        client: Optional JiraClient instance. If None, creates one internally.

    Returns:
        List of field dictionaries
    """

    def _do_list(c: JiraClient) -> list[dict[str, Any]]:
        fields = c.get("/rest/api/3/field")

        result: list[dict[str, Any]] = []
        for field in fields:
            if custom_only and not field.get("custom", False):
                continue

            name = field.get("name", "")
            field_id = field.get("id", "")

            if filter_pattern and filter_pattern.lower() not in name.lower():
                continue

            if agile_only:
                is_agile = any(pattern in name.lower() for pattern in AGILE_PATTERNS)
                if not is_agile:
                    continue

            schema = field.get("schema", {})
            result.append(
                {
                    "id": field_id,
                    "name": name,
                    "type": schema.get("type", "unknown"),
                    "custom": field.get("custom", False),
                    "searchable": field.get("searchable", False),
                    "navigable": field.get("navigable", False),
                }
            )

        result.sort(key=lambda x: x["name"].lower())
        return result

    if client is not None:
        return _do_list(client)

    with get_jira_client() as c:
        return _do_list(c)


def _create_field_impl(
    name: str,
    field_type: str,
    description: str | None = None,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """
    Create a custom field.

    Args:
        name: Field name
        field_type: Field type (text, number, select, etc.)
        description: Optional field description
        client: Optional JiraClient instance. If None, creates one internally.

    Returns:
        Created field data

    Raises:
        ValidationError: If field type is invalid
    """
    if field_type not in FIELD_TYPES:
        raise ValidationError(
            f"Invalid field type: {field_type}. "
            f"Valid types: {', '.join(FIELD_TYPES.keys())}"
        )

    def _do_create(c: JiraClient) -> dict[str, Any]:
        type_config = FIELD_TYPES[field_type]

        data: dict[str, Any] = {
            "name": name,
            "type": type_config["type"],
            "searcherKey": type_config["searcher"],
        }

        if description:
            data["description"] = description

        result = c.post("/rest/api/3/field", data=data)
        return result

    if client is not None:
        return _do_create(client)

    with get_jira_client() as c:
        return _do_create(c)


def _check_project_fields_impl(
    project_key: str,
    issue_type: str | None = None,
    check_agile: bool = False,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """
    Check field availability for a project.

    Args:
        project_key: Project key
        issue_type: Optional issue type to check
        check_agile: If True, specifically check Agile field availability
        client: Optional JiraClient instance. If None, creates one internally.

    Returns:
        Dictionary with project info and available fields
    """

    def _do_check(c: JiraClient) -> dict[str, Any]:
        project = c.get(f"/rest/api/3/project/{project_key}")

        result: dict[str, Any] = {
            "project_key": project.get("key"),
            "project": {
                "key": project.get("key"),
                "name": project.get("name"),
                "id": project.get("id"),
                "style": project.get("style", "classic"),
                "simplified": project.get("simplified", False),
                "project_type": project.get("projectTypeKey"),
            },
            "is_team_managed": project.get("style") == "next-gen",
            "fields": {},
            "issue_types": [],
        }

        # Use new per-project createmeta endpoints (replaces deprecated /issue/createmeta)
        issue_types_resp = c.get_create_issue_meta_issuetypes(project_key)
        issue_types = issue_types_resp.get("values", [])

        # Filter by issue type name if specified
        if issue_type:
            issue_types = [
                it
                for it in issue_types
                if it.get("name", "").lower() == issue_type.lower()
            ]

        for itype in issue_types:
            type_info: dict[str, Any] = {
                "name": itype.get("name"),
                "id": itype.get("id"),
                "fields": [],
            }

            # Get fields for this issue type
            fields_resp = c.get_create_issue_meta_fields(project_key, itype.get("id"))
            for finfo in fields_resp.get("values", []):
                fid = finfo.get("fieldId")
                field = {
                    "id": fid,
                    "name": finfo.get("name"),
                    "required": finfo.get("required", False),
                }
                type_info["fields"].append(field)

                if fid not in result["fields"]:
                    result["fields"][fid] = finfo.get("name")

            result["issue_types"].append(type_info)

        if check_agile:
            result["agile_fields"] = {}
            all_fields = {v.lower(): k for k, v in result["fields"].items()}

            for agile_type, patterns in AGILE_FIELDS.items():
                found = None
                for pattern in patterns:
                    for field_name, field_id in all_fields.items():
                        if pattern in field_name:
                            found = {"id": field_id, "name": result["fields"][field_id]}
                            break
                    if found:
                        break
                result["agile_fields"][agile_type] = found

        return result

    if client is not None:
        return _do_check(client)

    with get_jira_client() as c:
        return _do_check(c)


def _configure_agile_fields_impl(
    project_key: str,
    story_points_id: str | None = None,
    epic_link_id: str | None = None,
    sprint_id: str | None = None,
    dry_run: bool = False,
    client: JiraClient | None = None,
) -> dict[str, Any]:
    """
    Configure Agile fields for a project.

    Args:
        project_key: Project key
        story_points_id: Custom Story Points field ID (optional, auto-detect)
        epic_link_id: Custom Epic Link field ID (optional, auto-detect)
        sprint_id: Custom Sprint field ID (optional, auto-detect)
        dry_run: If True, show what would be done without making changes
        client: Optional JiraClient instance. If None, creates one internally.

    Returns:
        Configuration result

    Raises:
        ValidationError: If project is team-managed
    """

    def _do_configure(c: JiraClient) -> dict[str, Any]:
        project = c.get(f"/rest/api/3/project/{project_key}")

        if project.get("style") == "next-gen":
            raise ValidationError(
                f"Project {project_key} is team-managed (next-gen). "
                "Field configuration must be done in the project settings UI."
            )

        result: dict[str, Any] = {
            "project": project_key,
            "dry_run": dry_run,
            "fields_found": {},
            "screens_found": [],
            "fields_added": [],
        }

        agile_fields = _find_agile_fields(c)

        field_mapping = {
            "story_points": story_points_id or agile_fields.get("story_points"),
            "epic_link": epic_link_id or agile_fields.get("epic_link"),
            "sprint": sprint_id or agile_fields.get("sprint"),
        }

        result["fields_found"] = {k: v for k, v in field_mapping.items() if v}

        if not any(field_mapping.values()):
            raise ValidationError(
                "No Agile fields found in JIRA instance. "
                "Create Story Points, Epic Link, and Sprint fields first."
            )

        screens = _find_project_screens(c, project_key)
        result["screens_found"] = [s["name"] for s in screens]

        if not screens:
            screens = [{"id": 1, "name": "Default Screen"}]

        for screen in screens:
            screen_id = screen["id"]
            screen_name = screen["name"]

            for field_type, field_id in field_mapping.items():
                if field_id:
                    success = _add_field_to_screen(c, screen_id, field_id, dry_run)
                    if success:
                        result["fields_added"].append(
                            {
                                "field": field_type,
                                "field_id": field_id,
                                "screen": screen_name,
                                "screen_id": screen_id,
                            }
                        )

        return result

    if client is not None:
        return _do_configure(client)

    with get_jira_client() as c:
        return _do_configure(c)


# =============================================================================
# Formatting Functions
# =============================================================================


def _format_fields_list(fields: list[dict]) -> str:
    """Format fields list for text output."""
    if not fields:
        return "No fields found matching criteria"

    lines = []
    lines.append(f"Found {len(fields)} field(s)")
    lines.append("")

    # Calculate column widths
    id_width = max(len(f["id"]) for f in fields)
    name_width = max(len(f["name"]) for f in fields)
    type_width = max(len(f["type"]) for f in fields)

    id_width = max(id_width, 8)
    name_width = max(name_width, 4)
    type_width = max(type_width, 4)

    header = f"{'Field ID':<{id_width}}  {'Name':<{name_width}}  {'Type':<{type_width}}"
    lines.append(header)
    lines.append("─" * id_width + "  " + "─" * name_width + "  " + "─" * type_width)

    for f in fields:
        row = f"{f['id']:<{id_width}}  {f['name']:<{name_width}}  {f['type']:<{type_width}}"
        lines.append(row)

    return "\n".join(lines)


def _format_created_field(result: dict) -> str:
    """Format created field for text output."""
    lines = []
    lines.append(f"Created field: {result.get('name')}")
    lines.append(f"Field ID: {result.get('id')}")
    lines.append(f"Type: {result.get('schema', {}).get('type', 'unknown')}")
    return "\n".join(lines)


def _format_project_fields(result: dict, check_agile: bool) -> str:
    """Format project fields check for text output."""
    lines = []

    proj = result["project"]
    lines.append(f"Project: {proj['key']} ({proj['name']})")
    lines.append(f"Type: {proj['project_type']}")
    style = (
        "Team-managed (next-gen)"
        if result["is_team_managed"]
        else "Company-managed (classic)"
    )
    lines.append(f"Style: {style}")
    lines.append("")

    lines.append(f"Issue Types: {len(result['issue_types'])}")
    for itype in result["issue_types"]:
        lines.append(f"  - {itype['name']} ({len(itype['fields'])} fields)")
    lines.append("")

    if check_agile and "agile_fields" in result:
        lines.append("Agile Field Availability:")
        for field_type, field_info in result.get("agile_fields", {}).items():
            if field_info:
                lines.append(
                    f"  ✓ {field_type}: {field_info['name']} ({field_info['id']})"
                )
            else:
                lines.append(f"  ✗ {field_type}: NOT AVAILABLE")

        lines.append("")
        if result["is_team_managed"]:
            lines.append("Note: This is a team-managed project.")
            lines.append("  - Field configuration is done in project settings UI")
        else:
            lines.append("Note: This is a company-managed project.")
            lines.append(
                "  - Use 'jira-as fields configure-agile' to add missing fields"
            )

    return "\n".join(lines)


def _format_agile_config(result: dict) -> str:
    """Format agile configuration result for text output."""
    lines = []

    if result["dry_run"]:
        lines.append("[DRY RUN] No changes made")
        lines.append("")

    lines.append(f"Project: {result['project']}")
    lines.append("")

    lines.append("Agile Fields Found:")
    for field_type, field_id in result["fields_found"].items():
        lines.append(f"  {field_type}: {field_id}")
    lines.append("")

    lines.append(f"Screens Found: {len(result['screens_found'])}")
    for screen in result["screens_found"]:
        lines.append(f"  - {screen}")
    lines.append("")

    if result["fields_added"]:
        action = "Would add" if result["dry_run"] else "Added"
        lines.append(f"{action} fields:")
        for item in result["fields_added"]:
            lines.append(f"  {item['field']} ({item['field_id']}) -> {item['screen']}")

        if not result["dry_run"]:
            lines.append("")
            lines.append("Agile fields configured successfully!")
    else:
        lines.append("No fields to add (already configured or no fields found)")

    return "\n".join(lines)


# =============================================================================
# CLI Commands
# =============================================================================


@click.group()
def fields():
    """Commands for managing JIRA custom fields."""
    pass


@fields.command(name="list")
@click.option("--filter", "-f", "filter_pattern", help="Filter fields by name pattern")
@click.option("--agile", "-a", is_flag=True, help="Show only Agile-related fields")
@click.option(
    "--all", "show_all", is_flag=True, help="Show all fields (not just custom)"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
@handle_jira_errors
def fields_list(
    ctx: click.Context, filter_pattern: str, agile: bool, show_all: bool, output: str
):
    """List all available fields."""
    client = get_client_from_context(ctx)
    result = _list_fields_impl(
        filter_pattern=filter_pattern,
        agile_only=agile,
        custom_only=not show_all,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_fields_list(result))


@fields.command(name="create")
@click.option("--name", "-n", required=True, help="Field name")
@click.option(
    "--type",
    "-t",
    "field_type",
    required=True,
    type=click.Choice(list(FIELD_TYPES.keys())),
    help="Field type",
)
@click.option("--description", "-d", help="Field description")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
@handle_jira_errors
def fields_create(
    ctx: click.Context, name: str, field_type: str, description: str, output: str
):
    """Create a new custom field."""
    client = get_client_from_context(ctx)
    result = _create_field_impl(
        name=name,
        field_type=field_type,
        description=description,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_created_field(result))


@fields.command(name="check-project")
@click.argument("project_key")
@click.option("--type", "-t", "issue_type", help="Specific issue type to check")
@click.option(
    "--check-agile", "-a", is_flag=True, help="Check Agile field availability"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
@handle_jira_errors
def fields_check_project(
    ctx: click.Context,
    project_key: str,
    issue_type: str,
    check_agile: bool,
    output: str,
):
    """Check which fields are available for a project."""
    client = get_client_from_context(ctx)
    result = _check_project_fields_impl(
        project_key=project_key,
        issue_type=issue_type,
        check_agile=check_agile,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_project_fields(result, check_agile))


@fields.command(name="configure-agile")
@click.argument("project_key")
@click.option("--epic-link", help="Epic Link field ID")
@click.option("--story-points", help="Story Points field ID")
@click.option("--sprint", help="Sprint field ID")
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be done without making changes",
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
@handle_jira_errors
def fields_configure_agile(
    ctx: click.Context,
    project_key: str,
    epic_link: str,
    story_points: str,
    sprint: str,
    dry_run: bool,
    output: str,
):
    """Configure Agile field mappings for a project."""
    client = get_client_from_context(ctx)
    result = _configure_agile_fields_impl(
        project_key=project_key,
        story_points_id=story_points,
        epic_link_id=epic_link,
        sprint_id=sprint,
        dry_run=dry_run,
        client=client,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(_format_agile_config(result))
