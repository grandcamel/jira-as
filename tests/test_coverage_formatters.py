"""Public display behavior for Jira issues, comments, searches and SLAs."""

import pytest

from jira_as import (
    EPIC_LINK_FIELD,
    STORY_POINTS_FIELD,
    calculate_sla_percentage,
    extract_issue_fields,
    format_comments,
    format_duration,
    format_issue,
    format_search_results,
    format_sla_duration,
    format_sla_time,
    format_transitions,
    get_sla_status_emoji,
    get_sla_status_text,
    is_sla_at_risk,
)


def adf(*paragraphs):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
            for text in paragraphs
        ],
    }


@pytest.fixture
def issue():
    return {
        "key": "SBX-1",
        "fields": {
            "summary": "Repair the dashboard",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Story"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "Ada"},
            "reporter": {"displayName": "Grace"},
            "created": "2026-09-01T10:00:00+00:00",
            "updated": "2026-09-02T11:00:00+00:00",
        },
    }


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"status": None, "priority": None, "assignee": None, "reporter": None},
        {"status": {}, "priority": {}, "assignee": {}, "reporter": {}},
    ],
)
def test_issue_defaults_for_unset_nested_fields(fields):
    normalized = extract_issue_fields({"fields": fields})
    assert (normalized.key, normalized.summary, normalized.status) == (
        "N/A",
        "N/A",
        "N/A",
    )
    assert (normalized.priority, normalized.assignee, normalized.reporter) == (
        "None",
        "Unassigned",
        "N/A",
    )
    assert normalized.parent_key is None
    assert normalized.sprint is None
    assert format_issue({"fields": fields}).splitlines() == [
        "Key:      N/A",
        "Type:     N/A",
        "Summary:  N/A",
        "Status:   N/A",
        "Priority: None",
        "Assignee: Unassigned",
    ]


@pytest.mark.parametrize(
    "sprint, expected",
    [
        ({"name": "September"}, "September"),
        ([{"name": "September"}, {"name": "October"}], "September"),
        (["September"], "September"),
        ("September", "September"),
        ([], None),
        (None, None),
    ],
)
def test_sprint_response_shapes(issue, sprint, expected):
    issue["fields"]["sprint"] = sprint
    assert extract_issue_fields(issue).sprint == expected
    rendered = format_issue(issue)
    if expected:
        assert f"Sprint:   {expected}" in rendered
    else:
        assert "Sprint:" not in rendered


@pytest.mark.parametrize("points", [0, 3.5])
def test_issue_agile_and_parent_details(issue, points):
    issue["fields"].update(
        {
            EPIC_LINK_FIELD: "SBX-10",
            STORY_POINTS_FIELD: points,
            "parent": {"key": "SBX-9", "fields": {"summary": "Dashboard epic"}},
        }
    )
    normalized = extract_issue_fields(issue)
    assert (normalized.issue_type, normalized.status, normalized.assignee) == (
        "Story",
        "In Progress",
        "Ada",
    )
    assert normalized.reporter == "Grace"
    assert normalized.parent_summary == "Dashboard epic"
    rendered = format_issue(issue)
    assert "Epic:     SBX-10" in rendered
    assert f"Points:   {points}" in rendered
    assert "Parent:   SBX-9 - Dashboard epic" in rendered
    assert "Reporter:" not in rendered


@pytest.mark.parametrize(
    "description", ["First line\nSecond line", adf("First line", "Second line")]
)
def test_detailed_issue_renders_description_and_relationships(issue, description):
    issue["fields"].update(
        {
            "description": description,
            "labels": ["dashboard", "release"],
            "components": [{"name": "Frontend"}, {"name": "Reporting"}],
            "subtasks": [
                {
                    "key": "SBX-2",
                    "fields": {"summary": "Fix chart", "status": {"name": "Open"}},
                }
            ],
            "issuelinks": [
                {
                    "type": {"outward": "blocks"},
                    "outwardIssue": {
                        "key": "SBX-3",
                        "fields": {
                            "summary": "x" * 40 + "TRIMMED",
                            "status": {"name": "Open"},
                        },
                    },
                },
                {
                    "type": {"inward": "is blocked by"},
                    "inwardIssue": {
                        "key": "SBX-4",
                        "fields": {
                            "summary": "Prepare data",
                            "status": {"name": "Done"},
                        },
                    },
                },
            ],
        }
    )
    rendered = format_issue(issue, detailed=True)
    for text in (
        "Reporter: Grace",
        "Created:",
        "2026-09-01",
        "Updated:",
        "2026-09-02",
        "Description:\n  First line\n  Second line",
        "Labels: dashboard, release",
        "Components: Frontend, Reporting",
        "Subtasks (1):\n  [Open] SBX-2 - Fix chart",
        "Links (2):",
        "blocks SBX-3 [Open] " + "x" * 40,
        "is blocked by SBX-4 [Done] Prepare data",
    ):
        assert text in rendered
    assert "TRIMMED" not in rendered
    assert "Description:" not in format_issue(issue)


