"""Tests for JSM CLI commands."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from jira_as.cli.commands.jsm_cmds import (
    _format_approvals,  # Approval impl; Asset impl; Customer impl; KB impl; Organization impl; Participant impl; Queue impl; Request impl; SLA impl; Request Type impl; Helper functions; CLI commands
    _format_customers,
    _format_datetime,
    _format_kb_article,
    _format_organization,
    _format_organizations,
    _format_pending_approvals,
    _format_queue,
    _format_queues,
    _format_request,
    _format_request_types,
    _format_requests,
    _format_service_desk,
    _format_service_desks,
    _format_sla,
    _format_sla_breach_check,
    _format_sla_report_csv,
    _format_sla_report_text,
    _format_sla_time,
    _format_transitions,
    _get_approvals_impl,
    _get_request_comments_impl,
    _is_sla_breached,
    _parse_comma_list,
    _remove_participant_impl,
    _suggest_kb_impl,
    jsm,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client():
    """Mock JIRA client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client


@pytest.fixture
def sample_service_desks():
    """Sample service desks data."""
    return {
        "values": [
            {
                "id": "1",
                "projectId": "10001",
                "projectKey": "SD",
                "projectName": "Service Desk",
            },
            {
                "id": "2",
                "projectId": "10002",
                "projectKey": "IT",
                "projectName": "IT Support",
            },
        ],
        "size": 2,
    }


@pytest.fixture
def sample_request_types():
    """Sample request types data."""
    return {
        "values": [
            {
                "id": "1",
                "name": "Hardware Request",
                "description": "Request new hardware",
                "serviceDeskId": "1",
                "issueTypeId": "10001",
            },
            {
                "id": "2",
                "name": "Software Request",
                "description": "Request software installation",
                "serviceDeskId": "1",
                "issueTypeId": "10002",
            },
        ],
        "size": 2,
    }


@pytest.fixture
def sample_request():
    """Sample request data."""
    return {
        "issueKey": "SD-123",
        "serviceDeskId": "1",
        "requestType": {"name": "Hardware Request"},
        "currentStatus": {"status": "Open", "statusCategory": "To Do"},
        "requestFieldValues": [
            {"fieldId": "summary", "value": "Need new laptop"},
            {"fieldId": "description", "value": "My laptop is broken"},
        ],
        "reporter": {"emailAddress": "user@example.com"},
        "createdDate": {"friendly": "2024-01-15"},
        "_links": {
            "web": "https://example.atlassian.net/servicedesk/customer/portal/1/SD-123",
            "agent": "https://example.atlassian.net/browse/SD-123",
        },
    }


@pytest.fixture
def sample_customers():
    """Sample customers data."""
    return {
        "values": [
            {
                "accountId": "abc123",
                "displayName": "John Doe",
                "emailAddress": "john@example.com",
                "active": True,
            },
            {
                "accountId": "def456",
                "displayName": "Jane Smith",
                "emailAddress": "jane@example.com",
                "active": True,
            },
        ],
        "size": 2,
    }


@pytest.fixture
def sample_organizations():
    """Sample organizations data."""
    return {
        "values": [
            {"id": "1", "name": "Acme Corp"},
            {"id": "2", "name": "Beta Industries"},
        ],
        "size": 2,
    }


@pytest.fixture
def sample_queues():
    """Sample queues data."""
    return {
        "values": [
            {"id": "1", "name": "Unassigned", "jql": "assignee is EMPTY"},
            {"id": "2", "name": "My Queue", "jql": "assignee = currentUser()"},
        ],
        "size": 2,
    }


@pytest.fixture
def sample_sla_data():
    """Sample SLA data."""
    return {
        "values": [
            {
                "name": "Time to first response",
                "ongoingCycle": {
                    "breached": False,
                    "remainingTime": {"millis": 7200000},  # 2 hours
                },
            },
            {
                "name": "Time to resolution",
                "ongoingCycle": {
                    "breached": True,
                    "remainingTime": {"millis": -3600000},  # -1 hour (overdue)
                },
            },
        ],
    }


@pytest.fixture
def sample_approvals():
    """Sample approvals data."""
    return [
        {
            "id": "10001",
            "name": "Manager Approval",
            "status": "pending",
            "approvers": [{"displayName": "Manager User"}],
            "createdDate": "2024-01-15T10:00:00Z",
        },
    ]


