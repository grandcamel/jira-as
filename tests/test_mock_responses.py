"""
Tests for mock_responses backwards compatibility module.
"""



class TestMockResponsesBackwardsCompatibility:
    """Tests for backwards compatibility imports."""

    def test_import_mock_jira_client(self):
        """Test MockJiraClient is importable from mock_responses."""
        from jira_as.mock_responses import MockJiraClient

        assert MockJiraClient is not None

    def test_import_is_mock_mode(self):
        """Test is_mock_mode is importable from mock_responses."""
        from jira_as.mock_responses import is_mock_mode

        assert callable(is_mock_mode)

    def test_all_exports(self):
        """Test __all__ exports are correct."""
        from jira_as import mock_responses

        assert "MockJiraClient" in mock_responses.__all__
        assert "is_mock_mode" in mock_responses.__all__

    def test_same_as_mock_package(self):
        """Test mock_responses exports same objects as mock package."""
        from jira_as.mock import MockJiraClient as MC2
        from jira_as.mock import is_mock_mode as imm2
        from jira_as.mock_responses import MockJiraClient as MC1
        from jira_as.mock_responses import is_mock_mode as imm1

        assert MC1 is MC2
        assert imm1 is imm2
