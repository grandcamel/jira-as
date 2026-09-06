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

    def test_real_has_all_public_mock_methods(self):
        """Mock-only APIs must not silently conceal missing real methods."""
        # Existing mock-only APIs found during JAS-5, outside its repair scope.
        # Keep exceptions explicit; new gaps (including get_my_permissions)
        # must fail this check. Remove names as their real methods are added.
        known_mock_only = {
            "add_actor_to_project_role",
            "add_attachment",
            "add_customers",
            "add_vote",
            "add_watcher",
            "adjust_remaining_estimate",
            "advanced_search",
            "count_issues",
            "create_field_option",
            "create_issue_link",
            "delete_field_option",
            "delete_issue_link",
            "export_search_results",
            "generate_branch_name",
            "generate_commit_message",
            "generate_pr_description",
            "get_agile_fields",
            "get_all_project_roles",
            "get_all_projects",
            "get_attachment",
            "get_backlog_issues",
            "get_blocked_by",
            "get_blockers",
            "get_board_configuration",
            "get_boards",
            "get_branches",
            "get_builds",
            "get_commits",
            "get_create_meta",
            "get_custom_fields",
            "get_customers",
            "get_deployments",
            "get_development_info",
            "get_development_status",
            "get_edit_meta",
            "get_epic_issues",
            "get_epic_link_field",
            "get_epics",
            "get_field",
            "get_field_configuration_items",
            "get_field_configurations",
            "get_field_options",
            "get_fields",
            "get_groups",
            "get_issue_activity",
            "get_issue_link",
            "get_issue_link_type",
            "get_issue_link_types",
            "get_issue_types_for_project",
            "get_issue_with_changelog",
            "get_priorities",
            "get_priority",
            "get_project_fields",
            "get_project_role",
            "get_project_worklogs",
            "get_pull_requests",
            "get_related_issues",
            "get_sprint_field",
            "get_sprints",
            "get_story_points_field",
            "get_system_fields",
            "get_time_report",
            "get_time_tracking_configuration",
            "get_user_mentions",
            "get_user_worklogs",
            "get_votes",
            "get_watchers",
            "get_worklog_ids_modified_since",
            "link_repository",
            "move_issues_to_epic",
            "notify_users",
            "parse_commit_message",
            "remove_actor_from_project_role",
            "remove_customers",
            "remove_issues_from_epic",
            "remove_vote",
            "remove_watcher",
            "search_fields",
            "search_issues_by_keys",
            "set_estimate",
            "set_filter_favourite",
            "set_time_tracking_configuration",
            "update_field_option",
            "validate_jql",
        }
        missing = (
            set(get_public_methods(MockJiraClient))
            - set(get_public_methods(JiraClient))
            - known_mock_only
        )
        assert not missing, f"JiraClient missing mock methods: {sorted(missing)}"

    def test_get_my_permissions_signature(self):
        real = get_method_signature(JiraClient, "get_my_permissions")
        mock = get_method_signature(MockJiraClient, "get_my_permissions")
        assert real is not None
        assert list(real.parameters) == list(mock.parameters)
        for name, param in real.parameters.items():
            assert param.default == mock.parameters[name].default
            assert param.kind == mock.parameters[name].kind
            assert normalize_annotation(param.annotation) == normalize_annotation(
                mock.parameters[name].annotation
            )

    def test_get_my_permissions_explicit_mock_filter(self):
        with MockJiraClient() as mock:
            result = mock.get_my_permissions(
                "DEMO", ["MANAGE_SPRINTS_PERMISSION", "BROWSE_PROJECTS"]
            )
        assert set(result) == {"permissions"}
        assert set(result["permissions"]) == {
            "MANAGE_SPRINTS_PERMISSION",
            "BROWSE_PROJECTS",
        }
        assert all(p["havePermission"] is True for p in result["permissions"].values())

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
        assert hasattr(JiraClient, method_name), f"JiraClient missing: {method_name}"
        message = f"MockJiraClient missing method: {method_name}"
        assert hasattr(MockJiraClient, method_name), message


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

    def test_get_all_boards_signature(self):
        """Mock get_all_boards mirrors the real client's leading parameters."""
        real_sig = get_method_signature(JiraClient, "get_all_boards")
        mock_sig = get_method_signature(MockJiraClient, "get_all_boards")

        real_params = [p for p in real_sig.parameters if p != "self"]
        mock_params = [p for p in mock_sig.parameters if p != "self"]

        # The real client's parameters must lead, in order, so positional and
        # keyword calls behave identically against either client.
        assert mock_params[: len(real_params)] == real_params
        # The legacy alias stays available for older callers.
        assert "project_key_or_id" in mock_params

    def test_get_all_boards_project_key_filters(self):
        """project_key filters mock boards the same way the alias does."""
        with MockJiraClient() as client:
            by_key = client.get_all_boards(project_key="DEMO")
            by_alias = client.get_all_boards(project_key_or_id="DEMO")

        assert by_key == by_alias
        assert by_key["values"], "expected seeded DEMO boards"

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


class TestReturnShapeParity:
    """Mock methods must return the same envelope shape as the real client."""

    ENVELOPE_METHODS = [
        "get_request_participants",
        "get_request_comments",
        "get_request_type_fields",
    ]

    @staticmethod
    def _container(annotation):
        """Reduce an annotation to its outer container name.

        Modules differ on whether annotations are strings (from __future__
        import annotations) or objects, so "dict[str, Any]" and
        "dict[str, typing.Any]" must compare equal.
        """
        text = normalize_annotation(annotation) or ""
        return text.replace("typing.", "").split("[")[0].strip().lower()

    @pytest.mark.parametrize("method_name", ENVELOPE_METHODS)
    def test_declared_return_types_match(self, method_name):
        """A mock returning a bare list where the client returns an envelope
        breaks every caller that unwraps 'values'."""
        real = get_method_signature(JiraClient, method_name)
        mock = get_method_signature(MockJiraClient, method_name)

        assert self._container(real.return_annotation) == self._container(
            mock.return_annotation
        ), f"{method_name}: mock return type differs from JiraClient"

    def test_participants_envelope_has_values(self):
        """The mock participants response is unwrappable like the real one."""
        with MockJiraClient() as client:
            response = client.get_request_participants("DEMOSD-1")

        assert isinstance(response, dict)
        assert isinstance(response["values"], list)

    def test_update_issue_accepts_notify_users(self):
        """The mock takes notify_users so --no-notify works in mock mode."""
        sig = get_method_signature(MockJiraClient, "update_issue")

        assert "notify_users" in sig.parameters


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
                    message = f"{method_name}: organization_id should be int"
                    assert annotation is int or "int" in str(annotation), message
