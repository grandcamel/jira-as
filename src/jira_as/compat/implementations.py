"""Contract implementations use GenericClient; legacy helpers remain for JAS-49."""

from __future__ import annotations

from typing import Any

import click

from jira_as import (
    JiraError,
    NotFoundError,
    PermissionError,
    ValidationError,
    find_transition_by_name,
    format_datetime_for_jira,
    format_transitions,
    get_agile_fields,
    get_project_defaults,
    has_project_context,
    print_info,
    validate_issue_key,
    validate_project_key,
    validate_transition_id,
)
from jira_as.cli.commands.agile_cmds import FIBONACCI_SEQUENCE
from jira_as.cli.commands.issue_cmds import _load_template
from jira_as.cli.commands.lifecycle_cmds import (
    _get_context_workflow_hint,
    _screen_rejected_option_fields,
)
from jira_as.cli.commands.relationships_cmds import LINK_TYPE_MAPPING, _find_link_type
from jira_as.compat.client import GenericClient
from jira_as.compat.richtext import prepare_fields, richtext
from jira_as.time_utils import parse_relative_date, validate_time_format


def _create_issue_impl(
    project: str,
    issue_type: str,
    summary: str,
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    components: list[str] | None = None,
    template: str | None = None,
    custom_fields: dict | None = None,
    epic: str | None = None,
    sprint: int | None = None,
    story_points: float | None = None,
    blocks: list[str] | None = None,
    relates_to: list[str] | None = None,
    estimate: str | None = None,
    parent: str | None = None,
    parent_via_update: bool = False,
    dry_run: bool = False,
    no_defaults: bool = False,
    client: GenericClient | None = None,
    description_format: str | None = None,
) -> dict:
    """
    Create a new JIRA issue.

    Args:
        project: Project key
        issue_type: Issue type (Bug, Task, Story, etc.)
        summary: Issue summary
        description: Issue description (markdown supported)
        priority: Priority name
        assignee: Assignee account ID or email
        labels: List of labels
        components: List of component names
        template: Template name to use as base
        custom_fields: Additional custom fields
        epic: Epic key to link this issue to
        sprint: Sprint ID to add this issue to
        story_points: Story point estimate
        blocks: List of issue keys this issue blocks
        relates_to: List of issue keys this issue relates to
        estimate: Original time estimate (e.g., '2d', '4h')
        parent: Parent issue key (epic or parent task) set via the modern
            'parent' field rather than the legacy epic-link custom field
        parent_via_update: If True, create the issue without a parent and set
            it in a follow-up update. Some workflow validators reject a parent
            at create time but accept it afterwards.
        dry_run: If True, build and return the payload without calling the API
        no_defaults: If True, skip applying project context defaults
        client: Optional GenericClient instance. If None, creates one internally.

    Returns:
        Created issue data. For a dry run, a dict with 'dry_run': True and the
        'fields' payload that would have been sent.
    """
    project = validate_project_key(project)

    # Apply project context defaults for unspecified fields
    defaults_applied = []
    if not no_defaults and has_project_context(project):
        defaults = get_project_defaults(project, issue_type)
        if defaults:
            if priority is None and "priority" in defaults:
                priority = defaults["priority"]
                defaults_applied.append("priority")
            if assignee is None and "assignee" in defaults:
                assignee = defaults["assignee"]
                defaults_applied.append("assignee")
            if labels is None and "labels" in defaults:
                labels = defaults["labels"]
                defaults_applied.append("labels")
            if components is None and "components" in defaults:
                components = defaults["components"]
                defaults_applied.append("components")
            if story_points is None and "story_points" in defaults:
                story_points = defaults["story_points"]
                defaults_applied.append("story_points")

    fields = {}

    if template:
        template_data = _load_template(template)
        fields = template_data.get("fields", {})

    fields["project"] = {"key": project}
    fields["issuetype"] = {"name": issue_type}
    fields["summary"] = summary

    if description:
        fields["description"] = richtext(description, description_format)

    if priority:
        fields["priority"] = {"name": priority}

    if parent:
        # The modern 'parent' field covers epics and parent tasks alike; the
        # epic-link custom field is legacy and instance-specific.
        fields["parent"] = {"key": validate_issue_key(parent)}

    def _do_create(c: GenericClient) -> dict:
        """Inner function that performs the create with a client."""
        nonlocal assignee, fields

        if assignee:
            if assignee.lower() == "self":
                account_id = c.get_current_user_id(for_create=True)
                fields["assignee"] = {"accountId": account_id}
            elif "@" in assignee:
                fields["assignee"] = {"emailAddress": assignee}
            else:
                fields["assignee"] = {"accountId": assignee}

        if labels:
            fields["labels"] = labels

        if components:
            fields["components"] = [{"name": comp} for comp in components]

        if custom_fields:
            fields.update(custom_fields)

        # Agile fields - field IDs commonly differ per project, so resolve
        # them against this project rather than the global defaults.
        if epic or story_points is not None:
            agile_fields = get_agile_fields(project_key=project)

            if epic:
                validated_epic = validate_issue_key(epic)
                fields[agile_fields["epic_link"]] = validated_epic

            if story_points is not None:
                fields[c.story_points_field(project)] = story_points

        # Time tracking
        if estimate:
            fields["timetracking"] = {"originalEstimate": estimate}

        # Rich-text custom fields must be sent as ADF, not bare strings.
        prepare_fields(fields)

        # A workflow validator may reject a parent at create time; creating
        # first and setting the parent in a follow-up update works around it.
        deferred_parent = None
        if parent_via_update and "parent" in fields:
            deferred_parent = fields.pop("parent")

        if dry_run:
            payload: dict[str, Any] = {
                "dry_run": True,
                "fields": fields,
            }
            if deferred_parent:
                payload["deferred_parent"] = deferred_parent
            if defaults_applied:
                payload["defaults_applied"] = defaults_applied
            return payload

        result = c.create_issue(fields)

        # Add to sprint after creation (sprint assignment requires issue to exist)
        # The create endpoint always returns a key on success.
        issue_key = result["key"]

        if deferred_parent:
            c.update_issue(issue_key, {"parent": deferred_parent})
            result["parent_set_via_update"] = deferred_parent.get("key")

        if sprint:
            c.move_issues_to_sprint(sprint, [issue_key])

        # Create issue links after creation
        links_created = []
        links_failed = []
        if blocks:
            for target_key in blocks:
                validated_target = validate_issue_key(target_key)
                try:
                    c.create_link("Blocks", issue_key, validated_target)
                    links_created.append(f"blocks {validated_target}")
                except (PermissionError, NotFoundError) as e:
                    links_failed.append(f"blocks {validated_target}: {e!s}")

        if relates_to:
            for target_key in relates_to:
                validated_target = validate_issue_key(target_key)
                try:
                    c.create_link("Relates", issue_key, validated_target)
                    links_created.append(f"relates to {validated_target}")
                except (PermissionError, NotFoundError) as e:
                    links_failed.append(f"relates to {validated_target}: {e!s}")

        if links_created:
            result["links_created"] = links_created
        if links_failed:
            result["links_failed"] = links_failed
        if defaults_applied:
            result["defaults_applied"] = defaults_applied

        return result

    if client is not None:
        return _do_create(client)

    with GenericClient() as c:
        return _do_create(c)


