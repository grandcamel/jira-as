"""Search mixin for MockJiraClient.

Provides mock implementations for advanced JQL parsing, filters, and search operations.
"""

import re
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..protocols import MockClientProtocol

    _Base = MockClientProtocol
else:
    _Base = object


class SearchMixin(_Base):
    """Mixin providing advanced search functionality.

    Assumes base class provides:
        - self._issues: Dict[str, Dict]
        - self.base_url: str
        - self.USERS: Dict[str, Dict]
    """

    # =========================================================================
    # Class Constants - Saved Filters
    # =========================================================================

    FILTERS: ClassVar[list[dict[str, Any]]] = [
        {
            "id": "10000",
            "name": "My Open Issues",
            "jql": "assignee = currentUser() AND status != Done",
            "owner": {"accountId": "abc123", "displayName": "Jason Krueger"},
            "favourite": True,
        },
        {
            "id": "10001",
            "name": "All Bugs",
            "jql": "project = DEMO AND issuetype = Bug",
            "owner": {"accountId": "abc123", "displayName": "Jason Krueger"},
            "favourite": False,
        },
        {
            "id": "10002",
            "name": "Sprint Issues",
            "jql": "project = DEMO AND sprint in openSprints()",
            "owner": {"accountId": "def456", "displayName": "Jane Manager"},
            "favourite": True,
        },
    ]

    # =========================================================================
    # Advanced JQL Search
    # =========================================================================

    def advanced_search(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: list[str] | None = None,
        expand: list[str] | None = None,
        validate_query: bool = True,
    ) -> dict[str, Any]:
        """Perform advanced JQL search with full parsing.

        Args:
            jql: JQL query string.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.
            fields: List of fields to return.
            expand: List of expansions.
            validate_query: Whether to validate the JQL.

        Returns:
            Search results with pagination info.
        """
        if validate_query:
            validation = self.validate_jql(jql)
            if validation.get("errors"):
                from ...error_handler import JiraError

                raise JiraError(f"Invalid JQL: {validation['errors']}")

        issues = list(self._issues.values())

        # Apply filters based on parsed JQL
        issues = self._apply_jql_filters(issues, jql)

        # Apply ordering
        issues = self._apply_jql_order(issues, jql)

        from ..factories import ResponseFactory

        result = ResponseFactory.paginated_issues(issues, start_at, max_results)
        result["expand"] = ",".join(expand) if expand else ""
        result["warningMessages"] = []
        return result

    def _apply_jql_filters(self, issues: list[dict], jql: str) -> list[dict]:
        """Apply JQL filters to issue list.

        Args:
            issues: List of issues to filter.
            jql: JQL query string.

        Returns:
            Filtered list of issues.
        """
        jql_upper = jql.upper()

        # Project filter
        project_match = re.search(r"PROJECT\s*=\s*(\w+)", jql_upper)
        if project_match:
            project = project_match.group(1)
            if project == "DEMOSD":
                issues = [i for i in issues if i["key"].startswith("DEMOSD-")]
            elif project == "DEMO":
                issues = [
                    i
                    for i in issues
                    if i["key"].startswith("DEMO-")
                    and not i["key"].startswith("DEMOSD-")
                ]

        # Issue type filter
        type_match = re.search(r"ISSUETYPE\s*=\s*[\"']?(\w+)[\"']?", jql_upper)
        if type_match:
            issue_type = type_match.group(1).title()
            issues = [
                i
                for i in issues
                if i["fields"]["issuetype"]["name"].lower() == issue_type.lower()
            ]

        # Status filter
        status_match = re.search(
            r'STATUS\s*=\s*["\']?([^"\']+)["\']?', jql, re.IGNORECASE
        )
        if status_match:
            status = status_match.group(1).strip()
            issues = [
                i
                for i in issues
                if i["fields"]["status"]["name"].lower() == status.lower()
            ]

        # Status NOT filter
        status_not_match = re.search(
            r'STATUS\s*!=\s*["\']?([^"\']+)["\']?', jql, re.IGNORECASE
        )
        if status_not_match:
            status = status_not_match.group(1).strip()
            issues = [
                i
                for i in issues
                if i["fields"]["status"]["name"].lower() != status.lower()
            ]

        # Assignee filter
        if "ASSIGNEE" in jql_upper:
            if "CURRENTUSER()" in jql_upper:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("assignee", {}).get("accountId") == "abc123"
                ]
            elif "EMPTY" in jql_upper or "NULL" in jql_upper:
                issues = [i for i in issues if not i["fields"].get("assignee")]
            else:
                assignee_match = re.search(
                    r'ASSIGNEE\s*=\s*["\']?([^"\']+)["\']?', jql, re.IGNORECASE
                )
                if assignee_match:
                    assignee = assignee_match.group(1).strip().lower()
                    issues = [
                        i
                        for i in issues
                        if i["fields"]
                        .get("assignee", {})
                        .get("displayName", "")
                        .lower()
                        == assignee
                        or i["fields"].get("assignee", {}).get("accountId", "").lower()
                        == assignee
                    ]

        # Reporter filter
        if "REPORTER" in jql_upper:
            if "CURRENTUSER()" in jql_upper:
                issues = [
                    i
                    for i in issues
                    if i["fields"].get("reporter", {}).get("accountId") == "abc123"
                ]
            else:
                reporter_match = re.search(
                    r'REPORTER\s*=\s*["\']?([^"\']+)["\']?', jql, re.IGNORECASE
                )
                if reporter_match:
                    reporter = reporter_match.group(1).strip().lower()
                    issues = [
                        i
                        for i in issues
                        if i["fields"]
                        .get("reporter", {})
                        .get("displayName", "")
                        .lower()
                        == reporter
                    ]

        # Priority filter
        priority_match = re.search(
            r'PRIORITY\s*=\s*["\']?(\w+)["\']?', jql, re.IGNORECASE
        )
        if priority_match:
            priority = priority_match.group(1).strip()
            issues = [
                i
                for i in issues
                if i["fields"]["priority"]["name"].lower() == priority.lower()
            ]

        # Label filter
        label_match = re.search(r'LABELS\s*=\s*["\']?(\w+)["\']?', jql, re.IGNORECASE)
        if label_match:
            label = label_match.group(1).strip()
            issues = [i for i in issues if label in i["fields"].get("labels", [])]

        # Text search
        text_match = re.search(r'TEXT\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE)
        if text_match:
            search_term = text_match.group(1).lower()
            issues = [
                i
                for i in issues
                if search_term in i["fields"].get("summary", "").lower()
                or search_term in str(i["fields"].get("description", "")).lower()
            ]

        # Summary contains
        summary_match = re.search(
            r'SUMMARY\s*~\s*["\']([^"\']+)["\']', jql, re.IGNORECASE
        )
        if summary_match:
            search_term = summary_match.group(1).lower()
            issues = [
                i
                for i in issues
                if search_term in i["fields"].get("summary", "").lower()
            ]

        # Issue key filter
        key_match = re.search(r"KEY\s*=\s*(\w+-\d+)", jql, re.IGNORECASE)
        if key_match:
            key = key_match.group(1).upper()
            issues = [i for i in issues if i["key"] == key]

        # Key IN filter
        key_in_match = re.search(r"KEY\s+IN\s*\(([^)]+)\)", jql, re.IGNORECASE)
        if key_in_match:
            keys = [
                k.strip().strip("'\"").upper() for k in key_in_match.group(1).split(",")
            ]
            issues = [i for i in issues if i["key"] in keys]

        return issues

    def _apply_jql_order(self, issues: list[dict], jql: str) -> list[dict]:
        """Apply JQL ORDER BY clause.

        Args:
            issues: List of issues to sort.
            jql: JQL query string.

        Returns:
            Sorted list of issues.
        """
        order_match = re.search(
            r"ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?", jql, re.IGNORECASE
        )
        if not order_match:
            return issues

        field = order_match.group(1).lower()
        direction = order_match.group(2).upper() if order_match.group(2) else "ASC"
        reverse = direction == "DESC"

        def get_sort_key(issue):
            fields = issue.get("fields", {})
            if field == "created":
                return fields.get("created", "")
            elif field == "updated":
                return fields.get("updated", "")
            elif field == "priority":
                return fields.get("priority", {}).get("id", "999")
            elif field == "status":
                return fields.get("status", {}).get("name", "")
            elif field == "summary":
                return fields.get("summary", "")
            elif field == "key":
                # Sort by numeric part of key
                match = re.search(r"-(\d+)$", issue.get("key", ""))
                return int(match.group(1)) if match else 0
            return ""

        return sorted(issues, key=get_sort_key, reverse=reverse)

    # =========================================================================
    # JQL Validation
    # =========================================================================

    def validate_jql(self, jql: str) -> dict[str, Any]:
        """Validate a JQL query.

        Args:
            jql: JQL query string to validate.

        Returns:
            Validation result with any errors or warnings.
        """
        errors = []
        warnings = []

        # Check for unbalanced parentheses
        if jql.count("(") != jql.count(")"):
            errors.append("Unbalanced parentheses")

        # Check for unbalanced quotes
        if jql.count('"') % 2 != 0:
            errors.append("Unbalanced double quotes")

        # Check for invalid operators
        invalid_ops = re.findall(r"[=!<>]{3,}", jql)
        if invalid_ops:
            errors.append(f"Invalid operator: {invalid_ops[0]}")

        # Check for known fields
        known_fields = [
            "project",
            "issuetype",
            "status",
            "priority",
            "assignee",
            "reporter",
            "summary",
            "description",
            "labels",
            "created",
            "updated",
            "key",
            "text",
            "sprint",
            "fixversion",
            "component",
        ]
        field_pattern = r"(\w+)\s*[=!~<>]+"
        used_fields = re.findall(field_pattern, jql, re.IGNORECASE)
        for field in used_fields:
            if field.lower() not in known_fields and not field.startswith(
                "customfield_"
            ):
                warnings.append(f"Unknown field: {field}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "jql": jql,
        }

    def parse_jql(self, queries: list, validation: str = "strict") -> dict[str, Any]:
        """Parse and validate JQL queries.

        Args:
            queries: List of JQL query strings to parse.
            validation: Validation level: 'strict', 'warn', or 'none'.

        Returns:
            Dict with queries array containing structure and errors.
        """
        parsed_queries = []

        for jql in queries:
            query_result: dict[str, Any] = {
                "query": jql,
                "structure": {
                    "clauses": [],
                    "orderBy": None,
                },
                "errors": [],
            }

            # Extract ORDER BY
            order_match = re.search(r"ORDER\s+BY\s+(.+)$", jql, re.IGNORECASE)
            if order_match:
                query_result["structure"]["orderBy"] = order_match.group(1).strip()
                jql = jql[: order_match.start()].strip()

            # Parse clauses (simplified)
            clause_pattern = (
                r"(\w+)\s*([=!<>~]+|IN|NOT IN)\s*([^\s]+|\([^)]+\)|\"[^\"]+\"|'[^']+')"
            )
            for match in re.finditer(clause_pattern, jql, re.IGNORECASE):
                query_result["structure"]["clauses"].append(
                    {
                        "field": match.group(1),
                        "operator": match.group(2),
                        "value": match.group(3).strip("'\""),
                    }
                )

            # Basic validation if strict mode
            if validation == "strict":
                if jql.count("(") != jql.count(")"):
                    query_result["errors"].append("Unbalanced parentheses")

            parsed_queries.append(query_result)

        return {"queries": parsed_queries}

    # =========================================================================
    # Filter Operations
    # =========================================================================

    def get_filter(self, filter_id: str) -> dict[str, Any]:
        """Get a saved filter by ID.

        Args:
            filter_id: The filter ID.

        Returns:
            The filter details.

        Raises:
            NotFoundError: If the filter is not found.
        """
        for f in self.FILTERS:
            if f["id"] == filter_id:
                return f

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Filter {filter_id} not found")

    def get_favourite_filters(self) -> list[dict[str, Any]]:
        """Get user's favourite filters.

        Returns:
            List of favourite filters.
        """
        return [f for f in self.FILTERS if f.get("favourite")]

    def get_my_filters(self) -> list[dict[str, Any]]:
        """Get filters owned by current user.

        Returns:
            List of user's filters.
        """
        return [f for f in self.FILTERS if f["owner"]["accountId"] == "abc123"]

    def search_filters(
        self,
        filter_name: str | None = None,
        account_id: str | None = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Search for filters.

        Args:
            filter_name: Filter by name.
            account_id: Filter by owner.
            start_at: Starting index for pagination.
            max_results: Maximum number of results.

        Returns:
            Paginated list of filters.
        """
        filters = list(self.FILTERS)

        if filter_name:
            filter_name_lower = filter_name.lower()
            filters = [f for f in filters if filter_name_lower in f["name"].lower()]

        if account_id:
            filters = [f for f in filters if f["owner"]["accountId"] == account_id]

        from ..factories import ResponseFactory

        return ResponseFactory.paginated(filters, start_at, max_results)

    def create_filter(
        self,
        name: str,
        jql: str,
        description: str | None = None,
        favourite: bool = False,
    ) -> dict[str, Any]:
        """Create a saved filter.

        Args:
            name: Filter name.
            jql: JQL query for the filter.
            description: Filter description.
            favourite: Whether to mark as favourite.

        Returns:
            The created filter.
        """
        filter_id = str(10000 + len(self.FILTERS))
        return {
            "id": filter_id,
            "name": name,
            "jql": jql,
            "description": description,
            "owner": self.USERS["abc123"],
            "favourite": favourite,
            "self": f"{self.base_url}/rest/api/3/filter/{filter_id}",
        }

    def update_filter(
        self,
        filter_id: str,
        name: str | None = None,
        jql: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update a saved filter.

        Args:
            filter_id: The filter ID to update.
            name: New filter name.
            jql: New JQL query.
            description: New description.

        Returns:
            The updated filter.

        Raises:
            NotFoundError: If the filter is not found.
        """
        for f in self.FILTERS:
            if f["id"] == filter_id:
                updated = dict(f)
                if name:
                    updated["name"] = name
                if jql:
                    updated["jql"] = jql
                if description is not None:
                    updated["description"] = description
                return updated

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Filter {filter_id} not found")

    def delete_filter(self, filter_id: str) -> None:
        """Delete a saved filter.

        Args:
            filter_id: The filter ID to delete.

        Raises:
            NotFoundError: If the filter is not found.
        """
        for f in self.FILTERS:
            if f["id"] == filter_id:
                return  # Mock deletion

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Filter {filter_id} not found")

    def set_filter_favourite(self, filter_id: str, favourite: bool) -> dict[str, Any]:
        """Set filter favourite status.

        Args:
            filter_id: The filter ID.
            favourite: New favourite status.

        Returns:
            The updated filter.
        """
        for f in self.FILTERS:
            if f["id"] == filter_id:
                updated = dict(f)
                updated["favourite"] = favourite
                return updated

        from ...error_handler import NotFoundError

        raise NotFoundError(f"Filter {filter_id} not found")

    # =========================================================================
    # Bulk Search Operations
    # =========================================================================

    def search_issues_by_keys(
        self,
        keys: list[str],
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get multiple issues by their keys.

        Args:
            keys: List of issue keys.
            fields: Fields to return.

        Returns:
            List of issues.
        """
        return [self._issues[key] for key in keys if key in self._issues]

    def count_issues(self, jql: str) -> int:
        """Count issues matching a JQL query.

        Args:
            jql: JQL query string.

        Returns:
            Number of matching issues.
        """
        result = self.advanced_search(jql, max_results=0)
        return result["total"]

    def export_search_results(
        self,
        jql: str,
        format: str = "json",
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export search results.

        Args:
            jql: JQL query string.
            format: Export format ('json' or 'csv').
            fields: Fields to include in export.

        Returns:
            Export data.
        """
        results = self.advanced_search(jql, max_results=1000)

        if format == "csv":
            # Return CSV-compatible data
            rows = []
            for issue in results["issues"]:
                row = {
                    "key": issue["key"],
                    "summary": issue["fields"].get("summary", ""),
                    "status": issue["fields"]["status"]["name"],
                    "priority": issue["fields"]["priority"]["name"],
                    "assignee": issue["fields"]
                    .get("assignee", {})
                    .get("displayName", "Unassigned"),
                }
                rows.append(row)
            return {"format": "csv", "data": rows}
        else:
            return {"format": "json", "data": results["issues"]}

    # =========================================================================
    # Filter Favourite/Permission Operations
    # =========================================================================

    def add_filter_favourite(self, filter_id: str) -> dict[str, Any]:
        """Add a filter to favourites.

        Args:
            filter_id: The filter ID.

        Returns:
            The updated filter.
        """
        return self.set_filter_favourite(filter_id, True)

    def remove_filter_favourite(self, filter_id: str) -> dict[str, Any]:
        """Remove a filter from favourites.

        Args:
            filter_id: The filter ID.

        Returns:
            The updated filter.
        """
        return self.set_filter_favourite(filter_id, False)

    def get_filter_permissions(self, filter_id: str) -> list[dict[str, Any]]:
        """Get permissions for a filter.

        Args:
            filter_id: The filter ID.

        Returns:
            List of filter permissions.
        """
        # Verify filter exists
        self.get_filter(filter_id)

        return [
            {
                "id": 1,
                "type": "user",
                "user": {"accountId": "abc123", "displayName": "Jason Krueger"},
            },
            {
                "id": 2,
                "type": "project",
                "project": {"id": "10000", "key": "DEMO", "name": "Demo Project"},
            },
        ]

    def add_filter_permission(
        self,
        filter_id: str,
        permission_type: str,
        value: str | None = None,
    ) -> dict[str, Any]:
        """Add a permission to a filter.

        Args:
            filter_id: The filter ID.
            permission_type: Type of permission ('user', 'group', 'project', etc.).
            value: The value for the permission (account ID, group name, etc.).

        Returns:
            The created permission.
        """
        # Verify filter exists
        self.get_filter(filter_id)

        return {
            "id": 10,
            "type": permission_type,
            "value": value,
        }

    def delete_filter_permission(self, filter_id: str, permission_id: int) -> None:
        """Delete a permission from a filter.

        Args:
            filter_id: The filter ID.
            permission_id: The permission ID to delete.
        """
        # Verify filter exists
        self.get_filter(filter_id)
        # In mock, this is a no-op

    # =========================================================================
    # JQL Autocomplete Operations
    # =========================================================================

    def get_jql_autocomplete(self) -> dict[str, Any]:
        """Get JQL autocomplete data (fields and functions).

        Returns:
            Dict with visibleFieldNames and visibleFunctionNames.
        """
        return {
            "visibleFieldNames": [
                {"value": "project", "displayName": "Project"},
                {"value": "issuetype", "displayName": "Issue Type"},
                {"value": "status", "displayName": "Status"},
                {"value": "priority", "displayName": "Priority"},
                {"value": "assignee", "displayName": "Assignee"},
                {"value": "reporter", "displayName": "Reporter"},
                {"value": "created", "displayName": "Created"},
                {"value": "updated", "displayName": "Updated"},
                {"value": "summary", "displayName": "Summary"},
                {"value": "description", "displayName": "Description"},
                {"value": "labels", "displayName": "Labels"},
                {"value": "sprint", "displayName": "Sprint"},
            ],
            "visibleFunctionNames": [
                {"value": "currentUser()", "displayName": "currentUser()"},
                {"value": "now()", "displayName": "now()"},
                {"value": "startOfDay()", "displayName": "startOfDay()"},
                {"value": "endOfDay()", "displayName": "endOfDay()"},
                {"value": "startOfWeek()", "displayName": "startOfWeek()"},
                {"value": "endOfWeek()", "displayName": "endOfWeek()"},
                {"value": "openSprints()", "displayName": "openSprints()"},
                {"value": "closedSprints()", "displayName": "closedSprints()"},
            ],
        }

    def get_jql_suggestions(
        self, field_name: str, field_value: str | None = None
    ) -> dict[str, Any]:
        """Get JQL field value suggestions.

        Args:
            field_name: The field to get suggestions for.
            field_value: Partial value to filter suggestions.

        Returns:
            Dict with results array of suggestion objects.
        """
        suggestions: dict[str, list[dict[str, str]]] = {
            "project": [
                {"value": "DEMO", "displayName": "Demo Project"},
                {"value": "DEMOSD", "displayName": "Demo Service Desk"},
            ],
            "issuetype": [
                {"value": "Bug", "displayName": "Bug"},
                {"value": "Story", "displayName": "Story"},
                {"value": "Task", "displayName": "Task"},
                {"value": "Epic", "displayName": "Epic"},
            ],
            "status": [
                {"value": "To Do", "displayName": "To Do"},
                {"value": "In Progress", "displayName": "In Progress"},
                {"value": "Done", "displayName": "Done"},
            ],
            "priority": [
                {"value": "Highest", "displayName": "Highest"},
                {"value": "High", "displayName": "High"},
                {"value": "Medium", "displayName": "Medium"},
                {"value": "Low", "displayName": "Low"},
                {"value": "Lowest", "displayName": "Lowest"},
            ],
            "assignee": [
                {"value": "abc123", "displayName": "Jason Krueger"},
                {"value": "def456", "displayName": "Jane Manager"},
            ],
        }

        results = suggestions.get(field_name.lower(), [])

        # Filter by partial value if provided
        if field_value:
            field_value_lower = field_value.lower()
            results = [
                s
                for s in results
                if field_value_lower in s["value"].lower()
                or field_value_lower in s["displayName"].lower()
            ]

        return {"results": results}