@pytest.mark.parametrize("description", [None, "", adf()])
def test_empty_description_omits_section(issue, description):
    issue["fields"]["description"] = description
    rendered = format_issue(issue, detailed=True)
    assert "Description:" not in rendered
    assert "Labels:" not in rendered
    assert "Subtasks" not in rendered
    assert "Links" not in rendered


def test_transition_table_and_empty_message():
    assert format_transitions([]) == "No transitions available"
    rendered = format_transitions(
        [{"id": "31", "name": "Start work", "to": {"name": "In Progress"}}]
    )
    for value in ("ID", "Name", "To Status", "31", "Start work", "In Progress"):
        assert value in rendered


@pytest.mark.parametrize(
    "body", ["First line\nSecond line", adf("First line", "Second line")]
)
def test_comment_bodies_and_positive_limit(body):
    comments = [
        {"author": {"displayName": "Ada"}, "body": body},
        {"author": {"displayName": "Grace"}, "body": "Later comment"},
    ]
    limited = format_comments(comments, limit=1)
    assert "Comment #1 by Ada at N/A:" in limited
    assert "  First line\n  Second line" in limited
    assert "Later comment" not in limited
    assert "Comment #2 by Grace" in format_comments(comments)


def test_empty_comments_and_missing_body():
    assert format_comments([]) == "No comments"
    rendered = format_comments([{}])
    assert "Comment #1 by Unknown at N/A:" in rendered
    assert "None" not in rendered


@pytest.mark.parametrize(
    "options, headers, values",
    [
        ({}, ["Priority"], ["High"]),
        ({"show_agile": True}, ["Pts", "Epic"], ["SBX-10", "8"]),
        ({"show_links": True}, ["Links"], ["2 (Blocks)"]),
        ({"show_time": True}, ["Est", "Rem", "Spent"], ["2d", "3h", "1d"]),
    ],
)
def test_search_table_modes_and_missing_optional_values(
    issue, options, headers, values
):
    issue["fields"].update(
        {
            "summary": "x" * 50 + "TRIMMED",
            EPIC_LINK_FIELD: "SBX-10",
            STORY_POINTS_FIELD: 8,
            "issuelinks": [{"type": {"name": "Blocks"}}, {"type": {"name": "Blocks"}}],
            "timetracking": {
                "originalEstimate": "2d",
                "remainingEstimate": "3h",
                "timeSpent": "1d",
            },
        }
    )
    rendered = format_search_results([issue, {"key": "SBX-2", "fields": {}}], **options)
    for text in ["SBX-1", "SBX-2", "Ada", "Grace", "x" * 50, *headers, *values]:
        assert text in rendered
    assert "TRIMMED" not in rendered
    assert "None" not in rendered


def test_empty_search_results():
    assert format_search_results([]) == "No issues found"


@pytest.mark.parametrize(
    "value, expected",
    [
        ({}, "N/A"),
        ({"friendly": "Yesterday", "iso8601": "ignored"}, "Yesterday"),
        ({"iso8601": "2026-09-01"}, "2026-09-01"),
        ({"epochMillis": 1}, "Unknown"),
    ],
)
def test_sla_time_fallbacks(value, expected):
    assert format_sla_time(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ({}, "N/A"),
        ({"friendly": "2h", "millis": 7200000}, "2h"),
        ({"millis": 2500}, "2s"),
        ({"other": True}, "0s"),
    ],
)
def test_sla_duration_fallbacks(value, expected):
    assert format_sla_duration(value) == expected
    assert format_duration(value) == expected


@pytest.mark.parametrize(
    "elapsed, goal, expected", [(0, 0, 0.0), (50, 100, 50.0), (125, 100, 125.0)]
)
def test_sla_percentage(elapsed, goal, expected):
    assert calculate_sla_percentage(elapsed, goal) == expected


@pytest.mark.parametrize(
    "remaining, goal, threshold, expected",
    [
        (0, 0, 20, False),
        (19, 100, 20, True),
        (20, 100, 20, False),
        (21, 100, 20, False),
        (29, 100, 30, True),
    ],
)
def test_sla_risk_boundary(remaining, goal, threshold, expected):
    assert is_sla_at_risk(remaining, goal, threshold) is expected


@pytest.mark.parametrize(
    "sla, text, emoji",
    [
        ({}, "Unknown", "?"),
        ({"ongoingCycle": {"breached": True}}, "BREACHED", "✗"),
        ({"ongoingCycle": {"paused": True}}, "Paused", "⏸"),
        (
            {
                "ongoingCycle": {
                    "remainingTime": {"millis": 10},
                    "goalDuration": {"millis": 100},
                }
            },
            "At Risk",
            "⚠",
        ),
        (
            {
                "ongoingCycle": {
                    "remainingTime": {"millis": 50},
                    "goalDuration": {"millis": 100},
                }
            },
            "Active",
            "▶",
        ),
        ({"completedCycles": [{"breached": True}, {"breached": False}]}, "Met", "✓"),
        (
            {"completedCycles": [{"breached": False}, {"breached": True}]},
            "Failed",
            "✗",
        ),
    ],
)
def test_sla_status_display(sla, text, emoji):
    assert get_sla_status_text(sla) == text
    assert get_sla_status_emoji(sla) == emoji