def _update_issue_impl(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    components: list[str] | None = None,
    custom_fields: dict | None = None,
    parent: str | None = None,
    notify_users: bool = True,
    client: GenericClient | None = None,
    description_format: str | None = None,
) -> None:
    """
    Update a JIRA issue.

    Args:
        issue_key: Issue key (e.g., PROJ-123)
        summary: New summary
        description: New description (markdown supported)
        priority: New priority
        assignee: New assignee (account ID or email)
        labels: New labels (replaces existing)
        components: New components (replaces existing)
        custom_fields: Custom fields to update
        parent: New parent issue key, or "none" to remove the parent
        notify_users: Send notifications to watchers
        client: Optional GenericClient instance. If None, creates one internally.
    """
    issue_key = validate_issue_key(issue_key)

    fields: dict[str, Any] = {}

    if summary is not None:
        fields["summary"] = summary

    if description is not None:
        fields["description"] = richtext(description, description_format)

    if priority is not None:
        fields["priority"] = {"name": priority}

    if labels is not None:
        fields["labels"] = labels

    if components is not None:
        fields["components"] = [{"name": comp} for comp in components]

    if custom_fields:
        fields.update(custom_fields)

    if parent is not None:
        if parent.lower() in ("none", "unassigned", ""):
            fields["parent"] = None
        else:
            fields["parent"] = {"key": validate_issue_key(parent)}

    # Rich-text custom fields must be sent as ADF, not bare strings.
    prepare_fields(fields)

    def _do_update(c: GenericClient) -> None:
        """Inner function that performs the update with a client."""
        nonlocal fields

        if assignee is not None:
            if assignee.lower() in ("none", "unassigned"):
                fields["assignee"] = None
            elif assignee.lower() == "self":
                account_id = c.get_current_user_id()
                fields["assignee"] = {"accountId": account_id}
            elif "@" in assignee:
                fields["assignee"] = {"emailAddress": assignee}
            else:
                fields["assignee"] = {"accountId": assignee}

        if not fields:
            raise ValueError("No fields specified for update")

        c.update_issue(issue_key, fields, notify_users=notify_users)

    if client is not None:
        _do_update(client)
        return

    with GenericClient() as c:
        _do_update(c)