@pytest.fixture
def sample_kb_articles():
    """Sample KB articles."""
    return [
        {
            "title": "How to reset password",
            "excerpt": "This article explains how to <em>reset</em> your password.",
            "_links": {"self": "https://example.com/kb/1"},
        },
        {
            "title": "VPN Setup Guide",
            "excerpt": "Instructions for setting up <em>VPN</em> connection.",
            "_links": {"self": "https://example.com/kb/2"},
        },
    ]


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestParseCommaList:
    """Tests for _parse_comma_list."""

    def test_parse_simple_list(self):
        """Test parsing simple comma-separated list."""
        result = _parse_comma_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_with_spaces(self):
        """Test parsing list with spaces."""
        result = _parse_comma_list("a, b , c")
        assert result == ["a", "b", "c"]

    def test_parse_single_value(self):
        """Test parsing single value."""
        result = _parse_comma_list("single")
        assert result == ["single"]

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = _parse_comma_list("")
        assert result == []

    def test_parse_with_empty_values(self):
        """Test parsing list with empty values."""
        result = _parse_comma_list("a,,b, ,c")
        assert result == ["a", "b", "c"]


class TestFormatDatetime:
    """Tests for _format_datetime."""

    def test_format_iso_datetime(self):
        """Test formatting ISO datetime."""
        result = _format_datetime("2024-01-15T10:30:00Z")
        assert result == "2024-01-15 10:30"

    def test_format_empty_string(self):
        """Test formatting empty string."""
        result = _format_datetime("")
        assert result == "Unknown"

    def test_format_invalid_string(self):
        """Test formatting invalid string (truncates)."""
        result = _format_datetime("some invalid date string")
        assert result == "some invalid dat"


class TestFormatSlaTime:
    """Tests for _format_sla_time."""

    def test_format_hours_and_minutes(self):
        """Test formatting hours and minutes."""
        result = _format_sla_time(7200000)  # 2 hours
        assert result == "2h 0m"

    def test_format_minutes_only(self):
        """Test formatting minutes only."""
        result = _format_sla_time(1800000)  # 30 minutes
        assert result == "30m"

    def test_format_negative_overdue(self):
        """Test formatting negative (overdue)."""
        result = _format_sla_time(-3600000)
        assert result == "Overdue"


class TestIsSlaBreached:
    """Tests for _is_sla_breached."""

    def test_ongoing_breached(self):
        """Test ongoing cycle breached."""
        sla = {"ongoingCycle": {"breached": True}}
        assert _is_sla_breached(sla) is True

    def test_ongoing_not_breached(self):
        """Test ongoing cycle not breached."""
        sla = {"ongoingCycle": {"breached": False}}
        assert _is_sla_breached(sla) is False

    def test_completed_breached(self):
        """Test completed cycle breached."""
        sla = {"completedCycles": [{"breached": True}]}
        assert _is_sla_breached(sla) is True

    def test_no_breach(self):
        """Test no breach."""
        sla = {"ongoingCycle": {"breached": False}, "completedCycles": []}
        assert _is_sla_breached(sla) is False


# =============================================================================
# Service Desk Formatting Tests
# =============================================================================


class TestFormatServiceDesks:
    """Tests for _format_service_desks."""

    def test_format_service_desks(self, sample_service_desks):
        """Test formatting service desks."""
        result = _format_service_desks(sample_service_desks)
        assert "Available Service Desks:" in result
        assert "SD" in result
        assert "IT Support" in result
        assert "Total: 2 service desks" in result

    def test_format_empty_service_desks(self):
        """Test formatting empty service desks."""
        result = _format_service_desks({"values": []})
        assert "No service desks found" in result


class TestFormatServiceDesk:
    """Tests for _format_service_desk."""

    def test_format_single_service_desk(self):
        """Test formatting single service desk."""
        sd = {
            "id": "1",
            "projectId": "10001",
            "projectKey": "SD",
            "projectName": "Service Desk",
        }
        result = _format_service_desk(sd)
        assert "Service Desk Details:" in result
        assert "ID:           1" in result
        assert "Project Key:  SD" in result


# =============================================================================
# Request Type Formatting Tests
# =============================================================================


class TestFormatRequestTypes:
    """Tests for _format_request_types."""

    def test_format_request_types(self, sample_request_types):
        """Test formatting request types."""
        result = _format_request_types(sample_request_types)
        assert "Request Types:" in result
        assert "Hardware Request" in result
        assert "Software Request" in result
        assert "Total: 2 request types" in result

    def test_format_request_types_with_issue_types(self, sample_request_types):
        """Test formatting request types with issue types."""
        result = _format_request_types(sample_request_types, show_issue_types=True)
        assert "Issue Type" in result

    def test_format_empty_request_types(self):
        """Test formatting empty request types."""
        result = _format_request_types({"values": []})
        assert "No request types found" in result


