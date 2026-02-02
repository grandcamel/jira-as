"""Protocol definitions for mock client mixins.

Defines the interface that mixins expect from the base class,
enabling proper type checking with mypy.
"""

from typing import Any, ClassVar, Protocol


class MockClientProtocol(Protocol):
    """Protocol defining attributes/methods mixins expect from base class.

    Mixins should inherit from this protocol to get proper type checking
    for attributes they access from the base class.
    """

    # Class constants
    USERS: ClassVar[dict[str, dict[str, Any]]]
    PROJECTS: ClassVar[list[dict[str, str]]]

    # Instance attributes
    base_url: str
    _issues: dict[str, dict[str, Any]]
    _comments: dict[str, list[dict[str, Any]]]
    _worklogs: dict[str, list[dict[str, Any]]]
    _next_issue_id: int

    # Verification helpers
    def _verify_issue_exists(self, issue_key: str) -> dict[str, Any]:
        """Verify issue exists and return it."""
        ...

    def _verify_project_exists(self, project_key: str) -> dict[str, Any]:
        """Verify project exists and return it."""
        ...

    # HTTP operations (used by mixins that route/extend requests)
    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "fetch data",
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Make a GET request."""
        ...

    # Issue operations (used by relationships.py clone_issue)
    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a new issue."""
        ...