def _add_comment_impl(
    issue_key: str,
    body: str,
    body_format: str = "text",
    visibility_type: str | None = None,
    visibility_value: str | None = None,
    client: GenericClient | None = None,
) -> dict:
    """
    Add a comment to an issue.

    Args:
        issue_key: Issue key (e.g., PROJ-123)
        body: Comment body
        body_format: Format ('text', 'markdown', or 'adf')
        visibility_type: 'role' or 'group' (None for public)
        visibility_value: Role or group name
        client: Optional GenericClient instance

    Returns:
        Created comment data
    """
    issue_key = validate_issue_key(issue_key)

    if body_format == "adf":
        comment_body = richtext(body, "adf")
    elif body_format == "markdown":
        comment_body = richtext(body, "markdown")
    else:
        comment_body = richtext(body, "text")

    def _do_work(c: GenericClient) -> dict:
        if visibility_type:
            result = c.add_comment_with_visibility(
                issue_key,
                comment_body,
                visibility_type=visibility_type,
                visibility_value=visibility_value,
            )
        else:
            result = c.add_comment(issue_key, comment_body)
        return result

    if client is not None:
        return _do_work(client)

    with GenericClient() as c:
        return _do_work(c)


def _transition_issue_impl(
    issue_key: str,
    transition_id: str | None = None,
    transition_name: str | None = None,
    resolution: str | None = None,
    comment: str | None = None,
    fields: dict | None = None,
    sprint_id: int | None = None,
    dry_run: bool = False,
    client: GenericClient | None = None,
) -> dict:
    """
    Transition an issue to a new status.

    Args:
        issue_key: Issue key (e.g., PROJ-123)
        transition_id: Transition ID
        transition_name: Transition name (alternative to ID)
        resolution: Resolution to set (for Done transitions)
        comment: Comment to add
        fields: Additional fields to set
        sprint_id: Sprint ID to move issue to after transition
        dry_run: If True, preview changes without making them
        client: Optional GenericClient instance

    Returns:
        Dictionary with transition details
    """
    issue_key = validate_issue_key(issue_key)

    if not transition_id and not transition_name:
        raise ValidationError("Either --id or --to must be specified")

    def _do_work(c: GenericClient) -> dict:
        nonlocal transition_id
        # Get issue details first for context hints
        issue = c.get_issue(issue_key, fields=["status", "issuetype", "project"])
        current_status = (
            issue.get("fields", {}).get("status", {}).get("name", "Unknown")
        )
        issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "Unknown")
        project_key = (
            issue.get("fields", {})
            .get("project", {})
            .get("key", issue_key.split("-")[0])
        )

        transitions = c.get_transitions(issue_key)

        if not transitions:
            context_hint = _get_context_workflow_hint(
                project_key, issue_type, current_status
            )
            raise ValidationError(
                f"No transitions available for {issue_key} (status: {current_status}){context_hint}"
            )

        if transition_name:
            transition = find_transition_by_name(transitions, transition_name)
            transition_id = transition["id"]
        else:
            # transition_id must be set since we checked at line 107
            assert transition_id is not None
            transition_id = validate_transition_id(transition_id)
            matching = [t for t in transitions if t["id"] == transition_id]
            if not matching:
                available = format_transitions(transitions)
                context_hint = _get_context_workflow_hint(
                    project_key, issue_type, current_status
                )
                raise ValidationError(
                    f"Transition ID '{transition_id}' not available.\n\n{available}{context_hint}"
                )
            transition = matching[0]

        transition_fields = dict(fields or {})
        option_fields: set[str] = set()

        if resolution:
            transition_fields["resolution"] = {"name": resolution}
            option_fields.add("resolution")

        if comment:
            transition_fields["comment"] = richtext(comment, "markdown")
            option_fields.add("comment")

        target_status = transition.get("to", {}).get(
            "name", transition.get("name", "Unknown")
        )

        result = {
            "issue_key": issue_key,
            "transition": transition.get("name"),
            "transition_id": transition_id,
            "current_status": current_status,
            "target_status": target_status,
            "resolution": resolution,
            "comment": comment is not None,
            "resolution_applied": resolution is not None,
            "comment_applied": comment is not None,
            "fallback_fields": [],
            "sprint_id": sprint_id,
            "dry_run": dry_run,
        }

        if dry_run:
            print_info(f"[DRY RUN] Would transition {issue_key}:")
            click.echo(f"  Current status: {current_status}")
            click.echo(f"  Target status: {target_status}")
            click.echo(f"  Transition: {transition.get('name')}")
            if resolution:
                click.echo(f"  Resolution: {resolution}")
            if comment:
                click.echo("  Comment: (would add comment)")
            if sprint_id:
                click.echo(f"  Sprint: Would move to sprint {sprint_id}")

            context_hint = _get_context_workflow_hint(
                project_key, issue_type, target_status
            )
            if context_hint:
                click.echo(
                    f"\n  After transition, expected options:{context_hint.replace(chr(10), chr(10) + '  ')}"
                )

            return result

        pending_fields = dict(transition_fields)
        while True:
            try:
                c.transition_issue(
                    issue_key,
                    transition_id,
                    fields=pending_fields if pending_fields else None,
                )
                break
            except JiraError as error:
                rejected = _screen_rejected_option_fields(error, option_fields)
                if not rejected:
                    raise
                for field in sorted(rejected):
                    pending_fields.pop(field, None)
                    option_fields.remove(field)
                    result["fallback_fields"].append(field)
                    click.echo(
                        f"Warning: transition screen rejected --{field}; "
                        + (
                            "the comment will be added separately after transition."
                            if field == "comment"
                            else "transitioning without setting the requested resolution."
                        ),
                        err=True,
                    )

        if "resolution" in result["fallback_fields"]:
            result["resolution_applied"] = False

        if "comment" in result["fallback_fields"]:
            assert comment is not None
            c.add_comment(issue_key, richtext(comment, "markdown"))

        if sprint_id:
            c.move_issues_to_sprint(sprint_id, [issue_key])

        return result

    if client is not None:
        return _do_work(client)

    with GenericClient() as c:
        return _do_work(c)