# =============================================================================
# Request Formatting Tests
# =============================================================================


class TestFormatRequests:
    """Tests for _format_requests."""

    def test_format_requests(self):
        """Test formatting request list."""
        issues = [
            {
                "key": "SD-123",
                "fields": {
                    "summary": "Test issue",
                    "status": {"name": "Open"},
                    "reporter": {"emailAddress": "user@example.com"},
                },
            }
        ]
        result = _format_requests(issues)
        assert "SD-123" in result
        assert "Test issue" in result
        assert "Open" in result

    def test_format_empty_requests(self):
        """Test formatting empty requests."""
        result = _format_requests([])
        assert "No requests found" in result


class TestFormatRequest:
    """Tests for _format_request."""

    def test_format_request(self, sample_request):
        """Test formatting single request."""
        result = _format_request(sample_request)
        assert "Request: SD-123" in result
        assert "Need new laptop" in result
        assert "Hardware Request" in result
        assert "Open" in result

    def test_format_request_with_sla(self, sample_request, sample_sla_data):
        """Test formatting request with SLA data."""
        request = {**sample_request, "sla": sample_sla_data}
        result = _format_request(request)
        assert "SLA Information:" in result


class TestFormatTransitions:
    """Tests for _format_transitions."""

    def test_format_transitions(self):
        """Test formatting transitions."""
        transitions = [
            {"id": "11", "name": "Start Progress", "to": {"name": "In Progress"}},
            {"id": "21", "name": "Resolve", "to": {"name": "Resolved"}},
        ]
        result = _format_transitions(transitions)
        assert "Start Progress" in result
        assert "In Progress" in result


# =============================================================================
# Customer and Organization Formatting Tests
# =============================================================================


class TestFormatCustomers:
    """Tests for _format_customers."""

    def test_format_customers(self, sample_customers):
        """Test formatting customers."""
        result = _format_customers(sample_customers)
        assert "Customers:" in result
        assert "john@example.com" in result
        assert "John Doe" in result
        assert "Total: 2 customers" in result

    def test_format_empty_customers(self):
        """Test formatting empty customers."""
        result = _format_customers({"values": []})
        assert "No customers found" in result


class TestFormatOrganizations:
    """Tests for _format_organizations."""

    def test_format_organizations(self, sample_organizations):
        """Test formatting organizations."""
        result = _format_organizations(sample_organizations)
        assert "Organizations:" in result
        assert "Acme Corp" in result
        assert "Beta Industries" in result
        assert "Total: 2 organization(s)" in result

    def test_format_empty_organizations(self):
        """Test formatting empty organizations."""
        result = _format_organizations({"values": []})
        assert "No organizations found" in result


class TestFormatOrganization:
    """Tests for _format_organization."""

    def test_format_organization(self):
        """Test formatting single organization."""
        org = {"id": "1", "name": "Acme Corp"}
        result = _format_organization(org)
        assert "Organization Details:" in result
        assert "ID:   1" in result
        assert "Name: Acme Corp" in result


# =============================================================================
# Queue Formatting Tests
# =============================================================================


class TestFormatQueues:
    """Tests for _format_queues."""

    def test_format_queues(self, sample_queues):
        """Test formatting queues."""
        result = _format_queues(sample_queues)
        assert "Queues: 2 total" in result
        assert "Unassigned" in result
        assert "My Queue" in result

    def test_format_queues_with_jql(self, sample_queues):
        """Test formatting queues with JQL."""
        result = _format_queues(sample_queues, show_jql=True)
        assert "JQL:" in result
        assert "assignee is EMPTY" in result


class TestFormatQueue:
    """Tests for _format_queue."""

    def test_format_queue(self):
        """Test formatting single queue."""
        queue = {"id": "1", "name": "Unassigned", "jql": "assignee is EMPTY"}
        result = _format_queue(queue)
        assert "Queue: Unassigned" in result
        assert "ID: 1" in result


# =============================================================================
# SLA Formatting Tests
# =============================================================================


