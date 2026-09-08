# Wrapper verbs and migration

Decision 21 accepts 208 original verbs: **35 survivors, 143 dropped, 14 contract, 16 deferred**. Source: `tests/wrapper_verbs.json`. Deferred legacy commands and their guards remain unchanged pending JAS-64. Jira attachment transport and generic risk enrichment remain pending JAS-65.

| Verb | Class | Decision | Reason | Replacement / operations |
|---|---|---|---|---|
| admin project list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call searchProjects |
| admin project get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getProject --projectIdOrKey PROJECT_KEY |
| admin project create | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createProject --body @body.json |
| admin project update | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateProject --projectIdOrKey PROJECT_KEY --body @body.json |
| admin project delete | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteProject --projectIdOrKey PROJECT_KEY |
| admin project archive | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call archiveProject --projectIdOrKey PROJECT_KEY |
| admin project restore | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call restore --projectIdOrKey PROJECT_KEY |
| admin config get | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getProject --projectIdOrKey PROJECT_KEY |
| admin category list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllProjectCategories |
| admin category create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createProjectCategory --body @body.json |
| admin category assign | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateProject --projectIdOrKey PROJECT_KEY --body @body.json |
| admin user search | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call findUsers |
| admin user get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getUser |
| admin group list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call findGroups |
| admin group members | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getUsersFromGroup |
| admin group create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createGroup --body @body.json |
| admin group delete | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeGroup |
| admin group add-user | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addUserToGroup --body @body.json |
| admin group remove-user | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeUserFromGroup --accountId ACCOUNT_ID |
| admin automation list | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation get | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation search | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation enable | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation disable | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation toggle | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation invoke | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation-template list | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin automation-template get | A | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| admin permission-scheme list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllPermissionSchemes |
| admin permission-scheme get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getPermissionScheme --schemeId SCHEME_ID |
| admin permission-scheme create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createPermissionScheme --body @body.json |
| admin permission-scheme assign | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call assignPermissionScheme --projectKeyOrId PROJECT_KEY_OR_ID --body @body.json |
| admin permission list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllPermissions |
| admin permission check | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getMyPermissions |
| admin notification-scheme list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getNotificationSchemes --projectId PROJECT_KEY |
| admin notification-scheme get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getNotificationScheme --id ID |
| admin notification-scheme create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createNotificationScheme --body @body.json |
| admin notification add | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addNotifications --id ID --body @body.json |
| admin notification remove | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeNotificationFromNotificationScheme --notificationSchemeId NOTIFICATION_SCHEME_ID --notificationId NOTIFICATION_ID |
| admin screen list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getScreens |
| admin screen get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getScreens |
| admin screen tabs | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllScreenTabs --screenId SCREEN_ID --projectKey PROJECT_KEY |
| admin screen fields | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllScreenTabFields --screenId SCREEN_ID --tabId TAB_ID --projectKey PROJECT_KEY |
| admin screen add-field | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addScreenTabField --screenId SCREEN_ID --tabId TAB_ID --body @body.json |
| admin screen remove-field | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeScreenTabField --screenId SCREEN_ID --tabId TAB_ID --id ID |
| admin screen-scheme list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getScreenSchemes |
| admin screen-scheme get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getScreenSchemes |
| admin issue-type list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssueAllTypes |
| admin issue-type get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssueType --id ID |
| admin issue-type create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createIssueType --body @body.json |
| admin issue-type update | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateIssueType --id ID --body @body.json |
| admin issue-type delete | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteIssueType --id ID |
| admin issue-type-scheme list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllIssueTypeSchemes |
| admin issue-type-scheme get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllIssueTypeSchemes |
| admin issue-type-scheme create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createIssueTypeScheme --body @body.json |
| admin issue-type-scheme assign | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call assignIssueTypeSchemeToProject --body @body.json --project PROJECT_KEY |
| admin issue-type-scheme project | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssueTypeSchemeForProjects --projectId PROJECT_ID |
| admin workflow list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getWorkflowsPaginated |
| admin workflow get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getWorkflowsPaginated |
| admin workflow search | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getWorkflowsPaginated |
| admin workflow for-issue | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getWorkflowsPaginated |
| admin workflow-scheme list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllWorkflowSchemes |
| admin workflow-scheme get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getWorkflowScheme --id ID |
| admin workflow-scheme assign | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call switchWorkflowSchemeForProject --body @body.json --project PROJECT_KEY |
| admin status list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getStatuses |
| agile board list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllBoards --projectKeyOrId PROJECT_KEY |
| agile epic create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createIssue --body @body.json --project PROJECT_KEY |
| agile epic get | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssue --issueIdOrKey ISSUE_KEY |
| agile epic add-issues | B | dropped | One indexed operation accepts the issues array; the legacy per-issue loop is unnecessary. | api call moveIssuesToEpic --epicIdOrKey EPIC_KEY --field issues=["ISSUE_KEY"] |
| agile sprint list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getAllSprints --boardId BOARD_ID |
| agile sprint create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createSprint --body @body.json |
| agile sprint get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getSprint --sprintId SPRINT_ID |
| agile sprint manage | B | survivor | Rule: Close mode searches incomplete issues; branch to move them; close sprint only after move succeeds; preserve start/update modes. | searchAndReconsileIssuesUsingJql, moveIssuesToSprintAndRank, partiallyUpdateSprint |
| agile sprint move-issues | B | survivor | Rule: Select scoped issues; choose backlog/sprint; chunk and loop mutation with preview. | searchAndReconsileIssuesUsingJql, moveIssuesToSprintAndRank, moveIssuesToBacklog |
| agile backlog | B | dropped | Board resolution is a prerequisite; the 404 fallback is an error path. | api call getIssuesForBacklog --boardId BOARD_ID |
| agile rank | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call rankIssues --body @body.json |
| agile estimate | B | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getFields, editIssue |
| agile estimates | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssuesForSprint --sprintId SPRINT_ID |
| agile velocity | B | survivor | Rule: Select closed sprints; loop scoped issue searches; compute velocity aggregates not covered by tags. | getAllSprints, searchAndReconsileIssuesUsingJql |
| agile subtask | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createIssue --body @body.json --project PROJECT_KEY |
| bulk transition | B | survivor | Rule: Search scoped issues; loop issues; read transitions; fuzzy-match or report ambiguity; preview or transition; optional comment; checkpoint. | searchAndReconsileIssuesUsingJql, getTransitions, doTransition, addComment |
| bulk assign | A | survivor | Rule: Search scoped issues; loop selected issues; preview or assign; checkpoint each outcome. | searchAndReconsileIssuesUsingJql, assignIssue |
| bulk set-priority | A | survivor | Rule: Search scoped issues; loop selected issues; preview or update priority; checkpoint each outcome. | searchAndReconsileIssuesUsingJql, editIssue |
| bulk clone | B | survivor | Rule: Select issues; loop source issues; copy fields; create parent; branch into subtask and link copying; checkpoint. | searchAndReconsileIssuesUsingJql, getIssue, createIssue, linkIssues |
| bulk delete | A | survivor | Rule: Search scoped issues; preview by default; loop deletes only on explicit confirmation; checkpoint each outcome. | searchAndReconsileIssuesUsingJql, deleteIssue |
| collaborate comment add | C | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | addComment |
| collaborate comment list | C | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getComments |
| collaborate comment update | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateComment --issueIdOrKey ISSUE_KEY --id ID --body @body.json |
| collaborate comment delete | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteComment --issueIdOrKey ISSUE_KEY --id ID |
| collaborate attachment upload | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. Jira multipart/binary enrichment remains pending JAS-65; this indexed pointer does not claim completed attachment transport. | api call addAttachment --issueIdOrKey ISSUE_KEY --body @body.json |
| collaborate attachment list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssue --issueIdOrKey ISSUE_KEY |
| collaborate attachment download | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. Jira multipart/binary enrichment remains pending JAS-65; this indexed pointer does not claim completed attachment transport. | api call getAttachmentContent --id ID |
| collaborate watchers | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssueWatchers --issueIdOrKey ISSUE_KEY |
| collaborate activity | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getChangeLogs --issueIdOrKey ISSUE_KEY |
| collaborate notify | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call notify --issueIdOrKey ISSUE_KEY --body @body.json |
| collaborate update-fields | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call editIssue --issueIdOrKey ISSUE_KEY --body @body.json |
| dev branch-name | A | survivor | Rule: Read issue; transform key/type/summary into a branch name with local naming policy; no tag expresses this. | getIssue |
| dev pr-description | C | survivor | Rule: Read issue; assemble a PR template from issue metadata; ADF conversion itself uses engine tags. | getIssue |
| dev parse-commits | D | survivor | Rule: Local commit-message parsing workflow not expressed by an API operation or tag. | Local-only / deferred |
| dev link-commit | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call storeDevelopmentInformation --Authorization AUTHORIZATION --body @body.json |
| dev link-pr | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call storeDevelopmentInformation --Authorization AUTHORIZATION --body @body.json |
| dev get-commits | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| fields list | A | survivor | Rule: Instance metadata/cache affordance: read fields cache only; report cold cache; explicit fields cache warm performs bounded getFields. | getFields |
| fields create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createCustomField --body @body.json |
| fields check-project | E | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getCreateIssueMetaIssueTypeId --projectIdOrKey PROJECT_KEY --issueTypeId ISSUE_TYPE_ID |
| fields configure-agile | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addScreenTabField --screenId SCREEN_ID --tabId TAB_ID --body @body.json |
| issue get | C | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssue, getComments |
| issue create | B | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | createIssue, editIssue, moveIssuesToSprintAndRank, linkIssues, getFields, getCurrentUser |
| issue update | A | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | editIssue |
| issue delete | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteIssue --issueIdOrKey ISSUE_KEY |
| issue transitions | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getTransitions --issueIdOrKey ISSUE_KEY |
| issue transition | B | dropped | Duplicate of the preserved lifecycle transition contract verb; use its fuzzy matching workflow. | lifecycle transition ISSUE_KEY --to TRANSITION_NAME |
| issue comment | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addComment --issueIdOrKey ISSUE_KEY --body @body.json |
| jsm service-desk list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getServiceDesks |
| jsm service-desk get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getServiceDeskById --serviceDeskId SERVICE_DESK_ID |
| jsm service-desk create | A | dropped | Service desks are projects; create a service_desk project with the chosen template and lead. | api call createProject --field key=KEY --field name=NAME --field projectTypeKey=service_desk --field projectTemplateKey=TEMPLATE --field leadAccountId=ACCOUNT_ID |
| jsm request-type list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getRequestTypes --serviceDeskId SERVICE_DESK_ID |
| jsm request-type get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getRequestTypeById --serviceDeskId SERVICE_DESK_ID --requestTypeId REQUEST_TYPE_ID |
| jsm request-type fields | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getRequestTypeFields --serviceDeskId SERVICE_DESK_ID --requestTypeId REQUEST_TYPE_ID |
| jsm request list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call searchAndReconsileIssuesUsingJql --jql PROJECT_KEY |
| jsm request create | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createCustomerRequest --body @body.json |
| jsm request get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getCustomerRequestByIdOrKey --issueIdOrKey ISSUE_KEY |
| jsm request status | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getCustomerRequestStatus --issueIdOrKey ISSUE_KEY |
| jsm request transition | B | survivor | Rule: Read customer transitions; select unambiguous fuzzy match; perform selected transition. | getCustomerTransitions, performCustomerTransition |
| jsm request comment | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createRequestComment --issueIdOrKey ISSUE_KEY --body @body.json |
| jsm request comments | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getRequestComments --issueIdOrKey ISSUE_KEY |
| jsm request participants | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getRequestParticipants --issueIdOrKey ISSUE_KEY |
| jsm request add-participant | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addRequestParticipants --issueIdOrKey ISSUE_KEY --body @body.json |
| jsm request remove-participant | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeRequestParticipants --issueIdOrKey ISSUE_KEY --body @body.json |
| jsm customer list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getCustomers --serviceDeskId SERVICE_DESK_ID |
| jsm customer create | B | survivor | Rule: Create customer; only on success and supplied service desk add returned account; report each outcome. | createCustomer, addCustomers |
| jsm customer add | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addCustomers --serviceDeskId SERVICE_DESK_ID --body @body.json |
| jsm customer remove | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeCustomers --serviceDeskId SERVICE_DESK_ID --body @body.json |
| jsm organization list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getOrganizations |
| jsm organization get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getOrganization --organizationId ORGANIZATION_ID |
| jsm organization create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createOrganization --body @body.json |
| jsm organization delete | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteOrganization --organizationId ORGANIZATION_ID |
| jsm organization add-customer | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addUsersToOrganization --organizationId ORGANIZATION_ID --body @body.json |
| jsm organization remove-customer | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call removeUsersFromOrganization --organizationId ORGANIZATION_ID --body @body.json |
| jsm queue list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getQueues --serviceDeskId SERVICE_DESK_ID |
| jsm queue get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getQueue --serviceDeskId SERVICE_DESK_ID --queueId QUEUE_ID |
| jsm queue issues | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssuesInQueue --serviceDeskId SERVICE_DESK_ID --queueId QUEUE_ID |
| jsm sla get | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getSlaInformation --issueIdOrKey ISSUE_KEY |
| jsm sla check-breach | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getSlaInformation --issueIdOrKey ISSUE_KEY |
| jsm sla report | B | survivor | Rule: Search explicit project/JQL; loop keyed SLA reads; aggregate breach report. | searchAndReconsileIssuesUsingJql, getSlaInformation |
| jsm approval list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getApprovals --issueIdOrKey ISSUE_KEY |
| jsm approval pending | A | survivor | Rule: Search explicit project/JQL; loop request approval reads; retain pending decisions; no guessed SD-<id> project. | searchAndReconsileIssuesUsingJql, getApprovals |
| jsm approval approve | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call answerApproval --issueIdOrKey ISSUE_KEY --approvalId APPROVAL_ID --body @body.json |
| jsm approval decline | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call answerApproval --issueIdOrKey ISSUE_KEY --approvalId APPROVAL_ID --body @body.json |
| jsm kb search | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getServiceDeskArticles --serviceDeskId SERVICE_DESK_ID --query QUERY |
| jsm kb get | A | dropped | The id is the article's Confluence page id; use the indexed article view operation. | api call viewArticle --pageId PAGE_ID |
| jsm kb suggest | A | survivor | Rule: Read keyed request; extract its service desk and summary field; choose keywords or report none; query desk articles. | getCustomerRequestByIdOrKey, getServiceDeskArticles |
| jsm asset list | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| jsm asset get | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| jsm asset create | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| jsm asset update | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| jsm asset link | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| jsm asset find-affected | B | deferred | Deferred pending JAS-64. Retain the legacy command/client/1.x guard and tests unchanged; no matching operation in the pinned indexes. | Local-only / deferred |
| lifecycle transition | B | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssue, getTransitions, doTransition, addComment, moveIssuesToSprintAndRank |
| lifecycle transitions | A | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getTransitions |
| lifecycle assign | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call assignIssue --issueIdOrKey ISSUE_KEY --body @body.json |
| lifecycle resolve | B | survivor | Rule: Read transitions; select an unambiguous resolve transition by fuzzy name; transition with resolution; optional comment. | getTransitions, doTransition, addComment |
| lifecycle reopen | B | survivor | Rule: Read transitions; select an unambiguous reopen transition by fuzzy name; transition; optional comment. | getTransitions, doTransition, addComment |
| lifecycle version list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getProjectVersions --projectIdOrKey PROJECT_KEY |
| lifecycle version create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createVersion --body @body.json --project PROJECT_KEY |
| lifecycle version release | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateVersion --id ID --body @body.json --project PROJECT_KEY |
| lifecycle version archive | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateVersion --id ID --body @body.json --project PROJECT_KEY |
| lifecycle component list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getProjectComponents --projectIdOrKey PROJECT_KEY |
| lifecycle component create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createComponent --body @body.json --project PROJECT_KEY |
| lifecycle component update | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateComponent --id ID --body @body.json --project PROJECT_KEY |
| lifecycle component delete | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteComponent --id ID |
| ops cache-status | D | survivor | Rule: Cache affordance: inspect local cache without HTTP. | Local-only / deferred |
| ops cache-clear | D | survivor | Rule: Cache affordance: preview or clear local cache; preserve existing behavior and HOME chmod boundary. | Local-only / deferred |
| ops cache-warm | B | survivor | Rule: Cache affordance: select requested metadata sets; read through Surface and persist to cache; optional per-project loop. | searchProjects, getFields, getIssueAllTypes, getPriorities, findAssignableUsers |
| ops discover-project | E | survivor | Rule: Read project metadata and sampled scoped issues; branch on available fields; aggregate context and field distributions. | getProject, getAllStatuses, getProjectVersions, getProjectComponents, searchAndReconsileIssuesUsingJql |
| relationships link | B | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssueLinkTypes, linkIssues |
| relationships unlink | B | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssue, deleteIssueLink |
| relationships get-links | A | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssue |
| relationships get-blockers | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssue --issueIdOrKey ISSUE_KEY |
| relationships get-dependencies | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssue --issueIdOrKey ISSUE_KEY |
| relationships link-types | A | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | getIssueLinkTypes |
| relationships clone | B | survivor | Rule: Read source; create parent; conditionally loop subtasks and links; preserve link direction and report failures. | getIssue, createIssue, linkIssues |
| relationships bulk-link | B | survivor | Rule: Search; per issue read existing links; skip duplicates or create links; checkpoint. | searchAndReconsileIssuesUsingJql, getIssue, linkIssues |
| relationships stats | B | survivor | Rule: Search scoped issues; loop issue-link reads; aggregate graph statistics that no tag expresses. | searchAndReconsileIssuesUsingJql, getIssue |
| search query | A | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | searchAndReconsileIssuesUsingJql |
| search export | C | survivor | Rule: Scoped paged search; CSV projection/file export transform not covered by generic JSON/table/markdown formats. | searchAndReconsileIssuesUsingJql |
| search validate | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call parseJqlQueries --validation VALIDATION --body @body.json |
| search build | D | survivor | Rule: Local JQL-template assembly and quoting transform not expressed by a tag; optional indexed syntax validation. | parseJqlQueries |
| search suggest | D | survivor | Rule: Autocomplete/cache affordance: return cached suggestions or refresh through Surface. | getFieldAutoCompleteForQueryString |
| search fields | D | survivor | Rule: Autocomplete/cache affordance: return cached JQL field metadata or refresh through Surface; distinct from instance getFields cache. | getAutoComplete |
| search functions | D | survivor | Rule: Autocomplete/cache affordance: filter cached function metadata or refresh through Surface. | getAutoComplete |
| search bulk-update | B | survivor | Rule: Scoped search; loop per-issue updates with dry-run and checkpoints. | searchAndReconsileIssuesUsingJql, editIssue |
| search filter list | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getFiltersPaginated --projectId PROJECT_KEY |
| search filter create | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call createFilter --body @body.json |
| search filter run | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call searchAndReconsileIssuesUsingJql --jql PROJECT_KEY |
| search filter update | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateFilter --id ID --body @body.json |
| search filter delete | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteFilter --id ID |
| search filter share | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call addSharePermission --id ID --body @body.json |
| search filter favourite | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call setFavouriteForFilter --id ID |
| time log | C | contract | JAS-48 immutable compatibility verb; keep its callback, flags, output, and generic adapter behavior. | addWorklog |
| time worklogs | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssueWorklog --issueIdOrKey ISSUE_KEY |
| time update-worklog | C | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call updateWorklog --issueIdOrKey ISSUE_KEY --id ID --body @body.json |
| time delete-worklog | B | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call deleteWorklog --issueIdOrKey ISSUE_KEY --id ID |
| time estimate | B | dropped | Read-merge-write is a prerequisite chain. Pass both originalEstimate and remainingEstimate values. | api call editIssue --issueIdOrKey ISSUE_KEY --field fields.timetracking.originalEstimate=VALUE --field fields.timetracking.remainingEstimate=VALUE |
| time tracking | A | dropped | Single indexed operation or prerequisite-only chain; use the generic surface. | api call getIssue --issueIdOrKey ISSUE_KEY |
| time report | B | survivor | Rule: Search scoped issues; loop worklog reads; aggregate by requested report dimensions. | searchAndReconsileIssuesUsingJql, getIssueWorklog |
| time export | B | survivor | Rule: Search scoped issues; loop worklog reads; transform rows to CSV file. | searchAndReconsileIssuesUsingJql, getIssueWorklog |
| time bulk-log | B | survivor | Rule: Select scoped issues; loop validation and worklog mutation with dry-run and checkpoints. | searchAndReconsileIssuesUsingJql, getIssue, addWorklog |


