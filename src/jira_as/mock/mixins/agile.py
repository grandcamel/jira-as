"""Agile mixin for MockJiraClient.

Provides mock implementations for boards, sprints, and backlog operations.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class AgileMixin(_Base):
    """Mixin providing agile board and sprint functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Class Constants - Boards
    # =========================================================================

    BOARDS: ClassVar[list[dict[str, Any]]] = [
        {
            "id": 1,
            "self": "https://mock.atlassian.net/rest/agile/1.0/board/1",
            "name": "DEMO board",
            "type": "scrum",
            "location": {
                "projectId": 10000,
                "displayName": "Demo Project",
                "projectKey": "DEMO",
                "projectTypeKey": "software",
            },
        },
        {
            "id": 2,
            "self": "https://mock.atlassian.net/rest/agile/1.0/board/2",
            "name": "DEMO Kanban",
            "type": "kanban",
            "location": {
                "projectId": 10000,
                "displayName": "Demo Project",
                "projectKey": "DEMO",
                "projectTypeKey": "software",
            },
        },
    ]

    # =========================================================================
    # Class Constants - Sprints
    # =========================================================================

    SPRINTS: ClassVar[list[dict[str, Any]]] = [
        {
            "id": 1,
            "self": "https://mock.atlassian.net/rest/agile/1.0/sprint/1",
            "state": "active",
            "name": "Sprint 1",
            "startDate": "2025-01-01T00:00:00.000Z",
            "endDate": "2025-01-14T00:00:00.000Z",
            "originBoardId": 1,
            "goal": "Complete user authentication",
        },
        {
            "id": 2,
            "self": "https://mock.atlassian.net/rest/agile/1.0/sprint/2",
            "state": "future",
            "name": "Sprint 2",
            "startDate": "2025-01-15T00:00:00.000Z",
            "endDate": "2025-01-28T00:00:00.000Z",
            "originBoardId": 1,
            "goal": "API documentation and bug fixes",
        },
        {
            "id": 3,
            "self": "https://mock.atlassian.net/rest/agile/1.0/sprint/3",
            "state": "closed",
            "name": "Sprint 0",
            "startDate": "2024-12-15T00:00:00.000Z",
            "endDate": "2024-12-31T00:00:00.000Z",
            "originBoardId": 1,
            "goal": "Project setup and planning",
            "completeDate": "2024-12-31T00:00:00.000Z",
        },
    ]

    # =========================================================================
    # Board Operations
    # =========================================================================

    def get_boards(
        self,
        start_at: int = 0,
        max_results: int = 50,
        project_key_or_id: str | None = None,
        board_type: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Get all boards.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            project_key_or_id: Filter by project.
            board_type: Filter by board type (scrum, kanban).
            name: Filter by board name.

        Returns:
            Paginated list of boards.
        """
        boards = list(self.BOARDS)

        if project_key_or_id:
            boards = [
                b
                for b in boards
                if b["location"]["projectKey"] == project_key_or_id
                or str(b["location"]["projectId"]) == str(project_key_or_id)
            ]

        if board_type:
            boards = [b for b in boards if b["type"] == board_type]

        if name:
            name_lower = name.lower()
            boards = [b for b in boards if name_lower in b["name"].lower()]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(boards, start_at, max_results)

    def get_board(self, board_id: int) -> dict[str, Any]:
        """Get a specific board.

        Args:
            board_id: The board ID.

        Returns:
            The board data.

        Raises:
            NotFoundError: If the board is not found.
        """
        for board in self.BOARDS:
            if board["id"] == board_id:
                return board

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Board {board_id} not found")

    def get_board_configuration(self, board_id: int) -> dict[str, Any]:
        """Get board configuration.

        Args:
            board_id: The board ID.

        Returns:
            The board configuration.
        """
        return {
            "id": board_id,
            "name": f"Board {board_id} Configuration",
            "type": "scrum",
            "columnConfig": {
                "columns": [
                    {"name": "To Do", "statuses": [{"id": "10000"}]},
                    {"name": "In Progress", "statuses": [{"id": "10001"}]},
                    {"name": "Done", "statuses": [{"id": "10002"}]},
                ]
            },
            "estimation": {
                "type": "field",
                "field": {
                    "fieldId": "customfield_10016",
                    "displayName": "Story Points",
                },
            },
            "ranking": {"rankCustomFieldId": 10019},
        }

    # =========================================================================
    # Sprint Operations
    # =========================================================================

    def get_sprints(
        self,
        board_id: int,
        start_at: int = 0,
        max_results: int = 50,
        state: str | None = None,
    ) -> dict[str, Any]:
        """Get sprints for a board.

        Args:
            board_id: The board ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            state: Filter by sprint state (active, future, closed).

        Returns:
            Paginated list of sprints.
        """
        sprints = [s for s in self.SPRINTS if s["originBoardId"] == board_id]

        if state:
            sprints = [s for s in sprints if s["state"] == state]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(sprints, start_at, max_results)

    def get_sprint(self, sprint_id: int) -> dict[str, Any]:
        """Get a specific sprint.

        Args:
            sprint_id: The sprint ID.

        Returns:
            The sprint data.

        Raises:
            NotFoundError: If the sprint is not found.
        """
        for sprint in self.SPRINTS:
            if sprint["id"] == sprint_id:
                return sprint

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Sprint {sprint_id} not found")

    def create_sprint(
        self,
        name: str,
        board_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Create a new sprint.

        Args:
            name: Sprint name.
            board_id: Board ID for the sprint.
            start_date: Sprint start date.
            end_date: Sprint end date.
            goal: Sprint goal.

        Returns:
            The created sprint.
        """
        sprint_id = max(s["id"] for s in self.SPRINTS) + 1

        sprint = {
            "id": sprint_id,
            "self": f"https://mock.atlassian.net/rest/agile/1.0/sprint/{sprint_id}",
            "state": "future",
            "name": name,
            "originBoardId": board_id,
        }

        if start_date:
            sprint["startDate"] = start_date
        if end_date:
            sprint["endDate"] = end_date
        if goal:
            sprint["goal"] = goal

        return sprint

    def update_sprint(
        self,
        sprint_id: int,
        name: str | None = None,
        state: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Update a sprint.

        Args:
            sprint_id: The sprint ID to update.
            name: New sprint name.
            state: New sprint state.
            start_date: New start date.
            end_date: New end date.
            goal: New goal.

        Returns:
            The updated sprint.

        Raises:
            NotFoundError: If the sprint is not found.
        """
        sprint = self.get_sprint(sprint_id)
        updated = dict(sprint)

        if name:
            updated["name"] = name
        if state:
            updated["state"] = state
        if start_date:
            updated["startDate"] = start_date
        if end_date:
            updated["endDate"] = end_date
        if goal:
            updated["goal"] = goal

        return updated

    def get_sprint_issues(
        self,
        sprint_id: int,
        start_at: int = 0,
        max_results: int = 50,
        jql: str | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get issues in a sprint.

        Args:
            sprint_id: The sprint ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            jql: Additional JQL filter.
            fields: Fields to return.

        Returns:
            Paginated list of issues in the sprint.
        """
        # For mock, return DEMO issues (in real JIRA, issues would be assigned to sprints)
        demo_issues = [
            i
            for i in self._issues.values()
            if i["key"].startswith("DEMO-") and not i["key"].startswith("DEMOSD-")
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated_issues(demo_issues, start_at, max_results)

    def move_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]) -> None:
        """Move issues to a sprint.

        Args:
            sprint_id: The target sprint ID.
            issue_keys: List of issue keys to move.
        """
        # In mock, this is a no-op since we don't track sprint assignments
        pass

    # =========================================================================
    # Backlog Operations
    # =========================================================================

    def get_backlog_issues(
        self,
        board_id: int,
        start_at: int = 0,
        max_results: int = 50,
        jql: str | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get backlog issues for a board.

        Args:
            board_id: The board ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            jql: Additional JQL filter.
            fields: Fields to return.

        Returns:
            Paginated list of backlog issues.
        """
        # For mock, return DEMO issues not in any sprint
        demo_issues = [
            i
            for i in self._issues.values()
            if i["key"].startswith("DEMO-") and not i["key"].startswith("DEMOSD-")
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated_issues(demo_issues, start_at, max_results)

    def move_issues_to_backlog(self, issue_keys: list[str]) -> None:
        """Move issues to backlog (remove from sprint).

        Args:
            issue_keys: List of issue keys to move to backlog.
        """
        # In mock, this is a no-op
        pass

    def rank_issues(
        self,
        issue_keys: list[str],
        rank_before_issue: str | None = None,
        rank_after_issue: str | None = None,
    ) -> None:
        """Rank issues in the backlog.

        Args:
            issue_keys: Issues to rank.
            rank_before_issue: Issue to rank before.
            rank_after_issue: Issue to rank after.
        """
        # In mock, this is a no-op
        pass

    # =========================================================================
    # Epic Operations
    # =========================================================================

    def get_epics(
        self,
        board_id: int,
        start_at: int = 0,
        max_results: int = 50,
        done: bool | None = None,
    ) -> dict[str, Any]:
        """Get epics for a board.

        Args:
            board_id: The board ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            done: Filter by completion status.

        Returns:
            Paginated list of epics.
        """
        epics = [
            i
            for i in self._issues.values()
            if i["fields"]["issuetype"]["name"] == "Epic"
            and i["key"].startswith("DEMO-")
        ]

        if done is not None:
            if done:
                epics = [e for e in epics if e["fields"]["status"]["name"] == "Done"]
            else:
                epics = [e for e in epics if e["fields"]["status"]["name"] != "Done"]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(epics, start_at, max_results)

    def get_epic_issues(
        self,
        epic_id_or_key: str,
        start_at: int = 0,
        max_results: int = 50,
        jql: str | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get issues in an epic.

        Args:
            epic_id_or_key: The epic ID or key.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            jql: Additional JQL filter.
            fields: Fields to return.

        Returns:
            Paginated list of issues in the epic.
        """
        # For mock, return issues that could be in this epic
        # In real JIRA, issues would have an epic link field
        demo_issues = [
            i
            for i in self._issues.values()
            if i["key"].startswith("DEMO-")
            and not i["key"].startswith("DEMOSD-")
            and i["fields"]["issuetype"]["name"] != "Epic"
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated_issues(demo_issues, start_at, max_results)

    def move_issues_to_epic(self, epic_id_or_key: str, issue_keys: list[str]) -> None:
        """Move issues to an epic.

        Args:
            epic_id_or_key: The target epic ID or key.
            issue_keys: List of issue keys to move.
        """
        # In mock, this is a no-op
        pass

    def remove_issues_from_epic(self, issue_keys: list[str]) -> None:
        """Remove issues from their epic.

        Args:
            issue_keys: List of issue keys to remove from epics.
        """
        # In mock, this is a no-op
        pass
