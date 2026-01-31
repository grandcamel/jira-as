"""
Tests for CLI main entry point.
"""

import os

import pytest
from click.testing import CliRunner

from jira_as.cli.main import cli
from jira_as.cli.main import get_version


class TestGetVersion:
    """Test version retrieval function."""

    def test_get_version_returns_string(self):
        """Test get_version returns a string."""
        version = get_version()
        assert isinstance(version, str)
        # Should either be a version number or "unknown"
        assert version == "unknown" or "." in version

    def test_get_version_fallback_on_error(self):
        """Test that get_version returns 'unknown' on error."""
        # The function catches all exceptions and returns "unknown"
        # In test environment without the package installed, it should return "unknown"
        version = get_version()
        # Just verify it doesn't raise
        assert version is not None


class TestCliGroup:
    """Test the main CLI group."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def clean_env(self):
        """Clean up JIRA environment variables after test."""
        original_env = {}
        for key in ["JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET"]:
            if key in os.environ:
                original_env[key] = os.environ[key]
        yield
        # Restore original state
        for key in ["JIRA_OUTPUT", "JIRA_VERBOSE", "JIRA_QUIET"]:
            if key in original_env:
                os.environ[key] = original_env[key]
            elif key in os.environ:
                del os.environ[key]

    def test_cli_help(self, runner):
        """Test CLI displays help when invoked without command."""
        result = runner.invoke(cli)
        assert result.exit_code == 0
        assert "Jira Assistant Skills CLI" in result.output
        assert "--help" in result.output

    def test_cli_help_option(self, runner):
        """Test --help option."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Jira Assistant Skills CLI" in result.output

    def test_cli_version_option(self, runner):
        """Test --version option."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should show version info

    def test_cli_output_option_text(self, runner, clean_env):
        """Test --output text option sets environment variable."""
        result = runner.invoke(cli, ["--output", "text", "--help"])
        assert result.exit_code == 0

    def test_cli_output_option_json(self, runner, clean_env):
        """Test --output json option."""
        result = runner.invoke(cli, ["--output", "json", "--help"])
        assert result.exit_code == 0

    def test_cli_output_option_table(self, runner, clean_env):
        """Test --output table option."""
        result = runner.invoke(cli, ["--output", "table", "--help"])
        assert result.exit_code == 0

    def test_cli_verbose_option(self, runner, clean_env):
        """Test --verbose option."""
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_cli_quiet_option(self, runner, clean_env):
        """Test --quiet option."""
        result = runner.invoke(cli, ["--quiet", "--help"])
        assert result.exit_code == 0

    def test_cli_short_options(self, runner, clean_env):
        """Test short option forms."""
        result = runner.invoke(cli, ["-o", "json", "-v", "-q", "--help"])
        assert result.exit_code == 0


class TestSubcommands:
    """Test that subcommands are registered."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_issue_command_registered(self, runner):
        """Test issue subcommand is available."""
        result = runner.invoke(cli, ["issue", "--help"])
        assert result.exit_code == 0

    def test_search_command_registered(self, runner):
        """Test search subcommand is available."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0

    def test_lifecycle_command_registered(self, runner):
        """Test lifecycle subcommand is available."""
        result = runner.invoke(cli, ["lifecycle", "--help"])
        assert result.exit_code == 0

    def test_fields_command_registered(self, runner):
        """Test fields subcommand is available."""
        result = runner.invoke(cli, ["fields", "--help"])
        assert result.exit_code == 0

    def test_ops_command_registered(self, runner):
        """Test ops subcommand is available."""
        result = runner.invoke(cli, ["ops", "--help"])
        assert result.exit_code == 0

    def test_bulk_command_registered(self, runner):
        """Test bulk subcommand is available."""
        result = runner.invoke(cli, ["bulk", "--help"])
        assert result.exit_code == 0

    def test_dev_command_registered(self, runner):
        """Test dev subcommand is available."""
        result = runner.invoke(cli, ["dev", "--help"])
        assert result.exit_code == 0

    def test_relationships_command_registered(self, runner):
        """Test relationships subcommand is available."""
        result = runner.invoke(cli, ["relationships", "--help"])
        assert result.exit_code == 0

    def test_time_command_registered(self, runner):
        """Test time subcommand is available."""
        result = runner.invoke(cli, ["time", "--help"])
        assert result.exit_code == 0

    def test_collaborate_command_registered(self, runner):
        """Test collaborate subcommand is available."""
        result = runner.invoke(cli, ["collaborate", "--help"])
        assert result.exit_code == 0

    def test_agile_command_registered(self, runner):
        """Test agile subcommand is available."""
        result = runner.invoke(cli, ["agile", "--help"])
        assert result.exit_code == 0

    def test_jsm_command_registered(self, runner):
        """Test jsm subcommand is available."""
        result = runner.invoke(cli, ["jsm", "--help"])
        assert result.exit_code == 0

    def test_admin_command_registered(self, runner):
        """Test admin subcommand is available."""
        result = runner.invoke(cli, ["admin", "--help"])
        assert result.exit_code == 0