## Risk and confirmed calls

The generic surface now tags every DELETE and the documented destructive
non-DELETE operations as `destructive` or `irreversible`. Both levels default to
a JSON preview (exit 0), containing `dry_run`, `operationId`, `risk`, `method`,
`path`, validated `parameters` and `body`. No request, prerequisite lookup or
version read occurs. The preview reports unresolved aliases and version
requirements when applicable; it does not prove scope or remote validation.
Use `--confirm` to run the usual guarded call. `api describe OPERATION` shows the
level; `help risk` lists tagged irreversible operations and existing risk notes,
with explicit `--offset` continuation. Direct Python Surface calls retain their
existing behavior, and surviving workflows keep their own preview/confirmation.

```bash
jira-as api --transport responder call deleteIssue --issueIdOrKey SBX-1
jira-as api --transport responder call deleteIssue --issueIdOrKey SBX-1 --confirm
```

The two attachment migration hints above were recorded before JAS-65. Their
indexed replacements now support multipart upload with `--field file=@PATH`
(`X-Atlassian-Token: nocheck` is added) and binary download with `--output PATH`.
Downloads without `--output` use the sanitized response filename. File writes
are atomic; one same-origin redirect is allowed, and all cross-origin redirects
are refused. A numeric attachment ID has no project identity, so the existing
site-operation guard still applies. For an offline responder download only:

```bash
JIRA_ALLOWED_PROJECTS=SBX JIRA_ALLOW_SITE_OPERATIONS=true jira-as api --transport responder call getAttachmentContent --id 10000 --output attachment.bin
```

With only `JIRA_ALLOWED_PROJECTS=SBX`, that download remains refused (exit 4).
