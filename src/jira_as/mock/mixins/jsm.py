"""JSM (JIRA Service Management) mixin for MockJiraClient.

Provides mock implementations for service desk, request, SLA, and queue operations.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class JSMMixin(_Base):
    """Mixin providing JSM service desk functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self._comments: Dict[str, List[Dict]]
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Class Constants - Service Desks
    # =========================================================================

    SERVICE_DESKS: ClassVar[list[dict[str, str]]] = [
        {
            "id": "1",
            "projectId": "10001",
            "projectName": "Demo Service Desk",
            "projectKey": "DEMOSD",
        }
    ]

    # =========================================================================
    # Class Constants - Request Types
    # =========================================================================

    REQUEST_TYPES: ClassVar[dict[str, list[dict[str, str]]]] = {
        "1": [  # Service desk ID 1
            {"id": "1", "name": "IT help", "description": "Get help from IT"},
            {
                "id": "2",
                "name": "Computer support",
                "description": "Computer hardware/software issues",
            },
            {
                "id": "3",
                "name": "New employee",
                "description": "Onboard a new team member",
            },
            {
                "id": "4",
                "name": "Travel request",
                "description": "Request travel approval",
            },
            {
                "id": "5",
                "name": "Purchase over $100",
                "description": "Purchase request over $100",
            },
        ]
    }

    # =========================================================================
    # Class Constants - Queues
    # =========================================================================

    QUEUES: ClassVar[dict[str, list[dict[str, Any]]]] = {
        "1": [  # Service desk ID 1
            {"id": "1", "name": "All open", "issueCount": 5},
            {"id": "2", "name": "Assigned to me", "issueCount": 0},
            {"id": "3", "name": "Unassigned", "issueCount": 5},
        ]
    }

    # =========================================================================
    # Class Constants - SLAs
    # =========================================================================

    SLAS: ClassVar[dict[str, dict[str, Any]]] = {
        "1": {"name": "Time to first response", "completedCycles": []},
        "2": {"name": "Time to resolution", "completedCycles": []},
    }

    # =========================================================================
    # Class Constants - JSM Transitions
    # =========================================================================

    JSM_TRANSITIONS: ClassVar[list[dict[str, str]]] = [
        {"id": "11", "name": "Waiting for support"},
        {"id": "21", "name": "In Progress"},
        {"id": "31", "name": "Pending"},
        {"id": "41", "name": "Resolved"},
    ]

    # =========================================================================
    # Service Desk Operations
    # =========================================================================

    def get_service_desks(self, start: int = 0, limit: int = 50) -> dict[str, Any]:
        """Get all service desks.

        Args:
            start: The starting index for pagination.
            limit: The maximum number of service desks to return.

        Returns:
            A paginated list of all service desks available to the user.
        """
        from ..factories import ResponseFactory

        return ResponseFactory.paginated(self.SERVICE_DESKS, start, limit, format="jsm")

    def get_service_desk(self, service_desk_id: str) -> dict[str, Any]:
        """Get service desk by ID.

        Args:
            service_desk_id: The ID of the service desk to retrieve.

        Returns:
            The service desk details.

        Raises:
            NotFoundError: If the service desk is not found.
        """
        for sd in self.SERVICE_DESKS:
            if sd["id"] == service_desk_id:
                return sd
        from ...error_handler import NotFoundError

        raise NotFoundError(f"Service desk {service_desk_id} not found")

    def lookup_service_desk_by_project_key(self, project_key: str) -> dict[str, Any]:
        """Lookup service desk by project key.

        Args:
            project_key: The project key (e.g., 'DEMOSD') to look up.

        Returns:
            The service desk details for the given project.

        Raises:
            JiraError: If no service desk is found for the project key.
        """
        for sd in self.SERVICE_DESKS:
            if sd.get("projectKey") == project_key:
                return sd
        from ...error_handler import JiraError

        raise JiraError(f"No service desk found for project key: {project_key}")

    # =========================================================================
    # Queue Operations
    # =========================================================================

    def get_service_desk_queues(
        self,
        service_desk_id: int,
        include_count: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get queues for a service desk.

        Args:
            service_desk_id: The ID of the service desk.
            include_count: Whether to include issue counts in the response.
            start: The starting index for pagination.
            limit: The maximum number of queues to return.

        Returns:
            A paginated list of queues for the service desk.
        """
        queues = self.QUEUES.get(str(service_desk_id), [])

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(queues, start, limit, format="jsm")

    def get_queues(
        self,
        service_desk_id: int,
        include_count: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Alias for get_service_desk_queues.

        Args:
            service_desk_id: The ID of the service desk.
            include_count: Whether to include issue counts in the response.
            start: The starting index for pagination.
            limit: The maximum number of queues to return.

        Returns:
            A paginated list of queues for the service desk.
        """
        return self.get_service_desk_queues(
            service_desk_id, include_count, start, limit
        )

    def get_queue(self, service_desk_id: int, queue_id: int) -> dict[str, Any]:
        """Get a specific queue by ID.

        Args:
            service_desk_id: The ID of the service desk.
            queue_id: The ID of the queue to retrieve.

        Returns:
            The queue details.

        Raises:
            NotFoundError: If the queue is not found.
        """
        queues = self.QUEUES.get(str(service_desk_id), [])
        for queue in queues:
            if queue["id"] == str(queue_id):
                return queue
        from ...error_handler import NotFoundError

        raise NotFoundError(
            f"Queue {queue_id} not found in service desk {service_desk_id}"
        )

    def get_queue_issues(
        self,
        service_desk_id: int,
        queue_id: int,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get issues in a service desk queue.

        Args:
            service_desk_id: The ID of the service desk.
            queue_id: The ID of the queue.
            start: The starting index for pagination.
            limit: The maximum number of issues to return.

        Returns:
            A paginated list of issues in the queue.
        """
        # Get all DEMOSD issues
        demosd_issues = [
            i for i in self._issues.values() if i["key"].startswith("DEMOSD-")
        ]

        # Filter based on queue type
        queue = self.get_queue(service_desk_id, queue_id)
        queue_name = queue.get("name", "").lower()

        if "unassigned" in queue_name:
            demosd_issues = [
                i for i in demosd_issues if i["fields"].get("assignee") is None
            ]
        elif "assigned to me" in queue_name:
            demosd_issues = [
                i
                for i in demosd_issues
                if i["fields"].get("assignee", {}).get("accountId") == "abc123"
            ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(demosd_issues, start, limit, format="jsm")

    # =========================================================================
    # Request Type Operations
    # =========================================================================

    def get_request_types(
        self,
        service_desk_id: str,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get request types for a service desk.

        Args:
            service_desk_id: The ID of the service desk.
            start: The starting index for pagination.
            limit: The maximum number of request types to return.

        Returns:
            A paginated list of request types.
        """
        types = self.REQUEST_TYPES.get(service_desk_id, [])

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(types, start, limit, format="jsm")

    # =========================================================================
    # Request Operations
    # =========================================================================

    def get_request(self, issue_key: str, expand: list | None = None) -> dict[str, Any]:
        """Get JSM request details.

        Args:
            issue_key: The key of the request (e.g., 'DEMOSD-1').
            expand: Optional list of fields to expand.

        Returns:
            The request details in JSM format.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        issue = self._issues[issue_key]
        # Return JSM-formatted response
        return {
            "issueId": issue["id"],
            "issueKey": issue_key,
            "requestTypeId": issue.get("requestTypeId", "1"),
            "serviceDeskId": issue.get("serviceDeskId", "1"),
            "currentStatus": issue.get("currentStatus", {"status": "Open"}),
            "reporter": issue["fields"].get("reporter"),
            "requestFieldValues": [
                {
                    "fieldId": "summary",
                    "label": "Summary",
                    "value": issue["fields"].get("summary"),
                },
                {
                    "fieldId": "description",
                    "label": "Description",
                    "value": issue["fields"].get("description"),
                },
            ],
        }

    def get_request_status(self, issue_key: str) -> dict[str, Any]:
        """Get the status of a JSM request.

        Args:
            issue_key: The key of the request.

        Returns:
            The current status of the request.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        issue = self._issues[issue_key]
        return issue.get("currentStatus", {"status": issue["fields"]["status"]["name"]})

    def create_request(
        self,
        service_desk_id: str,
        request_type_id: str,
        request_field_values: dict[str, Any],
        raise_on_behalf_of: str | None = None,
    ) -> dict[str, Any]:
        """Create a new JSM request.

        Args:
            service_desk_id: The ID of the service desk.
            request_type_id: The ID of the request type.
            request_field_values: Field values for the request.
            raise_on_behalf_of: Optional account ID to raise the request on behalf of.

        Returns:
            The created request details.
        """
        self._next_issue_id += 1
        issue_key = f"DEMOSD-{self._next_issue_id}"
        issue_id = str(20000 + self._next_issue_id)

        # Get request type name
        request_types = self.REQUEST_TYPES.get(service_desk_id, [])
        type_name = "IT help"
        for rt in request_types:
            if rt["id"] == request_type_id:
                type_name = rt["name"]
                break

        new_issue = {
            "key": issue_key,
            "id": issue_id,
            "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
            "fields": {
                "summary": request_field_values.get("summary", "New Request"),
                "description": request_field_values.get("description"),
                "issuetype": {"name": type_name, "id": "10100"},
                "status": {"name": "Waiting for support", "id": "10100"},
                "priority": {"name": "Medium", "id": "3"},
                "assignee": None,
                "reporter": self.USERS.get(
                    raise_on_behalf_of or "abc123", self.USERS["abc123"]
                ),
                "project": {
                    "key": "DEMOSD",
                    "name": "Demo Service Desk",
                    "id": "10001",
                },
                "created": "2025-01-08T10:00:00.000+0000",
                "updated": "2025-01-08T10:00:00.000+0000",
                "labels": [],
            },
            "requestTypeId": request_type_id,
            "serviceDeskId": service_desk_id,
            "currentStatus": {"status": "Waiting for support", "statusCategory": "new"},
        }

        self._issues[issue_key] = new_issue

        return {
            "issueId": issue_id,
            "issueKey": issue_key,
            "requestTypeId": request_type_id,
            "serviceDeskId": service_desk_id,
            "currentStatus": {"status": "Waiting for support"},
        }

    # =========================================================================
    # SLA Operations
    # =========================================================================

    def get_request_slas(
        self,
        issue_key: str,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get SLAs for a request.

        Args:
            issue_key: The key of the request.
            start: The starting index for pagination.
            limit: The maximum number of SLAs to return.

        Returns:
            A paginated list of SLA metrics for the request.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        # Return mock SLA data
        return {
            "size": 2,
            "start": start,
            "limit": limit,
            "isLastPage": True,
            "values": [
                {
                    "id": "1",
                    "name": "Time to first response",
                    "completedCycles": [],
                    "ongoingCycle": {
                        "startTime": {"iso8601": "2025-01-01T10:00:00+0000"},
                        "breachTime": {"iso8601": "2025-01-02T10:00:00+0000"},
                        "remainingTime": {"millis": 86400000, "friendly": "24h"},
                        "breached": False,
                    },
                },
                {
                    "id": "2",
                    "name": "Time to resolution",
                    "completedCycles": [],
                    "ongoingCycle": {
                        "startTime": {"iso8601": "2025-01-01T10:00:00+0000"},
                        "breachTime": {"iso8601": "2025-01-08T10:00:00+0000"},
                        "remainingTime": {"millis": 604800000, "friendly": "7d"},
                        "breached": False,
                    },
                },
            ],
        }

    def get_request_sla(
        self,
        issue_key: str,
        sla_metric_id: str | None = None,
    ) -> dict[str, Any]:
        """Get a specific SLA for a request.

        Args:
            issue_key: The key of the request.
            sla_metric_id: Optional ID of a specific SLA metric to retrieve.

        Returns:
            The SLA metric details, or all SLAs if no metric ID specified.

        Raises:
            NotFoundError: If the request or SLA metric is not found.
        """
        if sla_metric_id:
            slas = self.get_request_slas(issue_key)
            for sla in slas.get("values", []):
                if sla["id"] == sla_metric_id:
                    return sla
            from ...error_handler import NotFoundError

            raise NotFoundError(f"SLA {sla_metric_id} not found")
        return self.get_request_slas(issue_key)

    # =========================================================================
    # Request Comment Operations
    # =========================================================================

    def add_request_comment(
        self,
        issue_key: str,
        body: str,
        public: bool = True,
    ) -> dict[str, Any]:
        """Add a JSM comment with visibility.

        Args:
            issue_key: The key of the request.
            body: The comment body text.
            public: If True, comment is visible to customers. If False, internal only.

        Returns:
            The created comment.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        if issue_key not in self._comments:
            self._comments[issue_key] = []

        comment_id = str(len(self._comments[issue_key]) + 1)
        comment = {
            "id": comment_id,
            "body": body,
            "public": public,
            "author": self.USERS["abc123"],
            "created": {"iso8601": "2025-01-08T10:00:00+0000"},
        }
        self._comments[issue_key].append(comment)
        return comment

    def get_request_comments(
        self,
        issue_key: str,
        public: bool | None = None,
        internal: bool | None = None,
        start: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get JSM comments with visibility filter.

        Args:
            issue_key: The key of the request.
            public: If True, return only public comments.
            internal: If True, return only internal comments.
            start: The starting index for pagination.
            limit: The maximum number of comments to return.

        Returns:
            A paginated list of comments.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        comments = self._comments.get(issue_key, [])

        # Filter by visibility
        if internal is not None and public is None:
            public = not internal
        if public is not None:
            comments = [c for c in comments if c.get("public") == public]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(comments, start, limit, format="jsm")

    # =========================================================================
    # Request Transition Operations
    # =========================================================================

    def get_request_transitions(self, issue_key: str) -> list:
        """Get available JSM transitions for a request.

        Args:
            issue_key: The key of the request.

        Returns:
            A list of available transitions.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")
        return self.JSM_TRANSITIONS

    def transition_request(
        self,
        issue_key: str,
        transition_id: str,
        comment: str | None = None,
        public: bool = True,
    ) -> None:
        """Transition a JSM request to a new status.

        Args:
            issue_key: The key of the request.
            transition_id: The ID of the transition to perform.
            comment: Optional comment to add with the transition.
            public: If True, the comment is visible to customers.

        Raises:
            NotFoundError: If the request is not found.
        """
        if issue_key not in self._issues:
            from ...error_handler import NotFoundError

            raise NotFoundError(f"Request {issue_key} not found")

        for t in self.JSM_TRANSITIONS:
            if t["id"] == transition_id:
                self._issues[issue_key]["fields"]["status"] = {
                    "name": t["name"],
                    "id": t["id"],
                }
                if issue_key.startswith("DEMOSD"):
                    self._issues[issue_key]["currentStatus"] = {"status": t["name"]}
                break

        if comment:
            self.add_request_comment(issue_key, comment, public)

    # =========================================================================
    # Customer Operations
    # =========================================================================

    def get_customers(
        self,
        service_desk_id: str,
        query: str | None = None,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get customers for a service desk.

        Args:
            service_desk_id: The ID of the service desk.
            query: Optional search query.
            start: Starting index for pagination.
            limit: Maximum number of results.

        Returns:
            Paginated list of customers.
        """
        customers = list(self.USERS.values())
        if query:
            query_lower = query.lower()
            customers = [
                c
                for c in customers
                if query_lower in c["displayName"].lower()
                or query_lower in c.get("emailAddress", "").lower()
            ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(customers, start, limit, format="jsm")

    def add_customers(
        self,
        service_desk_id: str,
        account_ids: list[str] | None = None,
        emails: list[str] | None = None,
    ) -> None:
        """Add customers to a service desk.

        Args:
            service_desk_id: The ID of the service desk.
            account_ids: List of account IDs to add.
            emails: List of emails to add.
        """
        # In mock, this is a no-op
        pass

    def remove_customers(
        self,
        service_desk_id: str,
        account_ids: list[str] | None = None,
        emails: list[str] | None = None,
    ) -> None:
        """Remove customers from a service desk.

        Args:
            service_desk_id: The ID of the service desk.
            account_ids: List of account IDs to remove.
            emails: List of emails to remove.
        """
        # In mock, this is a no-op
        pass

    # =========================================================================
    # Organization Operations
    # =========================================================================

    def get_organizations(
        self,
        service_desk_id: str | None = None,
        start: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get organizations.

        Args:
            service_desk_id: Optional service desk ID to filter by.
            start: Starting index for pagination.
            limit: Maximum number of results.

        Returns:
            Paginated list of organizations.
        """
        orgs = [
            {
                "id": "1",
                "name": "Acme Corp",
                "links": {
                    "self": f"{self.base_url}/rest/servicedeskapi/organization/1"
                },
            },
            {
                "id": "2",
                "name": "Demo Org",
                "links": {
                    "self": f"{self.base_url}/rest/servicedeskapi/organization/2"
                },
            },
        ]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(orgs, start, limit, format="jsm")

    def create_organization(self, name: str) -> dict[str, Any]:
        """Create an organization.

        Args:
            name: The organization name.

        Returns:
            The created organization.
        """
        return {
            "id": "3",
            "name": name,
            "links": {"self": f"{self.base_url}/rest/servicedeskapi/organization/3"},
        }

    def get_organization(self, organization_id: str) -> dict[str, Any]:
        """Get an organization by ID.

        Args:
            organization_id: The organization ID.

        Returns:
            The organization details.
        """
        return {
            "id": organization_id,
            "name": f"Organization {organization_id}",
            "links": {
                "self": f"{self.base_url}/rest/servicedeskapi/organization/{organization_id}"
            },
        }

    def delete_organization(self, organization_id: str) -> None:
        """Delete an organization.

        Args:
            organization_id: The organization ID to delete.
        """
        # In mock, this is a no-op
        pass

    def add_users_to_organization(
        self,
        organization_id: str,
        account_ids: list[str],
    ) -> None:
        """Add users to an organization.

        Args:
            organization_id: The organization ID.
            account_ids: List of account IDs to add.
        """
        # In mock, this is a no-op
        pass

    def remove_users_from_organization(
        self,
        organization_id: str,
        account_ids: list[str],
    ) -> None:
        """Remove users from an organization.

        Args:
            organization_id: The organization ID.
            account_ids: List of account IDs to remove.
        """
        # In mock, this is a no-op
        pass
