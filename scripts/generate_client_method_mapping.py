#!/usr/bin/env python3
"""Generate the complete 1.2.0 public-client migration inventory, offline.

Capture names once with --capture 1.x, then regenerate with no git dependency.
Targets were reviewed against legacy request routes and the frozen wrapper table;
API v2 screen routes map to their v3 equivalents. Explicit notes prevent invented
replacements for local helpers and routes absent from the pinned documents.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/client-methods-1.2.0.json"
OUTPUT = ROOT / "docs/client-method-mapping.md"
DEFERRED = "legacy client (deferred, JAS-64)"

# Indexed operationIds, surviving verbs, or an explicit absence/lifecycle note.
TARGETS: dict[str, str] = {
    "get": "note: Use api call <operationId> for an indexed GET; no arbitrary-URL CLI equivalent.",
    "post": "note: Use api call <operationId> for an indexed POST; no arbitrary-URL CLI equivalent.",
    "put": "note: Use api call <operationId> for an indexed PUT; no arbitrary-URL CLI equivalent.",
    "delete": "note: Use api call <operationId> for an indexed DELETE; risk preview requires --confirm to send.",
    "upload_file": "addAttachment",
    "download_file": "getAttachmentContent, getAttachmentThumbnail",
    "search_issues": "searchAndReconsileIssuesUsingJql",
    "get_issue": "getIssue",
    "create_issue": "createIssue",
    "create_issues_bulk": "createIssues",
    "get_create_issue_meta_issuetypes": "getCreateIssueMetaIssueTypes",
    "get_create_issue_meta_fields": "getCreateIssueMetaIssueTypeId",
    "update_issue": "editIssue",
    "delete_issue": "deleteIssue",
    "get_transitions": "getTransitions",
    "transition_issue": "doTransition",
    "get_current_user_id": "getCurrentUser",
    "assign_issue": "assignIssue",
    "add_comment": "addComment",
    "close": "note: Local transport lifecycle; use HTTPTransport.close() or its context manager, no HTTP operation.",
    "get_sprint": "getSprint",
    "get_sprint_issues": "getIssuesForSprint",
    "create_sprint": "createSprint",
    "update_sprint": "updateSprint",
    "move_issues_to_sprint": "moveIssuesToSprintAndRank",
    "get_board_backlog": "getIssuesForBacklog",
    "get_board_issues": "getIssuesForBoard",
    "move_issues_to_backlog": "moveIssuesToBacklog",
    "rank_issues": "rankIssues",
    "get_board": "getBoard",
    "get_all_boards": "getAllBoards",
    "get_board_sprints": "getAllSprints",
    "get_link_types": "getIssueLinkTypes",
    "get_link": "getIssueLink",
    "create_link": "linkIssues",
    "delete_link": "deleteIssueLink",
    "get_issue_links": "getIssue",
    "get_remote_links": "getRemoteIssueLinks",
    "create_remote_link": "createOrUpdateRemoteIssueLink",
    "delete_remote_link": "deleteRemoteIssueLinkById",
    "create_project": "createProject",
    "get_project": "getProject",
    "delete_project": "deleteProject",
    "get_project_statuses": "getAllStatuses",
    "delete_sprint": "deleteSprint",
    "delete_board": "deleteBoard",
    "get_comments": "getComments",
    "get_comment": "getComment",
    "update_comment": "updateComment",
    "delete_comment": "deleteComment",
    "get_attachments": "getIssue",
    "delete_attachment": "removeAttachment",
    "search_users": "findUsers",
    "add_worklog": "addWorklog",
    "get_worklogs": "getIssueWorklog",
    "get_worklog": "getWorklog",
    "update_worklog": "updateWorklog",
    "delete_worklog": "deleteWorklog",
    "get_time_tracking": "getIssue",
    "set_time_tracking": "editIssue",
    "get_jql_autocomplete": "getAutoComplete",
    "get_jql_suggestions": "getFieldAutoCompleteForQueryString",
    "parse_jql": "parseJqlQueries",
    "create_filter": "createFilter",
    "get_filter": "getFilter",
    "update_filter": "updateFilter",
    "delete_filter": "deleteFilter",
    "get_my_filters": "getMyFilters",
    "get_favourite_filters": "getFavouriteFilters",
    "search_filters": "getFiltersPaginated",
    "add_filter_favourite": "setFavouriteForFilter",
    "remove_filter_favourite": "deleteFavouriteForFilter",
    "get_filter_permissions": "getSharePermissions",
    "add_filter_permission": "addSharePermission",
    "delete_filter_permission": "deleteSharePermission",
    "add_comment_with_visibility": "addComment",
    "get_changelog": "getChangeLogs",
    "notify_issue": "notify",
    "create_version": "createVersion",
    "get_version": "getVersion",
    "update_version": "updateVersion",
    "delete_version": "deleteVersion",
    "get_project_versions": "getProjectVersions",
    "get_version_issue_counts": "getVersionRelatedIssues",
    "get_version_unresolved_count": "getVersionUnresolvedIssues",
    "create_component": "createComponent",
    "get_component": "getComponent",
    "update_component": "updateComponent",
    "delete_component": "deleteComponent",
    "get_project_components": "getProjectComponents",
    "get_component_issue_counts": "getComponentRelatedIssues",
    "clone_issue": "verb: relationships clone",
    "get_service_desks": "getServiceDesks",
    "get_service_desk": "getServiceDeskById",
    "get_request_types": "getRequestTypes",
    "get_request_type": "getRequestTypeById",
    "get_request_type_fields": "getRequestTypeFields",
    "create_service_desk": "createProject",
    "lookup_service_desk_by_project_key": "getServiceDesks",
    "create_customer": "createCustomer",
    "get_service_desk_customers": "getCustomers",
    "add_customers_to_service_desk": "addCustomers",
    "remove_customers_from_service_desk": "removeCustomers",
    "create_request": "createCustomerRequest",
    "get_request": "getCustomerRequestByIdOrKey",
    "get_request_status": "getCustomerRequestStatus",
    "get_request_transitions": "getCustomerTransitions",
    "transition_request": "performCustomerTransition",
    "get_request_slas": "getSlaInformation",
    "get_request_sla": "getSlaInformationById",
    "get_service_desk_queues": "getQueues",
    "get_queue": "getQueue",
    "get_queue_issues": "getIssuesInQueue",
    "get_organizations": "getOrganizations",
    "create_organization": "createOrganization",
    "get_organization": "getOrganization",
    "delete_organization": "deleteOrganization",
    "add_users_to_organization": "addUsersToOrganization",
    "remove_users_from_organization": "removeUsersFromOrganization",
    "get_request_participants": "getRequestParticipants",
    "add_request_participants": "addRequestParticipants",
    "remove_request_participants": "removeRequestParticipants",
    "add_request_comment": "createRequestComment",
    "get_request_comments": "getRequestComments",
    "get_request_comment": "getRequestCommentById",
    "get_request_approvals": "getApprovals",
    "get_request_approval": "getApprovalById",
    "answer_approval": "answerApproval",
    "get_pending_approvals": "getApprovals, searchAndReconsileIssuesUsingJql",
    "search_kb_articles": "getServiceDeskArticles",
    "get_kb_article": "viewArticle",
    "suggest_kb_for_request": "verb: jsm kb suggest",
    "has_assets_license": "legacy client (deferred, JAS-64)",
    "list_assets": "legacy client (deferred, JAS-64)",
    "get_asset": "legacy client (deferred, JAS-64)",
    "create_asset": "legacy client (deferred, JAS-64)",
    "update_asset": "legacy client (deferred, JAS-64)",
    "link_asset_to_request": "legacy client (deferred, JAS-64)",
    "find_assets_by_criteria": "legacy client (deferred, JAS-64)",
    "get_service_desk_organizations": "getServiceDeskOrganizations",
    "add_organization_to_service_desk": "addOrganization",
    "remove_organization_from_service_desk": "removeOrganization",
    "get_organization_users": "getUsersInOrganization",
    "update_organization": "note: No indexed organization rename. setOrganizationProperty stores metadata only; it does not rename an organization.",
    "get_service_desk_agents": "getServiceDeskById, getProjectRoles, getProjectRole",
    "get_my_approvals": "getApprovals, searchAndReconsileIssuesUsingJql",
    "get_queues": "getQueues",
    "search_knowledge_base": "getServiceDeskArticles",
    "get_knowledge_base_article": "viewArticle",
    "get_knowledge_base_suggestions": "verb: jsm kb suggest",
    "get_knowledge_base_spaces": "note: No indexed equivalent for the legacy knowledgebase/category route; no replacement verb.",
    "link_knowledge_base_article": "createRequestComment",
    "attach_article_as_solution": "createRequestComment",
    "get_object_schemas": "legacy client (deferred, JAS-64)",
    "get_object_schema": "legacy client (deferred, JAS-64)",
    "get_object_types": "legacy client (deferred, JAS-64)",
    "get_object_type_attributes": "legacy client (deferred, JAS-64)",
    "search_assets": "legacy client (deferred, JAS-64)",
    "delete_asset": "legacy client (deferred, JAS-64)",
    "get_issue_assets": "legacy client (deferred, JAS-64)",
    "link_asset_to_issue": "legacy client (deferred, JAS-64)",
    "find_affected_assets": "legacy client (deferred, JAS-64)",
    "get_workflows": "getWorkflowsPaginated",
    "search_workflows": "getWorkflowsPaginated",
    "get_workflow_bulk": "readWorkflows",
    "get_workflow_schemes_for_workflow": "getWorkflowSchemeUsagesForWorkflow",
    "get_workflow_schemes": "getAllWorkflowSchemes",
    "get_workflow_scheme": "getWorkflowScheme",
    "get_workflow_scheme_for_project": "getWorkflowSchemeProjectAssociations",
    "assign_workflow_scheme_to_project": "switchWorkflowSchemeForProject",
    "get_task_status": "getTask",
    "get_all_statuses": "getStatuses",
    "get_statuses": "getStatuses",
    "get_status": "getStatus",
    "search_statuses": "search",
    "get_notification_schemes": "getNotificationSchemes",
    "get_notification_scheme": "getNotificationScheme",
    "get_notification_scheme_projects": "getNotificationSchemeToProjectMappings",
    "create_notification_scheme": "createNotificationScheme",
    "update_notification_scheme": "updateNotificationScheme",
    "add_notification_to_scheme": "addNotifications",
    "delete_notification_scheme": "deleteNotificationScheme",
    "delete_notification_from_scheme": "removeNotificationFromNotificationScheme",
    "lookup_notification_scheme_by_name": "getNotificationSchemes",
    "get_user": "getUser",
    "get_current_user": "getCurrentUser",
    "get_user_groups": "getUserGroups",
    "find_assignable_users": "findAssignableUsers",
    "get_all_users": "getAllUsers",
    "get_users_bulk": "bulkGetUsers",
    "find_groups": "findGroups",
    "get_group": "getGroup",
    "create_group": "createGroup",
    "delete_group": "removeGroup",
    "get_group_members": "getUsersFromGroup",
    "add_user_to_group": "addUserToGroup",
    "remove_user_from_group": "removeUserFromGroup",
    "update_project": "updateProject",
    "search_projects": "searchProjects",
    "archive_project": "archiveProject",
    "restore_project": "restore",
    "delete_project_async": "deleteProjectAsynchronously",
    "get_project_categories": "getAllProjectCategories",
    "get_project_category": "getProjectCategoryById",
    "create_project_category": "createProjectCategory",
    "update_project_category": "updateProjectCategory",
    "delete_project_category": "removeProjectCategory",
    "get_project_types": "getAllProjectTypes",
    "get_project_type": "getProjectTypeByKey",
    "get_project_avatars": "getAllProjectAvatars",
    "set_project_avatar": "updateProjectAvatar",
    "upload_project_avatar": "createProjectAvatar",
    "delete_project_avatar": "deleteProjectAvatar",
    "get_screens": "getScreens",
    "get_screen": "getScreens",
    "get_screen_tabs": "getAllScreenTabs",
    "get_screen_tab_fields": "getAllScreenTabFields",
    "add_field_to_screen_tab": "addScreenTabField",
    "remove_field_from_screen_tab": "removeScreenTabField",
    "get_screen_available_fields": "getAvailableScreenFields",
    "get_screen_schemes": "getScreenSchemes",
    "get_screen_scheme": "getScreenSchemes",
    "get_issue_types": "getIssueAllTypes",
    "get_issue_type": "getIssueType",
    "create_issue_type": "createIssueType",
    "update_issue_type": "updateIssueType",
    "delete_issue_type": "deleteIssueType",
    "get_issue_type_alternatives": "getAlternativeIssueTypes",
    "get_issue_type_schemes": "getAllIssueTypeSchemes",
    "get_issue_type_scheme_items": "getIssueTypeSchemesMapping",
    "create_issue_type_scheme": "createIssueTypeScheme",
    "update_issue_type_scheme": "updateIssueTypeScheme",
    "delete_issue_type_scheme": "deleteIssueTypeScheme",
    "get_issue_type_scheme_for_projects": "getIssueTypeSchemeForProjects",
    "assign_issue_type_scheme": "assignIssueTypeSchemeToProject",
    "add_issue_types_to_scheme": "addIssueTypesToIssueTypeScheme",
    "remove_issue_type_from_scheme": "removeIssueTypeFromIssueTypeScheme",
    "reorder_issue_types_in_scheme": "reorderIssueTypesInIssueTypeScheme",
    "get_issue_type_screen_schemes": "getIssueTypeScreenSchemes",
    "get_issue_type_screen_scheme": "getIssueTypeScreenSchemes",
    "get_issue_type_screen_scheme_mappings": "getIssueTypeScreenSchemeMappings",
    "get_project_issue_type_screen_schemes": "getIssueTypeScreenSchemeProjectAssociations",
    "get_permission_schemes": "getAllPermissionSchemes",
    "get_permission_scheme": "getPermissionScheme",
    "create_permission_scheme": "createPermissionScheme",
    "update_permission_scheme": "updatePermissionScheme",
    "delete_permission_scheme": "deletePermissionScheme",
    "get_permission_scheme_grants": "getPermissionSchemeGrants",
    "create_permission_grant": "createPermissionGrant",
    "get_permission_grant": "getPermissionSchemeGrant",
    "delete_permission_grant": "deletePermissionSchemeEntity",
    "get_all_permissions": "getAllPermissions",
    "get_my_permissions": "getMyPermissions",
    "get_project_permission_scheme": "getAssignedPermissionScheme",
    "assign_permission_scheme_to_project": "assignPermissionScheme",
    "get_project_notification_scheme": "getNotificationSchemeForProject",
    "get_projects_for_permission_scheme": "getAssignedPermissionScheme, searchProjects",
    "get_projects_for_workflow_scheme": "getWorkflowSchemeProjectAssociations, searchProjects",
    "get_project_roles": "getAllProjectRoles",
}

NOTES = {
    "upload_file": "Attachment use: --body with an @file part; arbitrary uploads have no generic equivalent.",
    "download_file": "Attachment use: --output PATH; arbitrary URL downloads are not indexed.",
    "upload_project_avatar": "Operation is indexed, but its raw image body is not accepted by the JSON/multipart generic surface.",
    "get_kb_article": "Use the Confluence pageId, not an assumed legacy article ID; follows the frozen jsm kb get replacement.",
    "get_knowledge_base_article": "Use the Confluence pageId; not a promise of legacy article-ID equivalence.",
    "create_service_desk": "Create a service_desk project with the required template and lead fields; the legacy POST service-desk route is absent.",
    "get_screen": "Page getScreens and select the screen ID; there is no singular getScreen operation.",
    "get_screen_scheme": "Filter getScreenSchemes with id.",
    "get_issue_type_screen_scheme": "Filter getIssueTypeScreenSchemes with id.",
    "get_attachments": "Select fields=attachment on getIssue.",
    "get_issue_links": "Select fields=issuelinks on getIssue.",
    "get_time_tracking": "Select fields=timetracking on getIssue.",
    "set_time_tracking": "Set fields.timetracking in the editIssue body.",
    "lookup_service_desk_by_project_key": "Page service desks, then match projectKey.",
    "lookup_notification_scheme_by_name": "Page schemes, then match name.",
    "get_projects_for_permission_scheme": "Page projects, read each assignment, then filter by scheme ID.",
    "get_projects_for_workflow_scheme": "Page projects and inspect workflow-scheme associations.",
    "get_pending_approvals": "Search bounded project issues, read approvals per issue, then filter pending approvals.",
    "get_my_approvals": "Search bounded project issues, read approvals per issue, then filter current-user pending approvals.",
    "link_knowledge_base_article": "Write a public link comment; no native KB relationship is implied.",
    "attach_article_as_solution": "Write a public solution comment; no native KB relationship is implied.",
}


def public_members(source: str, class_name: str) -> list[str]:
    """Read only directly declared public def members, including properties."""
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return sorted(
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    )


def capture(ref: str) -> dict:
    """Capture method names and immutable source identities, never source text."""
    inventory: dict = {"source_ref": ref, "blobs": {}}
    for module, name in (
        ("jira_client", "JiraClient"),
        ("automation_client", "AutomationClient"),
    ):
        spec = f"{ref}:src/jira_as/{module}.py"
        source = subprocess.check_output(["git", "show", spec], cwd=ROOT, text=True)
        inventory[name] = public_members(source, name)
        inventory["blobs"][name] = subprocess.check_output(
            ["git", "rev-parse", spec], cwd=ROOT, text=True
        ).strip()
    return inventory


def render(inventory: dict) -> str:
    """Fail closed if a captured member is absent or a stale mapping remains."""
    if set(inventory["JiraClient"]) != set(TARGETS):
        raise ValueError(
            "JiraClient mapping does not exactly cover the captured inventory"
        )
    lines = [
        "# Client method migration from 1.2.0",
        "",
        "Generated by `scripts/generate_client_method_mapping.py` from the captured",
        "public members in `tests/fixtures/client-methods-1.2.0.json` (AST of",
        "`git show 1.x:src/jira_as/jira_client.py`, plus AutomationClient). The fixture",
        "records both immutable Git blob IDs; regeneration needs no checkout of 1.x.",
        "",
        f"Coverage: **{len(inventory['JiraClient'])}/259 JiraClient methods** and",
        f"**{len(inventory['AutomationClient'])}/21 AutomationClient public members**",
        "(including its two configuration properties). Private and dunder members are excluded.",
        "",
        "An operation target means `jira-as api call <operationId>`; inspect parameters",
        "and body with `api describe <operationId>`. Multiple targets name the building",
        "blocks of the old helper, not one equivalent invocation. Python callers can",
        "use the product Surface.call. This is a migration guide, not a promise that",
        "legacy Python signatures, IDs, paging, response shapes or retry behavior match.",
        "",
        "Scope still applies: set an explicit project allowlist, provide matching",
        "`--project` for body-only identities, and opt into site operations separately",
        "where needed. Destructive operations preview until `--confirm`. Indexed",
        "operations with unsupported request media remain unavailable through api call.",
        "",
        "The rc retains legacy modules for the 16 deferred CLI verbs pending JAS-64",
        "and their existing helper/export/test dependencies. Assets and Automation",
        "remain on that legacy path. Low-level transport helpers and two absent API",
        "capabilities have explicit notes rather than fabricated operation targets.",
        "",
        "See [the wrapper decision table](wrapper-verbs.md) and",
        "[the Compatibility Contract](compatibility-contract.md) for the supported CLI guarantees.",
        "",
        "## JiraClient",
        "",
        "| 1.2.0 method | OperationId / surviving verb / migration disposition | Notes |",
        "|---|---|---|",
    ]
    for name in inventory["JiraClient"]:
        target = TARGETS[name]
        if target.startswith("verb: "):
            target = f"`{target[6:]}` (surviving verb)"
        elif target.startswith("note: "):
            target = target[6:]
        elif target != DEFERRED:
            target = ", ".join(f"`{op.strip()}`" for op in target.split(","))
        lines.append(f"| `{name}` | {target} | {NOTES.get(name, '')} |")
    lines.extend(
        [
            "",
            "## AutomationClient",
            "",
            "| 1.2.0 public member | Migration disposition |",
            "|---|---|",
        ]
    )
    lines.extend(f"| `{name}` | {DEFERRED} |" for name in inventory["AutomationClient"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture",
        metavar="REF",
        help="refresh the method-name fixture from local git",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed document without writing",
    )
    args = parser.parse_args()
    if args.capture:
        FIXTURE.write_text(json.dumps(capture(args.capture), indent=2) + "\n")
    inventory = json.loads(FIXTURE.read_text())
    rendered = render(inventory)
    if args.check:
        if OUTPUT.read_text() != rendered:
            parser.exit(1, "client method mapping is stale\n")
    else:
        OUTPUT.write_text(rendered)
    print(
        f"mapping coverage: {len(inventory['JiraClient'])}/259 JiraClient; "
        f"{len(inventory['AutomationClient'])}/21 AutomationClient"
    )


if __name__ == "__main__":
    main()