class TestFormatSla:
    """Tests for _format_sla."""

    def test_format_sla(self, sample_sla_data):
        """Test formatting SLA data."""
        result = _format_sla(sample_sla_data)
        assert "SLA Information:" in result
        assert "Time to first response" in result
        assert "2h 0m remaining" in result
        assert "BREACHED" in result

    def test_format_empty_sla(self):
        """Test formatting empty SLA data."""
        result = _format_sla({"values": []})
        assert "No SLA information available" in result


class TestFormatSlaBreachCheck:
    """Tests for _format_sla_breach_check."""

    def test_format_breach_check(self):
        """Test formatting SLA breach check."""
        result_data = {
            "issue_key": "SD-123",
            "breached": ["Time to resolution"],
            "at_risk": ["Time to response"],
            "ok": ["Time to acknowledge"],
        }
        result = _format_sla_breach_check(result_data)
        assert "SLA Breach Check for SD-123" in result
        assert "BREACHED SLAs:" in result
        assert "AT RISK" in result
        assert "OK:" in result


class TestFormatSlaReport:
    """Tests for SLA report formatting."""

    def test_format_sla_report_text(self):
        """Test formatting SLA report as text."""
        report = {
            "total_issues": 10,
            "total_slas": 20,
            "report_data": [
                {
                    "issue_key": "SD-123",
                    "summary": "Test issue",
                    "sla": {
                        "name": "Time to response",
                        "ongoingCycle": {"breached": False},
                    },
                }
            ],
        }
        result = _format_sla_report_text(report)
        assert "SLA Compliance Report" in result
        assert "Total Issues: 10" in result
        assert "SD-123" in result

    def test_format_sla_report_csv(self):
        """Test formatting SLA report as CSV."""
        report = {
            "total_issues": 1,
            "total_slas": 1,
            "report_data": [
                {
                    "issue_key": "SD-123",
                    "summary": "Test issue",
                    "sla": {
                        "name": "Time to response",
                        "ongoingCycle": {"breached": True},
                    },
                }
            ],
        }
        result = _format_sla_report_csv(report)
        assert "Request Key,Summary,SLA Name,Breached" in result
        assert "SD-123" in result
        assert "Yes" in result


# =============================================================================
# Approval Formatting Tests
# =============================================================================


class TestFormatApprovals:
    """Tests for _format_approvals."""

    def test_format_approvals(self, sample_approvals):
        """Test formatting approvals."""
        result = _format_approvals(sample_approvals, "SD-123")
        assert "Approvals for SD-123" in result
        assert "Manager Approval" in result
        assert "pending" in result

    def test_format_empty_approvals(self):
        """Test formatting empty approvals."""
        result = _format_approvals([], "SD-123")
        assert "No approvals found" in result


class TestFormatPendingApprovals:
    """Tests for _format_pending_approvals."""

    def test_format_pending_approvals(self):
        """Test formatting pending approvals."""
        approvals = [
            {
                "issueKey": "SD-123",
                "id": "10001",
                "name": "Manager Approval",
                "createdDate": "2024-01-15T10:00:00Z",
            }
        ]
        result = _format_pending_approvals(approvals)
        assert "Pending Approvals:" in result
        assert "SD-123" in result
        assert "Manager Approval" in result

    def test_format_empty_pending(self):
        """Test formatting empty pending approvals."""
        result = _format_pending_approvals([])
        assert "No pending approvals found" in result


# =============================================================================
# KB Formatting Tests
# =============================================================================


class TestFormatKbArticle:
    """Tests for _format_kb_article."""

    def test_format_kb_article(self):
        """Test formatting KB article."""
        article = {
            "title": "Password Reset Guide",
            "body": {"content": "Here's how to reset your password..."},
        }
        result = _format_kb_article(article)
        assert "KB Article: Password Reset Guide" in result
        assert "Here's how to reset" in result


# =============================================================================
# Asset Formatting Tests
# =============================================================================


# =============================================================================
# Participant Formatting Tests
# =============================================================================


# =============================================================================
# CLI Command Tests
# =============================================================================


