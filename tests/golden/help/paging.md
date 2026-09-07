# paging

## bulkGetGroups

Bulk get groups

## bulkGetUsers

Bulk get users

## bulkGetUsersMigration

Automatic paging stops at the first empty response and advances by the requested maxResults, including short nonempty pages. Supply a page size the server accepts. Automatic paging is unsupported for findBulkAssignableUsers, findAssignableUsers, findUsersWithAllPermissions, and findUsersWithBrowsePermission: they filter after slicing, so an empty page does not prove exhaustion. Use getAllUsers plus caller-side filtering.

## findComponentsForProjects

Find components for projects

## findUserKeysByQuery

Find user keys by query

## findUsers

Automatic paging stops at the first empty response and advances by the requested maxResults, including short nonempty pages. Supply a page size the server accepts. The endpoint searches at most the first 1000 users; --all does not remove that limit.

## findUsersByQuery

Find users by query

## getAllBoards

Get all boards

## getAllDashboards

Get all dashboards

## getAllFieldConfigurationSchemes

Get all field configuration schemes

## getAllFieldConfigurations

Get all field configurations

## getAllIssueFieldOptions

Get all issue field options

## getAllIssueTypeSchemes

Get all issue type schemes

## getAllLabels

Get all labels

## getAllQuickFilters

Get all quick filters

## getAllRequestTypes

Get all request types

## getAllUsers

Automatic paging stops at the first empty response and advances by the requested maxResults, including short nonempty pages. Supply a page size the server accepts. Keep maxResults at or below the documented 1000-item server cap.

## getAllUsersDefault

Automatic paging stops at the first empty response and advances by the requested maxResults, including short nonempty pages. Supply a page size the server accepts. Keep maxResults at or below the documented 1000-item server cap.

## getAllWorkflowSchemes

Get all workflow schemes

## getApprovals

Get approvals

## getArticles

Get articles

## getAssetsWorkspaces

Get assets workspaces

## getAttachmentsForRequest

Get attachments for request

## getAuditRecords

Audit records use offset/limit and total, with the collection in records.

```sh
jira-as api call getAuditRecords --offset 0 --parameter-limit 25 --all --limit 50
```

## getAvailablePrioritiesByPriorityScheme

Get available priorities by priority scheme

## getBoardByFilterId

Get board by filter id

## getBoardIssuesForEpicJSIS

Get board issues for epic (enhanced)

## getBoardIssuesForSprintJSIS

Get board issues for sprint (enhanced)

## getBulkChangelogs

Bulk fetch changelogs

## getChangeLogs

Get changelogs

## getCommentAttachments

Get comment attachments

## getComments

Get comments

## getContextDefaultValues

Get default values for a custom field grouped by context and issue type

## getContextsForField

Get custom field contexts

Showing entries 1–34 of 125. Continue: help paging --offset 34.
