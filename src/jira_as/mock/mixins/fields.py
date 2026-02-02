"""Fields mixin for MockJiraClient.

Provides mock implementations for field metadata, screens, and custom fields.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class FieldsMixin(_Base):
    """Mixin providing field metadata functionality.

    Assumes base class provides:
        - self.base_url: str
        - self.PROJECTS: List[Dict]
    """

    # =========================================================================
    # HTTP Endpoint Routing
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "fetch data",
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Route GET requests to appropriate handlers.

        Args:
            endpoint: The API endpoint.
            params: Query parameters.
            operation: Description of the operation.
            headers: Additional headers.

        Returns:
            Response data from the appropriate handler.
        """
        # Route /rest/api/3/field to get_fields()
        if endpoint == "/rest/api/3/field":
            return self.get_fields()

        # Route /rest/api/3/screens to get_screens()
        if endpoint == "/rest/api/3/screens":
            start_at = int(params.get("startAt", 0)) if params else 0
            max_results = int(params.get("maxResults", 100)) if params else 100
            return self.get_screens(start_at, max_results)

        # Route /rest/api/3/field/{fieldId} to get_field()
        if endpoint.startswith("/rest/api/3/field/"):
            field_id = endpoint.split("/")[-1]
            return self.get_field(field_id)

        # Delegate to parent class for other endpoints
        return super().get(endpoint, params, operation, headers)  # type: ignore[safe-super]

    # =========================================================================
    # Class Constants - System Fields
    # =========================================================================

    SYSTEM_FIELDS: ClassVar[list[dict[str, Any]]] = [
        {
            "id": "summary",
            "name": "Summary",
            "schema": {"type": "string"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "description",
            "name": "Description",
            "schema": {"type": "doc"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "issuetype",
            "name": "Issue Type",
            "schema": {"type": "issuetype"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "status",
            "name": "Status",
            "schema": {"type": "status"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "priority",
            "name": "Priority",
            "schema": {"type": "priority"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "assignee",
            "name": "Assignee",
            "schema": {"type": "user"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "reporter",
            "name": "Reporter",
            "schema": {"type": "user"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "labels",
            "name": "Labels",
            "schema": {"type": "array", "items": "string"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "created",
            "name": "Created",
            "schema": {"type": "datetime"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "updated",
            "name": "Updated",
            "schema": {"type": "datetime"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "duedate",
            "name": "Due Date",
            "schema": {"type": "date"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "resolution",
            "name": "Resolution",
            "schema": {"type": "resolution"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "components",
            "name": "Components",
            "schema": {"type": "array", "items": "component"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "fixVersions",
            "name": "Fix Versions",
            "schema": {"type": "array", "items": "version"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "project",
            "name": "Project",
            "schema": {"type": "project"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "parent",
            "name": "Parent",
            "schema": {"type": "issuelink"},
            "custom": False,
            "searchable": True,
            "navigable": True,
        },
    ]

    # =========================================================================
    # Class Constants - Custom Fields
    # =========================================================================

    CUSTOM_FIELDS: ClassVar[list[dict[str, Any]]] = [
        {
            "id": "customfield_10016",
            "name": "Story Points",
            "schema": {
                "type": "number",
                "custom": "com.atlassian.jira.plugin.system.customfieldtypes:float",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10017",
            "name": "Sprint",
            "schema": {
                "type": "array",
                "items": "string",
                "custom": "com.pyxis.greenhopper.jira:gh-sprint",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10018",
            "name": "Epic Link",
            "schema": {
                "type": "string",
                "custom": "com.pyxis.greenhopper.jira:gh-epic-link",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10019",
            "name": "Rank",
            "schema": {
                "type": "string",
                "custom": "com.pyxis.greenhopper.jira:gh-lexo-rank",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10020",
            "name": "Epic Name",
            "schema": {
                "type": "string",
                "custom": "com.pyxis.greenhopper.jira:gh-epic-label",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10021",
            "name": "Team",
            "schema": {
                "type": "option",
                "custom": "com.atlassian.jira.plugin.system.customfieldtypes:select",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
        {
            "id": "customfield_10022",
            "name": "Start Date",
            "schema": {
                "type": "date",
                "custom": "com.atlassian.jira.plugin.system.customfieldtypes:datepicker",
            },
            "custom": True,
            "searchable": True,
            "navigable": True,
        },
    ]

    # =========================================================================
    # Class Constants - Screens
    # =========================================================================

    SCREENS: ClassVar[list[dict[str, str]]] = [
        {
            "id": "1",
            "name": "Default Screen",
            "description": "Default screen for all issue operations",
        },
        {
            "id": "2",
            "name": "Resolve Issue Screen",
            "description": "Screen for resolving issues",
        },
        {
            "id": "3",
            "name": "Workflow Screen",
            "description": "Screen for workflow transitions",
        },
    ]

    # =========================================================================
    # Field Operations
    # =========================================================================

    def get_fields(self) -> list[dict[str, Any]]:
        """Get all fields (system and custom).

        Returns:
            List of all available fields.
        """
        return self.SYSTEM_FIELDS + self.CUSTOM_FIELDS

    def get_field(self, field_id: str) -> dict[str, Any]:
        """Get a specific field by ID.

        Args:
            field_id: The field ID.

        Returns:
            The field metadata.

        Raises:
            NotFoundError: If the field is not found.
        """
        for field in self.SYSTEM_FIELDS + self.CUSTOM_FIELDS:
            if field["id"] == field_id:
                return field

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Field {field_id} not found")

    def get_system_fields(self) -> list[dict[str, Any]]:
        """Get all system fields.

        Returns:
            List of system fields.
        """
        return self.SYSTEM_FIELDS

    def get_custom_fields(self) -> list[dict[str, Any]]:
        """Get all custom fields.

        Returns:
            List of custom fields.
        """
        return self.CUSTOM_FIELDS

    def search_fields(
        self,
        query: str | None = None,
        custom: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Search for fields.

        Args:
            query: Search query for field name.
            custom: Filter by custom field status.

        Returns:
            List of matching fields.
        """
        fields = self.get_fields()

        if query:
            query_lower = query.lower()
            fields = [f for f in fields if query_lower in f["name"].lower()]

        if custom is not None:
            fields = [f for f in fields if f["custom"] == custom]

        return fields

    # =========================================================================
    # Project Field Operations
    # =========================================================================

    def get_project_fields(self, project_key: str) -> list[dict[str, Any]]:
        """Get fields available for a project.

        Args:
            project_key: The project key.

        Returns:
            List of fields available in the project.
        """
        # In mock, all fields are available for all projects
        return self.get_fields()

    def get_create_meta(
        self,
        project_keys: list[str] | None = None,
        issue_type_ids: list[str] | None = None,
        expand: str | None = None,
    ) -> dict[str, Any]:
        """Get create metadata for issues.

        Args:
            project_keys: Projects to get metadata for.
            issue_type_ids: Issue types to get metadata for.
            expand: Fields to expand (e.g., 'projects.issuetypes.fields').

        Returns:
            Create metadata including available fields.
        """
        projects = []
        for project in self.PROJECTS:
            if project_keys and project["key"] not in project_keys:
                continue

            issue_types = [
                {
                    "id": "10000",
                    "name": "Epic",
                    "fields": {f["id"]: f for f in self.get_fields()},
                },
                {
                    "id": "10001",
                    "name": "Story",
                    "fields": {f["id"]: f for f in self.get_fields()},
                },
                {
                    "id": "10002",
                    "name": "Bug",
                    "fields": {f["id"]: f for f in self.get_fields()},
                },
                {
                    "id": "10003",
                    "name": "Task",
                    "fields": {f["id"]: f for f in self.get_fields()},
                },
            ]

            projects.append(
                {
                    "key": project["key"],
                    "name": project["name"],
                    "issuetypes": issue_types,
                }
            )

        return {"projects": projects}

    def get_edit_meta(
        self,
        issue_key: str,
    ) -> dict[str, Any]:
        """Get edit metadata for an issue.

        Args:
            issue_key: The issue key.

        Returns:
            Edit metadata including editable fields.

        Raises:
            NotFoundError: If the issue is not found.
        """
        self._verify_issue_exists(issue_key)

        return {
            "fields": {f["id"]: f for f in self.get_fields()},
        }

    # =========================================================================
    # Agile Field Operations
    # =========================================================================

    def get_agile_fields(self, board_id: int | None = None) -> dict[str, Any]:
        """Get agile-specific field configuration.

        Args:
            board_id: Optional board ID for board-specific config.

        Returns:
            Agile field configuration.
        """
        return {
            "storyPointsField": {
                "id": "customfield_10016",
                "name": "Story Points",
            },
            "sprintField": {
                "id": "customfield_10017",
                "name": "Sprint",
            },
            "epicLinkField": {
                "id": "customfield_10018",
                "name": "Epic Link",
            },
            "rankField": {
                "id": "customfield_10019",
                "name": "Rank",
            },
            "epicNameField": {
                "id": "customfield_10020",
                "name": "Epic Name",
            },
        }

    def get_story_points_field(self) -> dict[str, Any]:
        """Get the story points field configuration.

        Returns:
            Story points field metadata.
        """
        return self.get_field("customfield_10016")

    def get_sprint_field(self) -> dict[str, Any]:
        """Get the sprint field configuration.

        Returns:
            Sprint field metadata.
        """
        return self.get_field("customfield_10017")

    def get_epic_link_field(self) -> dict[str, Any]:
        """Get the epic link field configuration.

        Returns:
            Epic link field metadata.
        """
        return self.get_field("customfield_10018")

    # =========================================================================
    # Screen Operations
    # =========================================================================

    def get_screens(
        self,
        start_at: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get all screens.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of screens.
        """
        from ..factories import ResponseFactory

        return ResponseFactory.paginated(self.SCREENS, start_at, max_results)

    def get_screen(self, screen_id: str) -> dict[str, Any]:
        """Get a screen by ID.

        Args:
            screen_id: The screen ID.

        Returns:
            The screen details.

        Raises:
            NotFoundError: If the screen is not found.
        """
        for screen in self.SCREENS:
            if screen["id"] == screen_id:
                return screen

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Screen {screen_id} not found")

    def get_screen_tabs(self, screen_id: str) -> list[dict[str, Any]]:
        """Get tabs for a screen.

        Args:
            screen_id: The screen ID.

        Returns:
            List of screen tabs.
        """
        return [
            {"id": "1", "name": "Field Tab", "position": 0},
        ]

    def get_screen_tab_fields(
        self, screen_id: str, tab_id: str
    ) -> list[dict[str, Any]]:
        """Get fields in a screen tab.

        Args:
            screen_id: The screen ID.
            tab_id: The tab ID.

        Returns:
            List of fields in the tab.
        """
        return [
            {"id": "summary", "name": "Summary"},
            {"id": "description", "name": "Description"},
            {"id": "issuetype", "name": "Issue Type"},
            {"id": "priority", "name": "Priority"},
            {"id": "assignee", "name": "Assignee"},
        ]

    # =========================================================================
    # Field Configuration Operations
    # =========================================================================

    def get_field_configurations(
        self,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get field configurations.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of field configurations.
        """
        configs = [
            {
                "id": "10000",
                "name": "Default Field Configuration",
                "description": "Default configuration for all projects",
                "isDefault": True,
            },
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(configs, start_at, max_results)

    def get_field_configuration_items(
        self,
        configuration_id: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get items in a field configuration.

        Args:
            configuration_id: The field configuration ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of field configuration items.
        """
        items = [
            {"id": f["id"], "isHidden": False, "isRequired": f["id"] == "summary"}
            for f in self.get_fields()
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(items, start_at, max_results)

    # =========================================================================
    # Field Option Operations
    # =========================================================================

    def get_field_options(
        self,
        field_id: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get options for a select field.

        Args:
            field_id: The field ID.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of field options.
        """
        # Return mock options for select fields
        if field_id == "customfield_10021":  # Team field
            options = [
                {"id": "1", "value": "Backend Team"},
                {"id": "2", "value": "Frontend Team"},
                {"id": "3", "value": "QA Team"},
                {"id": "4", "value": "DevOps Team"},
            ]
        else:
            options = []

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(options, start_at, max_results)

    def create_field_option(
        self,
        field_id: str,
        value: str,
    ) -> dict[str, Any]:
        """Create an option for a select field.

        Args:
            field_id: The field ID.
            value: The option value.

        Returns:
            The created option.
        """
        return {
            "id": "100",
            "value": value,
        }

    def update_field_option(
        self,
        field_id: str,
        option_id: str,
        value: str,
    ) -> dict[str, Any]:
        """Update a field option.

        Args:
            field_id: The field ID.
            option_id: The option ID.
            value: The new value.

        Returns:
            The updated option.
        """
        return {
            "id": option_id,
            "value": value,
        }

    def delete_field_option(
        self,
        field_id: str,
        option_id: str,
    ) -> None:
        """Delete a field option.

        Args:
            field_id: The field ID.
            option_id: The option ID to delete.
        """
        # In mock, this is a no-op
        pass