def _add_worklog_impl(
    issue_key: str,
    time_spent: str,
    started: str | None = None,
    comment: str | None = None,
    adjust_estimate: str = "auto",
    new_estimate: str | None = None,
    reduce_by: str | None = None,
    visibility_type: str | None = None,
    visibility_value: str | None = None,
    client: GenericClient | None = None,
) -> dict[str, Any]:
    """
    Add a worklog to an issue.

    Args:
        issue_key: Issue key (e.g., 'PROJ-123')
        time_spent: Time spent in JIRA format (e.g., '2h', '1d 4h')
        started: When work was started (ISO format, relative like 'yesterday')
        comment: Optional comment text
        adjust_estimate: How to adjust remaining estimate
        new_estimate: New remaining estimate (when adjust_estimate='new')
        reduce_by: Amount to reduce estimate (when adjust_estimate='manual')
        visibility_type: 'role' or 'group' to restrict visibility
        visibility_value: Role or group name for visibility restriction
        client: Optional GenericClient instance (uses context manager if None)

    Returns:
        Created worklog object
    """
    validate_issue_key(issue_key)

    if not time_spent or not time_spent.strip():
        raise ValidationError("Time spent cannot be empty")

    if not validate_time_format(time_spent):
        raise ValidationError(
            f"Invalid time format: '{time_spent}'. Use format like '2h', '1d 4h', '30m'"
        )

    if visibility_type and not visibility_value:
        raise ValidationError(
            "--visibility-value is required when --visibility-type is specified"
        )
    if visibility_value and not visibility_type:
        raise ValidationError(
            "--visibility-type is required when --visibility-value is specified"
        )

    started_iso = None
    if started:
        try:
            dt = parse_relative_date(started)
            started_iso = format_datetime_for_jira(dt)
        except ValueError as e:
            raise ValidationError(str(e))

    comment_adf = None
    if comment:
        comment_adf = richtext(comment, "markdown")

    def _do_work(c: GenericClient) -> dict[str, Any]:
        return c.add_worklog(
            issue_key=issue_key,
            time_spent=time_spent,
            started=started_iso,
            comment=comment_adf,
            adjust_estimate=adjust_estimate,
            new_estimate=new_estimate,
            reduce_by=reduce_by,
            visibility_type=visibility_type,
            visibility_value=visibility_value,
        )

    if client is not None:
        return _do_work(client)

    with GenericClient() as c:
        return _do_work(c)


