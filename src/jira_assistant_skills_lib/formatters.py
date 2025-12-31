"""
Output formatting utilities for JIRA data.

Provides functions to format JIRA API responses as tables, JSON,
CSV, and human-readable text.
"""

from typing import Dict, Any, List, Optional
from .adf_helper import adf_to_text

# Import generic formatters from the base library
from assistant_skills_lib.formatters import (
    format_table,
    format_json,
    export_csv,
    get_csv_string,
    print_success,
    print_warning,
    print_info,
    format_timestamp
)


EPIC_LINK_FIELD = 'customfield_10014'
STORY_POINTS_FIELD = 'customfield_10016'


def format_issue(issue: Dict[str, Any], detailed: bool = False) -> str:
    """
    Format a JIRA issue for display.

    Args:
        issue: Issue data from JIRA API
        detailed: If True, include all fields

    Returns:
        Formatted issue string
    """
    fields = issue.get('fields', {})
    key = issue.get('key', 'N/A')
    summary = fields.get('summary', 'N/A')
    status = fields.get('status', {}).get('name', 'N/A')
    issue_type = fields.get('issuetype', {}).get('name', 'N/A')
    priority = fields.get('priority', {}).get('name', 'N/A') if fields.get('priority') else 'None'
    assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
    reporter = fields.get('reporter', {}).get('displayName', 'N/A') if fields.get('reporter') else 'N/A'
    created = fields.get('created', 'N/A')
    updated = fields.get('updated', 'N/A')

    output = []
    output.append(f"Key:      {key}")
    output.append(f"Type:     {issue_type}")
    output.append(f"Summary:  {summary}")
    output.append(f"Status:   {status}")
    output.append(f"Priority: {priority}")
    output.append(f"Assignee: {assignee}")

    # Agile fields
    epic_link = fields.get(EPIC_LINK_FIELD)
    if epic_link:
        output.append(f"Epic:     {epic_link}")

    story_points = fields.get(STORY_POINTS_FIELD)
    if story_points is not None:
        output.append(f"Points:   {story_points}")

    # Sprint info (from customfield or sprint field)
    sprint = fields.get('sprint')
    if sprint:
        if isinstance(sprint, dict):
            sprint_name = sprint.get('name', str(sprint))
        elif isinstance(sprint, list) and sprint:
            sprint_name = sprint[0].get('name', str(sprint[0])) if isinstance(sprint[0], dict) else str(sprint[0])
        else:
            sprint_name = str(sprint)
        output.append(f"Sprint:   {sprint_name}")

    # Parent (for subtasks)
    parent = fields.get('parent')
    if parent:
        parent_key = parent.get('key', '')
        parent_summary = parent.get('fields', {}).get('summary', '')
        if parent_key:
            output.append(f"Parent:   {parent_key} - {parent_summary}")

    if detailed:
        output.append(f"Reporter: {reporter}")
        output.append(f"Created:  {format_timestamp(created)}")
        output.append(f"Updated:  {format_timestamp(updated)}")

        description = fields.get('description')
        if description:
            if isinstance(description, dict):
                desc_text = adf_to_text(description)
            else:
                desc_text = str(description)

            if desc_text:
                output.append(f"\nDescription:")
                for line in desc_text.split('\n'):
                    output.append(f"  {line}")

        labels = fields.get('labels', [])
        if labels:
            output.append(f"\nLabels: {', '.join(labels)}")

        components = fields.get('components', [])
        if components:
            comp_names = [c.get('name', '') for c in components]
            output.append(f"Components: {', '.join(comp_names)}")

        # Subtasks
        subtasks = fields.get('subtasks', [])
        if subtasks:
            output.append(f"\nSubtasks ({len(subtasks)}):")
            for st in subtasks:
                st_key = st.get('key', '')
                st_summary = st.get('fields', {}).get('summary', '')
                st_status = st.get('fields', {}).get('status', {}).get('name', '')
                output.append(f"  [{st_status}] {st_key} - {st_summary}")

        # Issue links
        issue_links = fields.get('issuelinks', [])
        if issue_links:
            output.append(f"\nLinks ({len(issue_links)}):")
            for link in issue_links:
                link_type = link.get('type', {}).get('name', 'Unknown')
                if 'outwardIssue' in link:
                    direction = link.get('type', {}).get('outward', 'links to')
                    linked = link['outwardIssue']
                else:
                    direction = link.get('type', {}).get('inward', 'linked from')
                    linked = link.get('inwardIssue', {})
                linked_key = linked.get('key', '')
                linked_summary = linked.get('fields', {}).get('summary', '')[:40]
                linked_status = linked.get('fields', {}).get('status', {}).get('name', '')
                output.append(f"  {direction} {linked_key} [{linked_status}] {linked_summary}")

    return '\n'.join(output)





def format_transitions(transitions: List[Dict[str, Any]]) -> str:
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
        data.append({
            'ID': t.get('id', ''),
            'Name': t.get('name', ''),
            'To Status': t.get('to', {}).get('name', '')
        })

    return format_table(data, columns=['ID', 'Name', 'To Status'])


def format_comments(comments: List[Dict[str, Any]], limit: Optional[int] = None) -> str:
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
        author = comment.get('author', {}).get('displayName', 'Unknown')
        created = comment.get('created', 'N/A')
        body = comment.get('body')

        if isinstance(body, dict):
            body_text = adf_to_text(body)
        else:
            body_text = str(body) if body else ''

        output.append(f"Comment #{i} by {author} at {format_timestamp(created)}:")
        for line in body_text.split('\n'):
            output.append(f"  {line}")
        output.append("")

    return '\n'.join(output)


def format_search_results(issues: List[Dict[str, Any]], show_agile: bool = False,
                          show_links: bool = False, show_time: bool = False) -> str:
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
        fields = issue.get('fields', {})
        row = {
            'Key': issue.get('key', ''),
            'Type': fields.get('issuetype', {}).get('name', ''),
            'Status': fields.get('status', {}).get('name', ''),
            'Priority': fields.get('priority', {}).get('name', '') if fields.get('priority') else '',
            'Assignee': fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else '',
            'Reporter': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else '',
            'Summary': fields.get('summary', '')[:50]
        }

        if show_agile:
            epic = fields.get(EPIC_LINK_FIELD, '')
            points = fields.get(STORY_POINTS_FIELD, '')
            row['Epic'] = epic if epic else ''
            row['Pts'] = str(points) if points else ''

        if show_links:
            links = fields.get('issuelinks', [])
            link_count = len(links)
            if link_count > 0:
                link_types = set()
                for link in links:
                    link_types.add(link.get('type', {}).get('name', ''))
                row['Links'] = f"{link_count} ({', '.join(link_types)})"
            else:
                row['Links'] = ''

        if show_time:
            tt = fields.get('timetracking', {})
            row['Est'] = tt.get('originalEstimate', '')
            row['Rem'] = tt.get('remainingEstimate', '')
            row['Spent'] = tt.get('timeSpent', '')

        data.append(row)

    if show_agile:
        columns = ['Key', 'Type', 'Status', 'Pts', 'Epic', 'Assignee', 'Reporter', 'Summary']
    elif show_links:
        columns = ['Key', 'Type', 'Status', 'Links', 'Assignee', 'Reporter', 'Summary']
    elif show_time:
        columns = ['Key', 'Type', 'Status', 'Est', 'Rem', 'Spent', 'Assignee', 'Reporter', 'Summary']
    else:
        columns = ['Key', 'Type', 'Status', 'Priority', 'Assignee', 'Reporter', 'Summary']

    return format_table(data, columns=columns)



