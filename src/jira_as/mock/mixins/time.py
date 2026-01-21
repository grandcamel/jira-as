"""Time tracking mixin for MockJiraClient.

Provides mock implementations for worklogs, time estimates, and time tracking configuration.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class TimeTrackingMixin(_Base):
    """Mixin providing time tracking functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self._worklogs: Dict[str, List[Dict]]
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Time Tracking Configuration
    # =========================================================================

    TIME_TRACKING_CONFIG: ClassVar[dict[str, Any]] = {
        "workingHoursPerDay": 8.0,
        "workingDaysPerWeek": 5.0,
        "timeFormat": "pretty",
        "defaultUnit": "minute",
    }

    # =========================================================================
    # Time Tracking Configuration Operations
    # =========================================================================

    def get_time_tracking_configuration(self) -> dict[str, Any]:
        """Get time tracking configuration.

        Returns:
            Time tracking configuration settings.
        """
        return self.TIME_TRACKING_CONFIG

    def set_time_tracking_configuration(
        self,
        working_hours_per_day: float | None = None,
        working_days_per_week: float | None = None,
        time_format: str | None = None,
        default_unit: str | None = None,
    ) -> dict[str, Any]:
        """Set time tracking configuration.

        Args:
            working_hours_per_day: Hours per working day.
            working_days_per_week: Days per working week.
            time_format: Time format ('pretty' or 'days').
            default_unit: Default time unit.

        Returns:
            Updated configuration.
        """
        config = dict(self.TIME_TRACKING_CONFIG)

        if working_hours_per_day is not None:
            config["workingHoursPerDay"] = working_hours_per_day
        if working_days_per_week is not None:
            config["workingDaysPerWeek"] = working_days_per_week
        if time_format is not None:
            config["timeFormat"] = time_format
        if default_unit is not None:
            config["defaultUnit"] = default_unit

        return config

    # =========================================================================
    # Estimate Operations
    # =========================================================================

    def get_time_tracking(self, issue_key: str) -> dict[str, Any]:
        """Get time tracking data for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Time tracking data including estimates and logged time.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        issue = self._issues[issue_key]
        fields = issue.get("fields", {})

        # Get logged time from worklogs
        worklogs = self._worklogs.get(issue_key, [])
        time_spent_seconds = sum(w.get("timeSpentSeconds", 0) for w in worklogs)

        # Default estimates
        original_estimate_seconds = fields.get(
            "timeoriginalestimate", 28800
        )  # 8h default
        remaining_estimate_seconds = max(
            0, original_estimate_seconds - time_spent_seconds
        )

        return {
            "originalEstimate": self._format_time(original_estimate_seconds),
            "remainingEstimate": self._format_time(remaining_estimate_seconds),
            "timeSpent": self._format_time(time_spent_seconds),
            "originalEstimateSeconds": original_estimate_seconds,
            "remainingEstimateSeconds": remaining_estimate_seconds,
            "timeSpentSeconds": time_spent_seconds,
        }

    def set_estimate(
        self,
        issue_key: str,
        original_estimate: str | None = None,
        remaining_estimate: str | None = None,
    ) -> None:
        """Set time estimate for an issue.

        Args:
            issue_key: The issue key.
            original_estimate: Original estimate in JIRA format (e.g., '2d', '8h').
            remaining_estimate: Remaining estimate in JIRA format.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        if original_estimate:
            self._issues[issue_key]["fields"]["timeoriginalestimate"] = (
                self._parse_time(original_estimate)
            )

        if remaining_estimate:
            self._issues[issue_key]["fields"]["timeestimate"] = self._parse_time(
                remaining_estimate
            )

    def adjust_remaining_estimate(
        self,
        issue_key: str,
        new_estimate: str | None = None,
        reduce_by: str | None = None,
    ) -> None:
        """Adjust remaining estimate for an issue.

        Args:
            issue_key: The issue key.
            new_estimate: New remaining estimate value.
            reduce_by: Amount to reduce the estimate by.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        if new_estimate:
            self._issues[issue_key]["fields"]["timeestimate"] = self._parse_time(
                new_estimate
            )
        elif reduce_by:
            current = self._issues[issue_key]["fields"].get("timeestimate", 28800)
            reduction = self._parse_time(reduce_by)
            self._issues[issue_key]["fields"]["timeestimate"] = max(
                0, current - reduction
            )

    # =========================================================================
    # Worklog Operations (Extended)
    # =========================================================================

    def get_worklog(self, issue_key: str, worklog_id: str) -> dict[str, Any]:
        """Get a specific worklog.

        Args:
            issue_key: The issue key.
            worklog_id: The worklog ID.

        Returns:
            The worklog data.

        Raises:
            NotFoundError: If the worklog is not found.
        """
        self._verify_issue_exists(issue_key)

        for worklog in self._worklogs.get(issue_key, []):
            if worklog["id"] == worklog_id:
                return worklog

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Worklog {worklog_id} not found")

    def update_worklog(
        self,
        issue_key: str,
        worklog_id: str,
        time_spent: str | None = None,
        time_spent_seconds: int | None = None,
        started: str | None = None,
        comment: dict[str, Any] | None = None,
        adjust_estimate: str | None = None,
        new_estimate: str | None = None,
    ) -> dict[str, Any]:
        """Update a worklog.

        Args:
            issue_key: The issue key.
            worklog_id: The worklog ID to update.
            time_spent: New time spent in JIRA format.
            time_spent_seconds: New time spent in seconds.
            started: New start time.
            comment: New comment.
            adjust_estimate: How to adjust estimate.
            new_estimate: New estimate value.

        Returns:
            The updated worklog.

        Raises:
            NotFoundError: If the worklog is not found.
        """
        self._verify_issue_exists(issue_key)

        for worklog in self._worklogs.get(issue_key, []):
            if worklog["id"] == worklog_id:
                if time_spent:
                    worklog["timeSpent"] = time_spent
                    worklog["timeSpentSeconds"] = self._parse_time(time_spent)
                elif time_spent_seconds is not None:
                    worklog["timeSpentSeconds"] = time_spent_seconds
                    worklog["timeSpent"] = self._format_time(time_spent_seconds)

                if started:
                    worklog["started"] = started
                if comment is not None:
                    worklog["comment"] = comment

                worklog["updated"] = "2025-01-08T12:00:00.000+0000"
                return worklog

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Worklog {worklog_id} not found")

    def delete_worklog(
        self,
        issue_key: str,
        worklog_id: str,
        adjust_estimate: str | None = None,
        new_estimate: str | None = None,
        increase_by: str | None = None,
    ) -> None:
        """Delete a worklog.

        Args:
            issue_key: The issue key.
            worklog_id: The worklog ID to delete.
            adjust_estimate: How to adjust estimate after deletion.
            new_estimate: New estimate value.
            increase_by: Amount to increase estimate by.

        Raises:
            NotFoundError: If the worklog is not found.
        """
        self._verify_issue_exists(issue_key)

        worklogs = self._worklogs.get(issue_key, [])
        original_length = len(worklogs)
        self._worklogs[issue_key] = [w for w in worklogs if w["id"] != worklog_id]

        if len(self._worklogs[issue_key]) == original_length:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Worklog {worklog_id} not found")

    def get_worklog_ids_modified_since(
        self,
        since: int,
        expand: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get worklog IDs modified since a timestamp.

        Args:
            since: Unix timestamp in milliseconds.
            expand: Fields to expand.

        Returns:
            List of modified worklog IDs.
        """
        # Return mock data
        return {
            "values": [],
            "since": since,
            "until": since + 86400000,
            "lastPage": True,
        }

    # =========================================================================
    # Time Reporting Operations
    # =========================================================================

    def get_user_worklogs(
        self,
        account_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        start_at: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get worklogs for a user across all issues.

        Args:
            account_id: The user's account ID.
            start_date: Filter worklogs from this date.
            end_date: Filter worklogs until this date.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of worklogs.
        """
        all_worklogs = []

        for issue_key, worklogs in self._worklogs.items():
            for worklog in worklogs:
                if worklog["author"].get("accountId") == account_id:
                    worklog_with_issue = dict(worklog)
                    worklog_with_issue["issueKey"] = issue_key
                    all_worklogs.append(worklog_with_issue)

        paginated = all_worklogs[start_at : start_at + max_results]

        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(all_worklogs),
            "worklogs": paginated,
        }

    def get_project_worklogs(
        self,
        project_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
        start_at: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get worklogs for a project.

        Args:
            project_key: The project key.
            start_date: Filter worklogs from this date.
            end_date: Filter worklogs until this date.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of worklogs.
        """
        all_worklogs = []

        for issue_key, worklogs in self._worklogs.items():
            if issue_key.startswith(f"{project_key}-"):
                for worklog in worklogs:
                    worklog_with_issue = dict(worklog)
                    worklog_with_issue["issueKey"] = issue_key
                    all_worklogs.append(worklog_with_issue)

        paginated = all_worklogs[start_at : start_at + max_results]

        return {
            "startAt": start_at,
            "maxResults": max_results,
            "total": len(all_worklogs),
            "worklogs": paginated,
        }

    def get_time_report(
        self,
        project_key: str | None = None,
        account_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get time tracking report.

        Args:
            project_key: Optional project to filter by.
            account_id: Optional user to filter by.
            start_date: Filter from this date.
            end_date: Filter until this date.

        Returns:
            Time tracking report with totals and breakdowns.
        """
        total_seconds = 0
        by_user = {}
        by_issue = {}

        for issue_key, worklogs in self._worklogs.items():
            # Filter by project if specified
            if project_key and not issue_key.startswith(f"{project_key}-"):
                continue

            for worklog in worklogs:
                # Filter by user if specified
                author_id = worklog["author"].get("accountId")
                if account_id and author_id != account_id:
                    continue

                seconds = worklog.get("timeSpentSeconds", 0)
                total_seconds += seconds

                # Aggregate by user
                if author_id not in by_user:
                    by_user[author_id] = {
                        "user": worklog["author"],
                        "totalSeconds": 0,
                    }
                by_user[author_id]["totalSeconds"] += seconds

                # Aggregate by issue
                if issue_key not in by_issue:
                    by_issue[issue_key] = {
                        "issueKey": issue_key,
                        "totalSeconds": 0,
                    }
                by_issue[issue_key]["totalSeconds"] += seconds

        return {
            "totalSeconds": total_seconds,
            "totalFormatted": self._format_time(total_seconds),
            "byUser": list(by_user.values()),
            "byIssue": list(by_issue.values()),
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_time(self, time_str: str) -> int:
        """Parse JIRA time format to seconds.

        Args:
            time_str: Time in JIRA format (e.g., '1d', '2h', '30m').

        Returns:
            Time in seconds.
        """
        if not time_str:
            return 0

        total_seconds = 0
        time_str = time_str.lower().strip()

        import re

        # Match patterns like "1d", "2h", "30m", "1d 2h 30m"
        patterns = [
            (r"(\d+)w", 5 * 8 * 3600),  # weeks (5 working days)
            (r"(\d+)d", 8 * 3600),  # days (8 hours)
            (r"(\d+)h", 3600),  # hours
            (r"(\d+)m", 60),  # minutes
            (r"(\d+)s", 1),  # seconds
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, time_str)
            if match:
                total_seconds += int(match.group(1)) * multiplier

        return total_seconds

    def _format_time(self, seconds: int) -> str:
        """Format seconds as JIRA time string.

        Args:
            seconds: Time in seconds.

        Returns:
            Formatted time string (e.g., '1d 2h 30m').
        """
        if seconds <= 0:
            return "0m"

        parts = []
        hours_per_day = 8

        days = seconds // (hours_per_day * 3600)
        seconds %= hours_per_day * 3600

        hours = seconds // 3600
        seconds %= 3600

        minutes = seconds // 60

        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "0m"
