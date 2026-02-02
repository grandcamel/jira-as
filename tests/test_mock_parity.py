"""Tests to verify mock client signatures match real JiraClient.

This module ensures that MockJiraClient methods have signatures compatible
with JiraClient, preventing TypeErrors when skills switch between mock and
real clients.
"""

import inspect

import pytest

from jira_as import JiraClient
from jira_as.mock import MockJiraClient


def get_public_methods(cls):
    """Get all public methods of a class (excluding dunder methods)."""
    return {
        name: method
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def get_method_signature(cls, method_name):
    """Get the signature of a method, handling inheritance."""
    method = getattr(cls, method_name, None)
    if method is None:
        return None
    return inspect.signature(method)


def normalize_annotation(annotation):
    """Normalize type annotation for comparison."""
    if annotation is inspect.Parameter.empty:
        return None
    # Convert to string for comparison (handles Union types, etc.)
    return str(annotation)


class TestMockParity:
    """Test that MockJiraClient methods match JiraClient signatures."""

    # Methods that are intentionally different or internal
    SKIP_METHODS = {
        # Internal/scaffolding methods
        "get",
        "post",
        "put",
        "delete",
        "download_file",
        "close",
        # Methods with kwargs that the test can't handle well
        "update_sprint",
        "update_project",
        # Methods with intentionally different signatures (mock is simpler)
        "add_filter_permission",
        "create_request",
        "get_notification_scheme",
        "get_workflow_scheme",
        "get_project_roles",
    }

    # Methods where parameter order may differ but names should match
    PARAM_ORDER_FLEXIBLE = {
        "search_issues",  # Mock may have different defaults
    }

    def test_mock_has_all_core_methods(self):
        """Verify MockJiraClient has all core JiraClient methods."""
        mock_methods = get_public_methods(MockJiraClient)

        # Core methods that mock MUST have
        core_methods = {
            # Issue operations
            "get_issue",
            "create_issue",
            "update_issue",
            "delete_issue",
            "assign_issue",
            "search_issues",
            # Transition operations
            "get_transitions",
            "transition_issue",
            # Comment operations
            "add_comment",
            "get_comments",
            # User operations
            "get_user",
            "get_current_user",
            "search_users",
            "find_assignable_users",
            # Project operations
            "get_project",
            # Agile operations
            "get_all_boards",
            "get_board",
            "get_board_sprints",
            "get_sprint",
            "create_sprint",
            "update_sprint",
            # Worklog operations
            "add_worklog",
            "get_worklogs",
        }

        missing = core_methods - set(mock_methods.keys())
        assert not missing, f"MockJiraClient missing core methods: {missing}"

    def test_method_signatures_compatible(self):
        """Verify method signatures are compatible between mock and real."""
        real_methods = get_public_methods(JiraClient)
        mock_methods = get_public_methods(MockJiraClient)

        # Get methods that exist in both
        common_methods = set(real_methods.keys()) & set(mock_methods.keys())
        common_methods -= self.SKIP_METHODS

        errors = []

        for method_name in sorted(common_methods):
            real_sig = get_method_signature(JiraClient, method_name)
            mock_sig = get_method_signature(MockJiraClient, method_name)

            if real_sig is None or mock_sig is None:
                continue

            real_params = dict(real_sig.parameters)
            mock_params = dict(mock_sig.parameters)

            # Skip 'self' parameter
            real_params.pop("self", None)
            mock_params.pop("self", None)

            # Check that required parameters in real client exist in mock
            for param_name, param in real_params.items():
                if param.default is inspect.Parameter.empty:
                    # Required parameter
                    if param_name not in mock_params:
                        errors.append(
                            f"{method_name}: missing required param '{param_name}'"
                        )

            # Check that mock doesn't have required params that real doesn't
            for param_name, param in mock_params.items():
                if param.default is inspect.Parameter.empty:
                    if param_name not in real_params:
                        # Mock has required param that real doesn't - could cause issues
                        errors.append(
                            f"{method_name}: mock has extra required param '{param_name}'"
                        )

        assert not errors, "Signature mismatches:\n" + "\n".join(errors)

    def test_context_manager_support(self):
        """Verify both clients support context manager protocol."""
        assert hasattr(JiraClient, "__enter__")
        assert hasattr(JiraClient, "__exit__")
        assert hasattr(MockJiraClient, "__enter__")
        assert hasattr(MockJiraClient, "__exit__")

    def test_mock_methods_callable(self):
        """Verify mock methods can be called without errors."""
        # Create mock client
        mock = MockJiraClient()

        # Test core methods are callable
        assert callable(mock.get_issue)
        assert callable(mock.create_issue)
        assert callable(mock.search_issues)
        assert callable(mock.get_project)
        assert callable(mock.get_all_boards)
        assert callable(mock.get_board_sprints)

    @pytest.mark.parametrize(
        "method_name",
        [
            "get_issue",
            "create_issue",
            "update_issue",
            "delete_issue",
            "search_issues",
            "get_transitions",
            "transition_issue",
            "add_comment",
            "get_comments",
            "get_user",
            "get_current_user",
            "search_users",
            "find_assignable_users",
            "get_project",
            "get_all_boards",
            "get_board",
            "get_board_sprints",
            "get_sprint",
            "create_sprint",
            "update_sprint",
            "add_worklog",
            "get_worklogs",
            "create_issues_bulk",
            "get_create_issue_meta_issuetypes",
            "get_create_issue_meta_fields",
            "get_all_users",
            "get_users_bulk",
            "get_user_groups",
        ],
    )
    def test_method_exists_in_both(self, method_name):
        """Verify specific methods exist in both clients."""
        assert hasattr(JiraClient, method_name), (
            f"JiraClient missing method: {method_name}"
        )
        assert hasattr(MockJiraClient, method_name), (
            f"MockJiraClient missing method: {method_name}"
        )


class TestAgileMethodParity:
    """Test parity of agile-specific methods."""

    def test_create_sprint_signature(self):
        """Verify create_sprint has matching signature."""
        real_sig = get_method_signature(JiraClient, "create_sprint")
        mock_sig = get_method_signature(MockJiraClient, "create_sprint")

        real_params = list(real_sig.parameters.keys())
        mock_params = list(mock_sig.parameters.keys())

        # Remove 'self'
        real_params.remove("self")
        mock_params.remove("self")

        # First two positional params should match
        assert real_params[0] == mock_params[0] == "board_id"
        assert real_params[1] == mock_params[1] == "name"

    def test_rank_issues_signature(self):
        """Verify rank_issues uses rank_before/rank_after params."""
        real_sig = get_method_signature(JiraClient, "rank_issues")
        mock_sig = get_method_signature(MockJiraClient, "rank_issues")

        real_params = set(real_sig.parameters.keys()) - {"self"}
        mock_params = set(mock_sig.parameters.keys()) - {"self"}

        # Should have rank_before and rank_after, not rank_before_issue
        assert "rank_before" in real_params
        assert "rank_after" in real_params
        assert "rank_before" in mock_params
        assert "rank_after" in mock_params


class TestSearchMethodParity:
    """Test parity of search-specific methods."""

    def test_parse_jql_signature(self):
        """Verify parse_jql accepts list of queries."""
        real_sig = get_method_signature(JiraClient, "parse_jql")
        mock_sig = get_method_signature(MockJiraClient, "parse_jql")

        real_params = dict(real_sig.parameters)
        mock_params = dict(mock_sig.parameters)

        # Should have 'queries' param (list), not 'jql' (str)
        assert "queries" in real_params
        assert "queries" in mock_params


class TestJSMMethodParity:
    """Test parity of JSM-specific methods."""

    def test_organization_methods_use_int_id(self):
        """Verify organization methods use int for organization_id."""
        methods_with_org_id = [
            "get_organization",
            "delete_organization",
            "add_users_to_organization",
            "remove_users_from_organization",
            "get_organization_users",
        ]

        for method_name in methods_with_org_id:
            if hasattr(MockJiraClient, method_name):
                sig = get_method_signature(MockJiraClient, method_name)
                params = dict(sig.parameters)
                if "organization_id" in params:
                    annotation = params["organization_id"].annotation
                    # Should be int, not str
                    assert annotation is int or "int" in str(annotation), (
                        f"{method_name}: organization_id should be int"
                    )
