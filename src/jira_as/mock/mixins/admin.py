"""Admin mixin for MockJiraClient.

Provides mock implementations for permissions, roles, groups, and project administration.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class AdminMixin(_Base):
    """Mixin providing administration functionality.

    Assumes base class provides:
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
        - self.PROJECTS: List[Dict]
    """

    # =========================================================================
    # Class Constants - Roles
    # =========================================================================

    ROLES: ClassVar[list[dict[str, Any]]] = [
        {
            "id": 10002,
            "name": "Administrators",
            "description": "Project administrators",
            "self": "https://mock.atlassian.net/rest/api/3/role/10002",
        },
        {
            "id": 10001,
            "name": "Developers",
            "description": "Project developers",
            "self": "https://mock.atlassian.net/rest/api/3/role/10001",
        },
        {
            "id": 10000,
            "name": "Users",
            "description": "Project users",
            "self": "https://mock.atlassian.net/rest/api/3/role/10000",
        },
    ]

    # =========================================================================
    # Class Constants - Groups
    # =========================================================================

    GROUPS: ClassVar[list[dict[str, str]]] = [
        {"name": "jira-administrators", "groupId": "group-1"},
        {"name": "jira-software-users", "groupId": "group-2"},
        {"name": "jira-servicedesk-users", "groupId": "group-3"},
        {"name": "developers", "groupId": "group-4"},
    ]

    # =========================================================================
    # Class Constants - Permission Schemes
    # =========================================================================

    PERMISSION_SCHEMES: ClassVar[list[dict[str, str]]] = [
        {
            "id": "10000",
            "name": "Default Permission Scheme",
            "description": "Default scheme for new projects",
            "self": "https://mock.atlassian.net/rest/api/3/permissionscheme/10000",
        },
        {
            "id": "10001",
            "name": "Service Desk Permission Scheme",
            "description": "For service desk projects",
            "self": "https://mock.atlassian.net/rest/api/3/permissionscheme/10001",
        },
    ]

    # =========================================================================
    # Class Constants - Issue Types
    # =========================================================================

    ISSUE_TYPES: ClassVar[list[dict[str, Any]]] = [
        {"id": "10000", "name": "Epic", "description": "A big user story"},
        {"id": "10001", "name": "Story", "description": "A user story"},
        {"id": "10002", "name": "Bug", "description": "A bug"},
        {"id": "10003", "name": "Task", "description": "A task"},
        {
            "id": "10004",
            "name": "Sub-task",
            "description": "A sub-task",
            "subtask": True,
        },
    ]

    # =========================================================================
    # Class Constants - Priorities
    # =========================================================================

    PRIORITIES: ClassVar[list[dict[str, str]]] = [
        {
            "id": "1",
            "name": "Highest",
            "description": "Critical",
            "iconUrl": "icons/priorities/highest.svg",
        },
        {
            "id": "2",
            "name": "High",
            "description": "Important",
            "iconUrl": "icons/priorities/high.svg",
        },
        {
            "id": "3",
            "name": "Medium",
            "description": "Normal",
            "iconUrl": "icons/priorities/medium.svg",
        },
        {
            "id": "4",
            "name": "Low",
            "description": "Low priority",
            "iconUrl": "icons/priorities/low.svg",
        },
        {
            "id": "5",
            "name": "Lowest",
            "description": "Trivial",
            "iconUrl": "icons/priorities/lowest.svg",
        },
    ]

    # =========================================================================
    # Role Operations
    # =========================================================================

    def get_all_project_roles(self) -> list[dict[str, Any]]:
        """Get all project roles.

        Returns:
            List of all project roles.
        """
        return self.ROLES

    def get_project_role(self, project_key: str, role_id: int) -> dict[str, Any]:
        """Get a project role with actors.

        Args:
            project_key: The project key.
            role_id: The role ID.

        Returns:
            The role with its actors.

        Raises:
            NotFoundError: If the role is not found.
        """
        for role in self.ROLES:
            if role["id"] == role_id:
                return {
                    **role,
                    "actors": [
                        {
                            "id": 10001,
                            "displayName": "jira-administrators",
                            "type": "atlassian-group-role-actor",
                            "name": "jira-administrators",
                        }
                    ],
                }

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Role {role_id} not found")

    def get_project_roles(self, project_key: str) -> dict[str, str]:
        """Get roles for a project.

        Args:
            project_key: The project key.

        Returns:
            Dictionary mapping role names to role URLs.
        """
        return {
            role[
                "name"
            ]: f"{self.base_url}/rest/api/3/project/{project_key}/role/{role['id']}"
            for role in self.ROLES
        }

    def add_actor_to_project_role(
        self,
        project_key: str,
        role_id: int,
        actor_type: str,
        actor_value: str,
    ) -> dict[str, Any]:
        """Add an actor to a project role.

        Args:
            project_key: The project key.
            role_id: The role ID.
            actor_type: Type of actor ('user' or 'group').
            actor_value: The actor value (account ID or group name).

        Returns:
            The updated role.
        """
        return self.get_project_role(project_key, role_id)

    def remove_actor_from_project_role(
        self,
        project_key: str,
        role_id: int,
        actor_type: str,
        actor_value: str,
    ) -> None:
        """Remove an actor from a project role.

        Args:
            project_key: The project key.
            role_id: The role ID.
            actor_type: Type of actor ('user' or 'group').
            actor_value: The actor value (account ID or group name).
        """
        # In mock, this is a no-op
        pass

    # =========================================================================
    # Group Operations
    # =========================================================================

    def get_groups(
        self,
        query: str | None = None,
        exclude: list[str] | None = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get all groups.

        Args:
            query: Filter groups by name.
            exclude: Groups to exclude.
            max_results: Maximum number of results.

        Returns:
            List of groups.
        """
        groups = list(self.GROUPS)

        if query:
            query_lower = query.lower()
            groups = [g for g in groups if query_lower in g["name"].lower()]

        if exclude:
            groups = [g for g in groups if g["name"] not in exclude]

        return {
            "header": "Showing groups",
            "total": len(groups),
            "groups": groups[:max_results],
        }

    def get_group(self, group_name: str) -> dict[str, Any]:
        """Get a group by name.

        Args:
            group_name: The group name.

        Returns:
            The group details.

        Raises:
            NotFoundError: If the group is not found.
        """
        for group in self.GROUPS:
            if group["name"] == group_name:
                return group

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Group {group_name} not found")

    def create_group(self, name: str) -> dict[str, Any]:
        """Create a new group.

        Args:
            name: The group name.

        Returns:
            The created group.
        """
        return {
            "name": name,
            "groupId": f"group-{len(self.GROUPS) + 1}",
        }

    def delete_group(self, group_name: str) -> None:
        """Delete a group.

        Args:
            group_name: The group name to delete.
        """
        # In mock, this is a no-op
        pass

    def get_group_members(
        self,
        group_name: str,
        start_at: int = 0,
        max_results: int = 50,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        """Get members of a group.

        Args:
            group_name: The group name.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            include_inactive: Include inactive users.

        Returns:
            Paginated list of group members.
        """
        members = list(self.USERS.values())
        if not include_inactive:
            members = [m for m in members if m.get("active", True)]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(members, start_at, max_results)

    def add_user_to_group(self, group_name: str, account_id: str) -> dict[str, Any]:
        """Add a user to a group.

        Args:
            group_name: The group name.
            account_id: The user's account ID.

        Returns:
            The group with the added user.
        """
        return self.get_group(group_name)

    def remove_user_from_group(self, group_name: str, account_id: str) -> None:
        """Remove a user from a group.

        Args:
            group_name: The group name.
            account_id: The user's account ID.
        """
        # In mock, this is a no-op
        pass

    # =========================================================================
    # Permission Operations
    # =========================================================================

    def get_my_permissions(
        self,
        project_key: str | None = None,
        issue_key: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get current user's permissions.

        Args:
            project_key: Optional project to check permissions for.
            issue_key: Optional issue to check permissions for.
            permissions: Optional list of specific permissions to check.

        Returns:
            Dictionary of permissions and whether they are granted.
        """
        all_permissions = [
            "BROWSE_PROJECTS",
            "CREATE_ISSUES",
            "EDIT_ISSUES",
            "DELETE_ISSUES",
            "ASSIGN_ISSUES",
            "TRANSITION_ISSUES",
            "MANAGE_WATCHERS",
            "ADD_COMMENTS",
            "DELETE_OWN_COMMENTS",
            "DELETE_ALL_COMMENTS",
            "WORK_ON_ISSUES",
            "SCHEDULE_ISSUES",
            "ADMINISTER_PROJECTS",
        ]

        if permissions:
            all_permissions = [p for p in all_permissions if p in permissions]

        return {
            "permissions": {
                perm: {
                    "id": str(i),
                    "key": perm,
                    "name": perm.replace("_", " ").title(),
                    "type": "PROJECT",
                    "description": f"Permission to {perm.lower().replace('_', ' ')}",
                    "havePermission": True,
                }
                for i, perm in enumerate(all_permissions)
            }
        }

    def get_permission_schemes(self) -> dict[str, Any]:
        """Get all permission schemes.

        Returns:
            List of permission schemes.
        """
        return {
            "permissionSchemes": self.PERMISSION_SCHEMES,
        }

    def get_permission_scheme(self, scheme_id: str) -> dict[str, Any]:
        """Get a permission scheme by ID.

        Args:
            scheme_id: The permission scheme ID.

        Returns:
            The permission scheme details.

        Raises:
            NotFoundError: If the scheme is not found.
        """
        for scheme in self.PERMISSION_SCHEMES:
            if scheme["id"] == scheme_id:
                return scheme

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Permission scheme {scheme_id} not found")

    # =========================================================================
    # Issue Type Operations
    # =========================================================================

    def get_issue_types(self) -> list[dict[str, Any]]:
        """Get all issue types.

        Returns:
            List of issue types.
        """
        return self.ISSUE_TYPES

    def get_issue_type(self, issue_type_id: str) -> dict[str, Any]:
        """Get an issue type by ID.

        Args:
            issue_type_id: The issue type ID.

        Returns:
            The issue type details.

        Raises:
            NotFoundError: If the issue type is not found.
        """
        for it in self.ISSUE_TYPES:
            if it["id"] == issue_type_id:
                return it

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Issue type {issue_type_id} not found")

    def get_issue_types_for_project(self, project_key: str) -> list[dict[str, Any]]:
        """Get issue types available for a project.

        Args:
            project_key: The project key.

        Returns:
            List of issue types for the project.
        """
        return self.ISSUE_TYPES

    # =========================================================================
    # Priority Operations
    # =========================================================================

    def get_priorities(self) -> list[dict[str, Any]]:
        """Get all priorities.

        Returns:
            List of priorities.
        """
        return self.PRIORITIES

    def get_priority(self, priority_id: str) -> dict[str, Any]:
        """Get a priority by ID.

        Args:
            priority_id: The priority ID.

        Returns:
            The priority details.

        Raises:
            NotFoundError: If the priority is not found.
        """
        for p in self.PRIORITIES:
            if p["id"] == priority_id:
                return p

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Priority {priority_id} not found")

    # =========================================================================
    # Project Administration Operations
    # =========================================================================

    def get_all_projects(
        self,
        start_at: int = 0,
        max_results: int = 50,
        expand: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all projects.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            expand: Fields to expand.

        Returns:
            List of projects.
        """
        return self.PROJECTS[start_at : start_at + max_results]

    def create_project(
        self,
        key: str,
        name: str,
        project_type_key: str = "software",
        lead_account_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project.

        Args:
            key: Project key.
            name: Project name.
            project_type_key: Type of project.
            lead_account_id: Project lead's account ID.
            description: Project description.

        Returns:
            The created project.
        """
        project_id = str(10000 + len(self.PROJECTS))
        return {
            "id": project_id,
            "key": key,
            "name": name,
            "projectTypeKey": project_type_key,
            "self": f"{self.base_url}/rest/api/3/project/{project_id}",
        }

    def delete_project(self, project_key: str) -> None:
        """Delete a project.

        Args:
            project_key: The project key to delete.
        """
        # In mock, this is a no-op
        pass

    def update_project(
        self,
        project_key: str,
        name: str | None = None,
        description: str | None = None,
        lead_account_id: str | None = None,
    ) -> dict[str, Any]:
        """Update a project.

        Args:
            project_key: The project key.
            name: New project name.
            description: New description.
            lead_account_id: New lead's account ID.

        Returns:
            The updated project.
        """
        for project in self.PROJECTS:
            if project["key"] == project_key:
                updated = dict(project)
                if name:
                    updated["name"] = name
                return updated

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Project {project_key} not found")

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    def get_workflows(
        self,
        start_at: int = 0,
        max_results: int = 50,
        workflow_name: str | None = None,
    ) -> dict[str, Any]:
        """Get all workflows.

        Args:
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            workflow_name: Filter by workflow name.

        Returns:
            Paginated list of workflows.
        """
        workflows: list[dict[str, Any]] = [
            {
                "name": "Software Simplified Workflow",
                "description": "Simple workflow for software projects",
                "default": True,
            },
            {
                "name": "Service Desk Workflow",
                "description": "Workflow for service desk projects",
                "default": False,
            },
        ]

        if workflow_name:
            workflows = [
                w for w in workflows if workflow_name.lower() in w["name"].lower()
            ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(workflows, start_at, max_results)

    def get_workflow_scheme(self, project_key: str) -> dict[str, Any]:
        """Get workflow scheme for a project.

        Args:
            project_key: The project key.

        Returns:
            The workflow scheme details.
        """
        return {
            "id": "10000",
            "name": "Default Workflow Scheme",
            "description": "Default workflow scheme",
            "defaultWorkflow": "Software Simplified Workflow",
            "issueTypeMappings": {},
        }
