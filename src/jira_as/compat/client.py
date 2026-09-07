"""Transport-only adapter for the recorded compatibility command callbacks.

This is deliberately not a replacement JiraClient: only the contract callbacks
receive it. Each method delegates to the compiled Generic Surface.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import click
from as_engine.errors import SurfaceError, messages_from
from as_engine.surface import Surface

from jira_as import engine
from jira_as.config_manager import ConfigManager
from jira_as.error_handler import JiraError, ValidationError
from jira_as.project_guard import check_project_access


def get_client(ctx: click.Context) -> Any:
    """Retain the legacy argv refusal before any metadata or transport access."""
    identities = {
        key: value
        for key, value in ctx.params.items()
        if key
        in {"issue_key", "project", "source_issue", "target_issue", "target", "jql"}
    }
    check_project_access(
        identities, ConfigManager.get_instance().get_allowed_projects()
    )
    ctx.ensure_object(dict)
    client = ctx.obj.get("_compat_client")
    if client is None:
        client = GenericClient(identity_context=identities)
        ctx.obj["_compat_client"] = client
    return client


class GenericClient:
    def __init__(
        self,
        surface: Surface | None = None,
        *,
        identity_context: Mapping[str, Any] | None = None,
    ) -> None:
        # Retain the offline legacy setting while retiring the hand-written mock
        # from these command paths. Explicit generic transport always wins.
        mode = None
        if (
            not os.environ.get("JIRA_AS_TRANSPORT")
            and os.environ.get("JIRA_MOCK_MODE", "").lower() == "true"
        ):
            mode = "responder"
        self.surface = surface or engine.create_surface(transport=mode)
        factory = self.surface.transport_factory
        self.surface.transport_factory = lambda document, index: _ScreenErrors(
            factory(document, index), self
        )
        self._screen_errors: dict[str, str] = {}
        self._field_ids: dict[str, str] = {}
        self._identity_context = dict(identity_context or {})
        self._link_proofs: dict[str, list[tuple[str, str]]] = {}

    def __enter__(self) -> GenericClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Surface closes each owned transport after its complete logical call."""

    def call(
        self, name: str, parameters: Mapping[str, Any], body: Any = None, **options: Any
    ) -> Any:
        _, _, operation = self.surface.resolve(name)
        descriptors = operation.extensions.get("x-as-richtext", [])
        if any("response" in descriptor for descriptor in descriptors):
            options.setdefault("raw", True)
        self._screen_errors = {}
        try:
            return self.surface.call(name, parameters, body, **options).body
        except SurfaceError as exc:
            # The legacy callbacks used ValidationError/JiraError -> exit 1,
            # not the api group's separate local scope / HTTP error codes.
            raise JiraError(
                str(exc),
                status_code=exc.status,
                response_data={"errors": self._screen_errors},
            ) from exc

    def get_issue(
        self, issue_key: str, fields: list[str] | None = None
    ) -> dict[str, Any]:
        parameters: dict[str, Any] = {"issueIdOrKey": issue_key}
        if fields is not None:
            parameters["fields"] = fields
        return self.call("getIssue", parameters)

    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        project = fields.get("project", {}).get("key")
        return self.call(
            "createIssue", {}, {"fields": fields}, scope_argv_identity=project
        )

    def update_issue(
        self, issue_key: str, fields: dict[str, Any], notify_users: bool = True
    ) -> None:
        self.call(
            "editIssue",
            {"issueIdOrKey": issue_key, "notifyUsers": notify_users},
            {"fields": fields},
        )

    def get_comments(
        self,
        issue_key: str,
        max_results: int = 50,
        start_at: int = 0,
        order_by: str = "-created",
    ) -> dict[str, Any]:
        return self.call(
            "getComments",
            {
                "issueIdOrKey": issue_key,
                "maxResults": max_results,
                "startAt": start_at,
                "orderBy": order_by,
            },
        )

    def get_comment(self, issue_key: str, comment_id: str) -> dict[str, Any]:
        return self.call("getComment", {"issueIdOrKey": issue_key, "id": comment_id})

    def add_comment(self, issue_key: str, comment_body: Any) -> dict[str, Any]:
        return self.call(
            "addComment", {"issueIdOrKey": issue_key}, {"body": comment_body}
        )

    def add_comment_with_visibility(
        self,
        issue_key: str,
        comment_body: Any,
        visibility_type: str,
        visibility_value: str | None,
    ) -> dict[str, Any]:
        return self.call(
            "addComment",
            {"issueIdOrKey": issue_key},
            {
                "body": comment_body,
                "visibility": {"type": visibility_type, "value": visibility_value},
            },
        )

    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        return self.call("getTransitions", {"issueIdOrKey": issue_key}).get(
            "transitions", []
        )

    def transition_issue(
        self, issue_key: str, transition_id: str, fields: dict[str, Any] | None = None
    ) -> None:
        body: dict[str, Any] = {"transition": {"id": transition_id}}
        if fields:
            body["fields"] = fields
        self.call("doTransition", {"issueIdOrKey": issue_key}, body)

    def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int = 50,
        next_page_token: str | None = None,
    ) -> dict[str, Any]:
        parameters: dict[str, Any] = {"jql": jql, "maxResults": max_results}
        if fields is not None:
            parameters["fields"] = fields
        if next_page_token:
            parameters["nextPageToken"] = next_page_token
        return self.call("searchAndReconsileIssuesUsingJql", parameters)

    def add_worklog(
        self,
        issue_key: str,
        time_spent: str,
        started: str | None = None,
        comment: Any = None,
        adjust_estimate: str = "auto",
        new_estimate: str | None = None,
        reduce_by: str | None = None,
        visibility_type: str | None = None,
        visibility_value: str | None = None,
    ) -> dict[str, Any]:
        from jira_as.time_utils import parse_time_string

        body: dict[str, Any] = {"timeSpentSeconds": parse_time_string(time_spent)}
        if started:
            body["started"] = started
        if comment is not None:
            body["comment"] = comment
        if visibility_type:
            body["visibility"] = {
                "type": visibility_type,
                "value": visibility_value,
                "identifier": visibility_value,
            }
        parameters: dict[str, Any] = {
            "issueIdOrKey": issue_key,
            "adjustEstimate": adjust_estimate,
        }
        if new_estimate is not None and adjust_estimate == "new":
            parameters["newEstimate"] = new_estimate
        if reduce_by is not None and adjust_estimate == "manual":
            parameters["reduceBy"] = reduce_by
        return self.call("addWorklog", parameters, body)

    def story_points_field(self, project: str) -> str:
        from jira_as.autocomplete_cache import get_autocomplete_cache
        from jira_as.project_context import get_project_agile_fields

        if project in self._field_ids:
            return self._field_ids[project]
        configured = get_project_agile_fields(project).get("story_points")
        if configured:
            self._field_ids[project] = configured
            return configured
        cached = get_autocomplete_cache().get_fields()
        field = self._story_field(cached)
        if field is None:
            # Decision 20: one internal metadata GET; this does not change the
            # Surface default or expose a user-facing site-permission switch.
            field = self._story_field(self.call("getFields", {}, scope_allow_site=True))
        if field is None:
            raise ValidationError("Story points field not found in instance metadata")
        self._field_ids[project] = field
        return field

    @staticmethod
    def _story_field(fields: Any) -> str | None:
        if not isinstance(fields, list):
            return None
        matches = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name", field.get("displayName", ""))).casefold()
            if name not in {"story points", "story point estimate"}:
                continue
            field_id = field.get("id", field.get("value"))
            if isinstance(field_id, str) and field_id.startswith("customfield_"):
                matches.append(field_id)
        unique = set(matches)
        if len(unique) > 1:
            raise ValidationError(
                "Multiple story points fields; configure the project's field ID"
            )
        return matches[0] if matches else None

    def get_link_types(self) -> list[dict[str, Any]]:
        # Decision 20a: instance metadata, no issue/project content.
        return self.call("getIssueLinkTypes", {}, scope_allow_site=True).get(
            "issueLinkTypes", []
        )

    def create_link(
        self, link_type: str, inward_key: str, outward_key: str, comment: Any = None
    ) -> None:
        from jira_as.compat.richtext import richtext

        body: dict[str, Any] = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }
        if comment is not None:
            body["comment"] = {"body": richtext(comment, "markdown")}
        self.call("linkIssues", {}, body, scope_argv_identity=outward_key.split("-")[0])

    def get_issue_links(self, issue_key: str) -> list[dict[str, Any]]:
        links = (
            self.get_issue(issue_key, fields=["issuelinks"])
            .get("fields", {})
            .get("issuelinks", [])
        )
        self._link_proofs = {}
        for link in links:
            endpoints = [
                link[key].get("key")
                for key in ("inwardIssue", "outwardIssue")
                if isinstance(link.get(key), dict)
            ]
            if (
                len(endpoints) == 1
                and isinstance(endpoints[0], str)
                and isinstance(link.get("id"), str)
            ):
                self._link_proofs.setdefault(link["id"], []).append(
                    (issue_key, endpoints[0])
                )
        return links

    def delete_link(self, link_id: str) -> None:
        source = self._identity_context.get("source_issue")
        target = self._identity_context.get("target_issue")
        from jira_as import validate_issue_key

        source = validate_issue_key(source) if source else None
        target = validate_issue_key(target) if target else None
        proof = self._link_proofs.get(link_id, [])
        if not source or not target or proof != [(source, target)]:
            raise ValidationError(
                "Link deletion requires one guarded link matching the explicit source and target keys"
            )
        # Recheck policy on the actual selected keys, not only on the argv.
        check_project_access(
            {"source_issue": source, "target_issue": target},
            ConfigManager.get_instance().get_allowed_projects(),
        )
        self.call("deleteIssueLink", {"linkId": link_id}, scope_allow_site=True)
        del self._link_proofs[link_id]

    def get_current_user_id(self, *, for_create: bool = False) -> str:
        return self.call(
            "getCurrentUser", {}, **({"scope_allow_site": True} if for_create else {})
        ).get("accountId", "")

    def move_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]) -> None:
        self.call("moveIssuesToSprint", {"sprintId": sprint_id}, {"issues": issue_keys})

    def get_filter(self, filter_id: str) -> dict[str, Any]:
        return self.call("getFilter", {"id": int(filter_id)})

    def create_filter(
        self,
        name: str,
        jql: str,
        description: str | None = None,
        favourite: bool = False,
    ) -> dict[str, Any]:
        body = {"name": name, "jql": jql, "favourite": favourite}
        if description is not None:
            body["description"] = description
        return self.call("createFilter", {}, body)


class _ScreenErrors:
    """Retain only field rejection diagnostics needed by the 1.x retry decision.

    Observes the ordinary transport seam; Surface still validates every call,
    enforces policy, runs transforms, and owns response/error conversion.
    """

    def __init__(self, transport: Any, client: GenericClient) -> None:
        self.transport = transport
        self.client = client

    def _record(self, data: Any) -> None:
        if not isinstance(data, dict) or not isinstance(data.get("errors"), dict):
            return
        for key in ("comment", "resolution"):
            value = data["errors"].get(key)
            if isinstance(value, str):
                self.client._screen_errors[key] = "; ".join(messages_from(value))

    def call(self, operation: Any, parameters: Any, body: Any, **options: Any) -> Any:
        try:
            response = self.transport.call(operation, parameters, body, **options)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 400:
                self._record(getattr(exc, "response_data", None))
            raise
        if response.status == 400:
            self._record(response.body)
        return response

    def close(self) -> None:
        self.transport.close()