class TestRequestTransitionCommand:
    """Tests for request transition command."""

    def test_show_transitions(self, generic_workflow, runner):
        result = runner.invoke(
            jsm,
            [
                "request",
                "transition",
                "SBX-1",
                "--show-transitions",
                "--transport",
                "simulation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Done" in result.output
        assert [call[0] for call in generic_workflow.calls] == [
            "getCustomerTransitions"
        ]

    def test_transition_dry_run(self, generic_workflow, runner):
        before = generic_workflow.snapshot()
        result = runner.invoke(
            jsm,
            [
                "request",
                "transition",
                "SBX-1",
                "--to",
                "Done",
                "--dry-run",
                "--transport",
                "simulation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert '"dry_run": true' in result.output
        assert generic_workflow.snapshot() == before


class TestSlaReportCommand:
    """Tests for sla report command."""

    def test_sla_report_missing_args(self, generic_workflow, runner):
        result = runner.invoke(jsm, ["sla", "report"])
        assert result.exit_code == 1
        assert "--project or scoped --jql is required" in result.output
        assert generic_workflow.calls == []


# =============================================================================
# Tests for servicedeskapi envelope handling and repaired client calls
# =============================================================================


@pytest.fixture
def spec_client():
    """MagicMock bound to the real JiraClient attribute surface."""
    from jira_as import JiraClient

    client = MagicMock(spec=JiraClient)
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client


class TestServiceDeskApiEnvelopes:
    """The servicedeskapi wraps collections in {'values': [...]}."""

    def test_comments_are_unwrapped(self, spec_client):
        """'request comments' returns the list, not the envelope."""
        spec_client.get_request_comments.return_value = {
            "size": 1,
            "isLastPage": True,
            "values": [{"id": "1", "body": "hi", "public": True}],
        }

        result = _get_request_comments_impl("SD-1", client=spec_client)

        assert result == [{"id": "1", "body": "hi", "public": True}]

    def test_comments_honour_public_only(self, spec_client):
        """--public-only asks the API for public comments."""
        spec_client.get_request_comments.return_value = {"values": []}

        _get_request_comments_impl("SD-1", public_only=True, client=spec_client)

        spec_client.get_request_comments.assert_called_once_with("SD-1", public=True)

    def test_comments_honour_internal_only(self, spec_client):
        """--internal-only was previously ignored; it now filters."""
        spec_client.get_request_comments.return_value = {"values": []}

        _get_request_comments_impl("SD-1", internal_only=True, client=spec_client)

        spec_client.get_request_comments.assert_called_once_with("SD-1", public=False)

    def test_comments_default_to_all(self, spec_client):
        """With neither flag, no visibility filter is sent."""
        spec_client.get_request_comments.return_value = {"values": []}

        _get_request_comments_impl("SD-1", client=spec_client)

        spec_client.get_request_comments.assert_called_once_with("SD-1", public=None)

    def test_approvals_are_unwrapped(self, spec_client):
        """'approval list' returns the list, not the envelope."""
        spec_client.get_request_approvals.return_value = {
            "values": [{"id": "1", "name": "Manager Approval"}]
        }

        assert _get_approvals_impl("SD-1", client=spec_client) == [
            {"id": "1", "name": "Manager Approval"}
        ]

    def test_remove_participant_uses_plural_client_method(self, spec_client):
        """The client method is remove_request_participants and takes a list."""
        _remove_participant_impl("SD-1", "abc123", client=spec_client)

        spec_client.remove_request_participants.assert_called_once_with(
            "SD-1", account_ids=["abc123"]
        )

    def test_kb_suggest_uses_existing_client_method(self, spec_client):
        """suggest_kb_articles does not exist; suggest_kb_for_request does."""
        spec_client.suggest_kb_for_request.return_value = []

        _suggest_kb_impl("SD-1", max_results=3, client=spec_client)

        spec_client.suggest_kb_for_request.assert_called_once_with("SD-1", 3)


@pytest.fixture
def generic_workflow(tmp_path, monkeypatch):
    from as_engine.simulation import JiraSimulationStore

    from jira_as import engine
    from jira_as.autocomplete_cache import InstanceFieldsCache

    monkeypatch.setenv("JIRA_ALLOWED_PROJECTS", "SBX")
    monkeypatch.setenv("JIRA_ALLOW_SITE_OPERATIONS", "true")
    monkeypatch.setenv("JIRA_FIELDS_CACHE_DIR", str(tmp_path))
    seed = JiraSimulationStore().snapshot()
    seed["sprints"] = [
        {"id": 456, "originBoardId": 1, "name": "Sprint 456", "state": "future"},
        {"id": 457, "originBoardId": 1, "name": "Closed", "state": "closed"},
    ]
    seed["issues"][0]["fields"].update(
        {"sprint": 457, "status": {"name": "Done"}, "customfield_10016": 8}
    )
    store = JiraSimulationStore(seed)
    surface = engine.create_surface(transport="simulation", store=store)
    monkeypatch.setattr(engine, "create_surface", lambda **_: surface)
    InstanceFieldsCache(tmp_path).write(store.fields)
    return store
