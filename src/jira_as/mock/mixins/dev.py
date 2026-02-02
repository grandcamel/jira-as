"""Dev mixin for MockJiraClient.

Provides mock implementations for development panel, git integration,
branch names, and commit associations.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class DevMixin(_Base):
    """Mixin providing development integration functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self.base_url: str
    """

    # =========================================================================
    # Development Info Operations
    # =========================================================================

    def get_development_info(self, issue_key: str) -> dict[str, Any]:
        """Get development information for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Development information including commits, branches, PRs.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        # Return mock development data
        return {
            "detail": [
                {
                    "instanceType": "GitHub",
                    "repository": {
                        "name": "demo-project",
                        "url": "https://github.com/example/demo-project",
                    },
                    "branches": [
                        {
                            "name": f"feature/{issue_key.lower()}-mock-branch",
                            "url": f"https://github.com/example/demo-project/tree/feature/{issue_key.lower()}-mock-branch",
                            "createPullRequestUrl": f"https://github.com/example/demo-project/compare/feature/{issue_key.lower()}-mock-branch?expand=1",
                        }
                    ],
                    "pullRequests": [],
                    "commits": [],
                }
            ],
            "errors": [],
        }

    def get_commits(self, issue_key: str) -> list[dict[str, Any]]:
        """Get commits associated with an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of commits.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return [
            {
                "id": "abc123def456",
                "displayId": "abc123d",
                "authorTimestamp": "2025-01-01T10:00:00+0000",
                "author": {
                    "name": "Jason Krueger",
                    "email": "jasonkrue@gmail.com",
                },
                "message": f"{issue_key}: Initial implementation",
                "url": "https://github.com/example/demo-project/commit/abc123def456",
                "files": [
                    {"path": "src/main.py", "changeType": "MODIFIED"},
                ],
            },
        ]

    def get_branches(self, issue_key: str) -> list[dict[str, Any]]:
        """Get branches associated with an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of branches.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return [
            {
                "name": f"feature/{issue_key.lower()}-mock-branch",
                "url": f"https://github.com/example/demo-project/tree/feature/{issue_key.lower()}-mock-branch",
                "repository": {
                    "name": "demo-project",
                    "url": "https://github.com/example/demo-project",
                },
                "lastCommit": {
                    "id": "abc123def456",
                    "message": f"{issue_key}: Latest changes",
                },
            },
        ]

    def get_pull_requests(self, issue_key: str) -> list[dict[str, Any]]:
        """Get pull requests associated with an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of pull requests.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return [
            {
                "id": "1",
                "title": f"{issue_key}: Implement feature",
                "status": "OPEN",
                "url": "https://github.com/example/demo-project/pull/1",
                "author": {
                    "name": "Jason Krueger",
                    "email": "jasonkrue@gmail.com",
                },
                "source": {
                    "branch": f"feature/{issue_key.lower()}-mock-branch",
                    "repository": "demo-project",
                },
                "destination": {
                    "branch": "main",
                    "repository": "demo-project",
                },
                "reviewers": [],
                "commentCount": 0,
            },
        ]

    # =========================================================================
    # Branch Name Generation
    # =========================================================================

    def generate_branch_name(
        self,
        issue_key: str,
        prefix: str = "feature",
        include_summary: bool = True,
        max_length: int = 50,
    ) -> str:
        """Generate a branch name for an issue.

        Args:
            issue_key: The issue key.
            prefix: Branch prefix (e.g., 'feature', 'bugfix', 'hotfix').
            include_summary: Whether to include issue summary in branch name.
            max_length: Maximum length of the branch name.

        Returns:
            Generated branch name.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        issue = self._issues[issue_key]
        branch_parts = [prefix, issue_key.lower()]

        if include_summary:
            summary = issue["fields"].get("summary", "")
            # Sanitize summary for branch name
            sanitized = self._sanitize_branch_name(summary)
            if sanitized:
                branch_parts.append(sanitized)

        branch_name = (
            "/".join(branch_parts[:2]) + "-" + "-".join(branch_parts[2:])
            if len(branch_parts) > 2
            else "/".join(branch_parts)
        )

        # Truncate if too long
        if len(branch_name) > max_length:
            branch_name = branch_name[:max_length].rstrip("-")

        return branch_name

    def _sanitize_branch_name(self, text: str) -> str:
        """Sanitize text for use in branch name.

        Args:
            text: Text to sanitize.

        Returns:
            Sanitized text safe for branch names.
        """
        import re

        # Convert to lowercase
        text = text.lower()
        # Replace spaces and special chars with hyphens
        text = re.sub(r"[^a-z0-9]+", "-", text)
        # Remove leading/trailing hyphens
        text = text.strip("-")
        # Collapse multiple hyphens
        text = re.sub(r"-+", "-", text)
        return text

    # =========================================================================
    # Commit Message Generation
    # =========================================================================

    def generate_commit_message(
        self,
        issue_key: str,
        message: str,
        include_type: bool = True,
    ) -> str:
        """Generate a commit message with issue reference.

        Args:
            issue_key: The issue key.
            message: The commit message body.
            include_type: Whether to include issue type as prefix.

        Returns:
            Formatted commit message.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        issue = self._issues[issue_key]

        if include_type:
            issue_type = issue["fields"]["issuetype"]["name"].lower()
            type_prefix = {
                "bug": "fix",
                "story": "feat",
                "epic": "feat",
                "task": "chore",
            }.get(issue_type, "chore")
            return f"{type_prefix}({issue_key}): {message}"
        else:
            return f"{issue_key}: {message}"

    def parse_commit_message(self, message: str) -> dict[str, Any]:
        """Parse a commit message to extract issue keys.

        Args:
            message: The commit message to parse.

        Returns:
            Parsed commit information including issue keys.
        """
        import re

        # Find issue keys in message (e.g., DEMO-123, DEMOSD-1)
        issue_keys = re.findall(r"[A-Z]+-\d+", message)

        # Parse conventional commit format
        conventional_match = re.match(
            r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?:\s*(?P<description>.+)$",
            message.split("\n")[0],
        )

        result = {
            "issueKeys": list(set(issue_keys)),
            "raw": message,
        }

        if conventional_match:
            result["type"] = conventional_match.group("type")
            result["scope"] = conventional_match.group("scope")
            result["description"] = conventional_match.group("description")

        return result

    # =========================================================================
    # PR Description Generation
    # =========================================================================

    def generate_pr_description(
        self,
        issue_key: str,
        changes_summary: str | None = None,
        include_checklist: bool = True,
    ) -> str:
        """Generate a pull request description for an issue.

        Args:
            issue_key: The issue key.
            changes_summary: Summary of changes (optional).
            include_checklist: Whether to include a review checklist.

        Returns:
            Formatted PR description.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        issue = self._issues[issue_key]
        summary = issue["fields"].get("summary", "No summary")
        issue_type = issue["fields"]["issuetype"]["name"]

        lines = [
            f"## {issue_type}: {summary}",
            "",
            f"**Issue:** [{issue_key}]({self.base_url}/browse/{issue_key})",
            "",
        ]

        if changes_summary:
            lines.extend(
                [
                    "## Changes",
                    "",
                    changes_summary,
                    "",
                ]
            )

        if include_checklist:
            lines.extend(
                [
                    "## Checklist",
                    "",
                    "- [ ] Tests added/updated",
                    "- [ ] Documentation updated",
                    "- [ ] Code reviewed",
                    "- [ ] Ready for merge",
                ]
            )

        return "\n".join(lines)

    # =========================================================================
    # Development Status Operations
    # =========================================================================

    def get_development_status(self, issue_key: str) -> dict[str, Any]:
        """Get development status summary for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Summary of development activity.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return {
            "issueKey": issue_key,
            "hasDevInfo": True,
            "branches": 1,
            "commits": 1,
            "pullRequests": 1,
            "openPRs": 1,
            "mergedPRs": 0,
            "declinedPRs": 0,
        }

    def link_repository(
        self,
        project_key: str,
        repository_url: str,
        repository_name: str | None = None,
    ) -> dict[str, Any]:
        """Link a repository to a project (mock).

        Args:
            project_key: The project key.
            repository_url: URL of the repository.
            repository_name: Display name for the repository.

        Returns:
            The linked repository information.
        """
        return {
            "id": "1",
            "name": repository_name or "demo-project",
            "url": repository_url,
            "projectKey": project_key,
        }

    # =========================================================================
    # Build Integration Operations
    # =========================================================================

    def get_builds(self, issue_key: str) -> list[dict[str, Any]]:
        """Get builds associated with an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of builds.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return [
            {
                "id": "build-1",
                "pipelineId": "pipeline-1",
                "displayName": "CI Build #42",
                "url": "https://ci.example.com/builds/42",
                "state": "successful",
                "lastUpdated": "2025-01-08T10:00:00+0000",
                "references": [
                    {"commit": {"id": "abc123def456"}},
                ],
            },
        ]

    def get_deployments(self, issue_key: str) -> list[dict[str, Any]]:
        """Get deployments associated with an issue.

        Args:
            issue_key: The issue key.

        Returns:
            List of deployments.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return [
            {
                "deploymentSequenceNumber": 1,
                "updateSequenceNumber": 1,
                "displayName": "Production Deploy #10",
                "url": "https://deploy.example.com/deployments/10",
                "description": "Deployed to production",
                "lastUpdated": "2025-01-08T12:00:00+0000",
                "state": "successful",
                "pipeline": {
                    "id": "pipeline-1",
                    "displayName": "Deploy Pipeline",
                },
                "environment": {
                    "id": "env-prod",
                    "displayName": "Production",
                    "type": "production",
                },
            },
        ]