def _estimate_issue_impl(
    issue_keys: list[str] | None = None,
    jql: str | None = None,
    points: float | None = None,
    validate_fibonacci: bool = False,
    client: "GenericClient | None" = None,
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

    def _do_work(c: "GenericClient") -> dict[str, Any]:
        keys_to_update = issue_keys
        if jql and not keys_to_update:
            search_result = c.search_issues(jql)
            keys_to_update = [issue["key"] for issue in search_result.get("issues", [])]

        if not keys_to_update:
            return {"updated": 0, "issues": []}

        validated_keys = [validate_issue_key(k) for k in keys_to_update]
        story_points_field = c.story_points_field(validated_keys[0].split("-")[0])
        points_value = None if points == 0 else points

        updated = 0
        for key in validated_keys:
            c.update_issue(key, {story_points_field: points_value})
            updated += 1

        return {"updated": updated, "issues": validated_keys, "points": points}

    if client is not None:
        return _do_work(client)

    with GenericClient() as c:
        return _do_work(c)


def _link_issue_impl(
    issue_key: str,
    blocks: str | None = None,
    duplicates: str | None = None,
    relates_to: str | None = None,
    clones: str | None = None,
    is_blocked_by: str | None = None,
    is_duplicated_by: str | None = None,
    is_cloned_by: str | None = None,
    link_type: str | None = None,
    target_issue: str | None = None,
    comment: str | None = None,
    dry_run: bool = False,
    client: GenericClient | None = None,
) -> dict | None:
    """Create a link between two issues."""
    issue_key = validate_issue_key(issue_key)

    # Determine link type and target from semantic flags or explicit type
    resolved_type = None
    resolved_target = None
    is_inward = False

    semantic_args = {
        "blocks": blocks,
        "duplicates": duplicates,
        "relates_to": relates_to,
        "clones": clones,
        "is_blocked_by": is_blocked_by,
        "is_duplicated_by": is_duplicated_by,
        "is_cloned_by": is_cloned_by,
    }

    for flag_name, flag_value in semantic_args.items():
        if flag_value:
            resolved_type = LINK_TYPE_MAPPING[flag_name]
            resolved_target = flag_value
            is_inward = flag_name.startswith("is_")
            break

    if link_type and target_issue:
        resolved_type = link_type
        resolved_target = target_issue

    if not resolved_type or not resolved_target:
        raise ValidationError(
            "Must specify a link type (--blocks, --duplicates, etc.) or --type with --to"
        )

    resolved_target = validate_issue_key(resolved_target)

    if issue_key.upper() == resolved_target.upper():
        raise ValidationError("Cannot link an issue to itself")

    def _do_work(c: GenericClient) -> dict | None:
        link_types = c.get_link_types()
        link_type_obj = _find_link_type(link_types, resolved_type)

        if is_inward:
            inward_key = issue_key
            outward_key = resolved_target
        else:
            inward_key = resolved_target
            outward_key = issue_key

        adf_comment = None
        if comment:
            adf_comment = richtext(comment, "markdown")

        if dry_run:
            direction = (
                link_type_obj.get("outward", resolved_type)
                if not is_inward
                else link_type_obj.get("inward", resolved_type)
            )
            return {
                "source": issue_key,
                "target": resolved_target,
                "link_type": link_type_obj["name"],
                "direction": direction,
                "preview": f"{issue_key} {direction} {resolved_target}",
            }

        try:
            c.create_link(link_type_obj["name"], inward_key, outward_key, adf_comment)
        except JiraError as e:
            if e.status_code not in (403, 404) and not isinstance(
                e, (NotFoundError, PermissionError)
            ):
                raise
            # Cross-project and JSM targets often reject a native link even
            # though a remote link to the same issue works fine.
            click.echo(
                f"Hint: a native link to {resolved_target} was rejected. "
                "If the target is in another project or a service desk, try "
                f"'relationships link {issue_key} --remote-url <issue URL>'.",
                err=True,
            )
            raise e
        return None

    if client is not None:
        return _do_work(client)

    with GenericClient() as c:
        return _do_work(c)
