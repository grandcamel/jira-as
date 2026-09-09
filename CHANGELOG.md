# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- JAS-77: resolve the socket subprocess test's `jira-as` binary beside the running interpreter or on PATH, skipping with a clear reason when neither location provides it.

### Removed

- JAS-76 / JAS-64, decision 34: retire the sixteen Automation, Assets and
  dev-status verbs at 2.0.0. Each remains a request-free migration shim that
  exits 2; `--help` exits 0. There is no indexed replacement.

| Retired verb | Migration disposition |
|---|---|
| `admin automation list` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation get` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation search` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation enable` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation disable` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation toggle` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation invoke` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation-template list` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `admin automation-template get` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `dev get-commits` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset list` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset get` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset create` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset update` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset link` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |
| `jsm asset find-affected` | `note: retired at 2.0.0; no indexed replacement — JAS-64, decision 34` |

### Added

- JAS-52: Split Mode adds same-build `jira-as serve` and credential-free socket clients, authoritative validation/scope binding and private call logs; engine `fake_sidecar` tests use the same Responder seam. Binary downloads/output and multipart uploads are explicitly unsupported.

## [2.0.0rc1] - 2026-09-09

Main is the 2.0 line (spec JAS-31; wayfinder map JAS-6). Fixes for the pinned 1.x line land on branch `1.x`.

### Added
- JAS-45: jira-as runs on as-engine. The Jira platform v3, Jira Software and
  Jira Service Management Base Documents are vendored under
  `src/jira_as/specs` with a manifest (version, sha256, fetch date) and
  compiled by the build hook into `src/jira_as/_generated` (catalog +
  `platform`/`software`/`servicedesk` indexes, in the wheel, never committed).
  New `api` group (`call`, `search`, `describe`, `topics`; `--transport
  responder` and `JIRA_AS_TRANSPORT`), `help` levels with a Level 0 template,
  `engine.py` over the existing configuration chain, lazy package exports and
  lazy legacy-group registration so discovery loads no client code. Identity
  overlays disambiguate 20 duplicate operationIds (Software `getIssue` →
  `getSoftwareIssue`, `getConfiguration` → `getBoardConfiguration`, the
  sprint/organization/request-type property quartets, the Service Management
  skip-permission-check and service-desk variants). Generated paging tags with
  hand overrides (`getAuditRecords`, `getFailedWebhooks`; four user listings
  page until an empty page; four post-slice user searches refuse `--all`;
  `getAllUsers` maxResults capped at 1000). Ported
  `scripts/generate_paging_tags.py` and `scripts/refresh_base_documents.py`.
  The final wrapper inventory and retained legacy dependencies are recorded
  below under Removed verbs.
- Added generated project-scope metadata for all three Jira API documents,
  first-call project allowlist enforcement, matching --project for body
  identities, conservative bounded JQL, and explicit site-operation opt-in on
  the Generic Surface; keyed updates also validate hidden body project changes
  (JAS-46). (JAS-46)
- Added Jira v3 ADF schema references and Markdown conversion for issue,
  comment and worklog fields, including bulk issue input and raw reads;
  corrected four invalid enum defaults and two search examples, named the
  removed-search replacements, and seeded source-backed help notes and topics.
  Custom-field resolution follows the JAS-49 instance-field cache below. (JAS-47)
- Recorded the fourteen-operation jira-host Compatibility Contract and
  migrated its legacy commands to the generic Surface while preserving output
  and legacy exit codes; added responder compatibility coverage, normalized
  spaced and unspaced worklog durations, explicit description input formats,
  and bounded project-safe search ordering and link support (JAS-48). (JAS-48)
- Wrapper Verbs under the rule (JAS-49): all 208 legacy verbs classified in
  `tests/wrapper_verbs.json` / `docs/wrapper-verbs.md` — 35 survivors (bulk,
  clone, transition/resolve/reopen, project discovery and cache, JSM
  sequences, reports, local transforms, cache/autocomplete affordances)
  rebuilt on the generic transport with the stateful simulation; 143 single-
  operation and prerequisite-chain wrappers REMOVED and replaced by migration
  shims that name the indexed `api call` replacement and exit 2 (admin 56, JSM
  34, agile 11, collaborate 9, lifecycle 9, search 8, time 5, issue 4, fields
  3, dev 2, relationships 2); the 14 Compatibility Contract verbs unchanged;
  16 verbs deferred on the legacy client pending JAS-64 (Automation, Assets,
  dev-status). New `fields list/get/cache warm` over a v2 instance-fields
  cache (`JIRA_FIELDS_CACHE_DIR`, 24 h TTL); cached textarea custom fields
  auto-resolve markdown to ADF on `api call`, and repeatable `--adf-field`
  overrides per call. ADF helpers no longer emit empty text nodes (JAS-27).
  Attachment transport and risk-tag enrichment are included in JAS-65 below. (JAS-49)
- Risk enrichment (JAS-65): every DELETE operation in the three pinned Jira
  documents (platform 89, software 24, servicedesk 10) and 24 destructive
  bulk, move, archive and removal operations carry `x-as-risk` (`destructive`
  or `irreversible`), activating the default zero-request preview and the
  explicit `--confirm` on `api call`; the `risk` help topic lists the
  irreversible set. Attachment downloads (`getAttachmentContent`,
  `getAttachmentThumbnail`) stream to `api call --output PATH`;
  `addAttachment` sends multipart uploads; the two attachment migration hints
  no longer carry a limitation note. (JAS-65)
- Cassette-backed Compatibility Contract tests (synthetic fixture and argv
  sidecar under tests/cassettes/), an SBX-only cassette recorder
  (scripts/record_cassettes.py), a cleanup-tracked live suite under tests/live
  for the dev wrapper, generated dev-wrapper argv checks, and a three-document
  Base Document drift job (scripts/check_base_document_drift.py, drift
  workflow). Host recording and live SBX validation are supervisor-run release
  acceptance steps. (JAS-50)
- Cassette recorder keeps and reports its original failed step when cleanup
  also fails; the SBX live-suite cleanup tolerates the JQL index's lag with
  per-key leak checks and detailed errors; recreated SBX keys are owned again;
  the bulk-update dry-run check asserts would_update/issues/changes. (JAS-68)
- SBX live-suite cleanup asks the JQL search for the issue key (`--fields
  key`) in label recovery and verification — the current Jira Cloud search
  returns id-only items otherwise — and reports id-only items as a malformed
  envelope; `tests/cassettes/compatibility.json` re-recorded with the as-
  engine response-header allowlist (Authorization and Set-Cookie placeholders
  removed from all 37 interactions). (JAS-71)
- `agile estimate` and the contract's story-points resolution on a site with
  both "Story Points" and "Story point estimate" fields: the field is chosen
  by project type (team-managed → Story point estimate, company-managed →
  Story Points) through one guarded `getProject` read, memoised per project;
  explicit per-project configuration still overrides; a single candidate needs
  no project read; the refusal remains only when neither rule names one field.
  (JAS-67)

### Removed verbs

The frozen [wrapper decision table](docs/wrapper-verbs.md) classifies all 208
1.x verbs: **143 dropped, 14 Compatibility Contract verbs kept, 35 survivors
kept, and 16 deferred on the legacy client pending JAS-64**. Dropped invocations
are migration shims: they send no requests, print the replacement and exit 2;
`--help` still exits 0. Parameter names and bodies now follow `api describe`.

| Removed 1.x verb | Generic Surface replacement |
|---|---|
| `admin project list` | `api call searchProjects` |
| `admin project get` | `api call getProject --projectIdOrKey PROJECT_KEY` |
| `admin project create` | `api call createProject --body @body.json` |
| `admin project update` | `api call updateProject --projectIdOrKey PROJECT_KEY --body @body.json` |
| `admin project delete` | `api call deleteProject --projectIdOrKey PROJECT_KEY` |
| `admin project archive` | `api call archiveProject --projectIdOrKey PROJECT_KEY` |
| `admin project restore` | `api call restore --projectIdOrKey PROJECT_KEY` |
| `admin config get` | `api call getProject --projectIdOrKey PROJECT_KEY` |
| `admin category list` | `api call getAllProjectCategories` |
| `admin category create` | `api call createProjectCategory --body @body.json` |
| `admin category assign` | `api call updateProject --projectIdOrKey PROJECT_KEY --body @body.json` |
| `admin user search` | `api call findUsers` |
| `admin user get` | `api call getUser` |
| `admin group list` | `api call findGroups` |
| `admin group members` | `api call getUsersFromGroup` |
| `admin group create` | `api call createGroup --body @body.json` |
| `admin group delete` | `api call removeGroup` |
| `admin group add-user` | `api call addUserToGroup --body @body.json` |
| `admin group remove-user` | `api call removeUserFromGroup --accountId ACCOUNT_ID` |
| `admin permission-scheme list` | `api call getAllPermissionSchemes` |
| `admin permission-scheme get` | `api call getPermissionScheme --schemeId SCHEME_ID` |
| `admin permission-scheme create` | `api call createPermissionScheme --body @body.json` |
| `admin permission-scheme assign` | `api call assignPermissionScheme --projectKeyOrId PROJECT_KEY_OR_ID --body @body.json` |
| `admin permission list` | `api call getAllPermissions` |
| `admin permission check` | `api call getMyPermissions` |
| `admin notification-scheme list` | `api call getNotificationSchemes --projectId PROJECT_KEY` |
| `admin notification-scheme get` | `api call getNotificationScheme --id ID` |
| `admin notification-scheme create` | `api call createNotificationScheme --body @body.json` |
| `admin notification add` | `api call addNotifications --id ID --body @body.json` |
| `admin notification remove` | `api call removeNotificationFromNotificationScheme --notificationSchemeId NOTIFICATION_SCHEME_ID --notificationId NOTIFICATION_ID` |
| `admin screen list` | `api call getScreens` |
| `admin screen get` | `api call getScreens` |
| `admin screen tabs` | `api call getAllScreenTabs --screenId SCREEN_ID --projectKey PROJECT_KEY` |
| `admin screen fields` | `api call getAllScreenTabFields --screenId SCREEN_ID --tabId TAB_ID --projectKey PROJECT_KEY` |
| `admin screen add-field` | `api call addScreenTabField --screenId SCREEN_ID --tabId TAB_ID --body @body.json` |
| `admin screen remove-field` | `api call removeScreenTabField --screenId SCREEN_ID --tabId TAB_ID --id ID` |
| `admin screen-scheme list` | `api call getScreenSchemes` |
| `admin screen-scheme get` | `api call getScreenSchemes` |
| `admin issue-type list` | `api call getIssueAllTypes` |
| `admin issue-type get` | `api call getIssueType --id ID` |
| `admin issue-type create` | `api call createIssueType --body @body.json` |
| `admin issue-type update` | `api call updateIssueType --id ID --body @body.json` |
| `admin issue-type delete` | `api call deleteIssueType --id ID` |
| `admin issue-type-scheme list` | `api call getAllIssueTypeSchemes` |
| `admin issue-type-scheme get` | `api call getAllIssueTypeSchemes` |
| `admin issue-type-scheme create` | `api call createIssueTypeScheme --body @body.json` |
| `admin issue-type-scheme assign` | `api call assignIssueTypeSchemeToProject --body @body.json --project PROJECT_KEY` |
| `admin issue-type-scheme project` | `api call getIssueTypeSchemeForProjects --projectId PROJECT_ID` |
| `admin workflow list` | `api call getWorkflowsPaginated` |
| `admin workflow get` | `api call getWorkflowsPaginated` |
| `admin workflow search` | `api call getWorkflowsPaginated` |
| `admin workflow for-issue` | `api call getWorkflowsPaginated` |
| `admin workflow-scheme list` | `api call getAllWorkflowSchemes` |
| `admin workflow-scheme get` | `api call getWorkflowScheme --id ID` |
| `admin workflow-scheme assign` | `api call switchWorkflowSchemeForProject --body @body.json --project PROJECT_KEY` |
| `admin status list` | `api call getStatuses` |
| `agile board list` | `api call getAllBoards --projectKeyOrId PROJECT_KEY` |
| `agile epic create` | `api call createIssue --body @body.json --project PROJECT_KEY` |
| `agile epic get` | `api call getIssue --issueIdOrKey ISSUE_KEY` |
| `agile epic add-issues` | `api call moveIssuesToEpic --epicIdOrKey EPIC_KEY --field issues=["ISSUE_KEY"]` |
| `agile sprint list` | `api call getAllSprints --boardId BOARD_ID` |
| `agile sprint create` | `api call createSprint --body @body.json` |
| `agile sprint get` | `api call getSprint --sprintId SPRINT_ID` |
| `agile backlog` | `api call getIssuesForBacklog --boardId BOARD_ID` |
| `agile rank` | `api call rankIssues --body @body.json` |
| `agile estimates` | `api call getIssuesForSprint --sprintId SPRINT_ID` |
| `agile subtask` | `api call createIssue --body @body.json --project PROJECT_KEY` |
| `collaborate comment update` | `api call updateComment --issueIdOrKey ISSUE_KEY --id ID --body @body.json` |
| `collaborate comment delete` | `api call deleteComment --issueIdOrKey ISSUE_KEY --id ID` |
| `collaborate attachment upload` | `api call addAttachment --issueIdOrKey ISSUE_KEY --body @body.json` |
| `collaborate attachment list` | `api call getIssue --issueIdOrKey ISSUE_KEY` |
| `collaborate attachment download` | `api call getAttachmentContent --id ID` |
| `collaborate watchers` | `api call getIssueWatchers --issueIdOrKey ISSUE_KEY` |
| `collaborate activity` | `api call getChangeLogs --issueIdOrKey ISSUE_KEY` |
| `collaborate notify` | `api call notify --issueIdOrKey ISSUE_KEY --body @body.json` |
| `collaborate update-fields` | `api call editIssue --issueIdOrKey ISSUE_KEY --body @body.json` |
| `dev link-commit` | `api call storeDevelopmentInformation --Authorization AUTHORIZATION --body @body.json` |
| `dev link-pr` | `api call storeDevelopmentInformation --Authorization AUTHORIZATION --body @body.json` |
| `fields create` | `api call createCustomField --body @body.json` |
| `fields check-project` | `api call getCreateIssueMetaIssueTypeId --projectIdOrKey PROJECT_KEY --issueTypeId ISSUE_TYPE_ID` |
| `fields configure-agile` | `api call addScreenTabField --screenId SCREEN_ID --tabId TAB_ID --body @body.json` |
| `issue delete` | `api call deleteIssue --issueIdOrKey ISSUE_KEY` |
| `issue transitions` | `api call getTransitions --issueIdOrKey ISSUE_KEY` |
| `issue transition` | `lifecycle transition ISSUE_KEY --to TRANSITION_NAME` |
| `issue comment` | `api call addComment --issueIdOrKey ISSUE_KEY --body @body.json` |
| `jsm service-desk list` | `api call getServiceDesks` |
| `jsm service-desk get` | `api call getServiceDeskById --serviceDeskId SERVICE_DESK_ID` |
| `jsm service-desk create` | `api call createProject --field key=KEY --field name=NAME --field projectTypeKey=service_desk --field projectTemplateKey=TEMPLATE --field leadAccountId=ACCOUNT_ID` |
| `jsm request-type list` | `api call getRequestTypes --serviceDeskId SERVICE_DESK_ID` |
| `jsm request-type get` | `api call getRequestTypeById --serviceDeskId SERVICE_DESK_ID --requestTypeId REQUEST_TYPE_ID` |
| `jsm request-type fields` | `api call getRequestTypeFields --serviceDeskId SERVICE_DESK_ID --requestTypeId REQUEST_TYPE_ID` |
| `jsm request list` | `api call searchAndReconsileIssuesUsingJql --jql PROJECT_KEY` |
| `jsm request create` | `api call createCustomerRequest --body @body.json` |
| `jsm request get` | `api call getCustomerRequestByIdOrKey --issueIdOrKey ISSUE_KEY` |
| `jsm request status` | `api call getCustomerRequestStatus --issueIdOrKey ISSUE_KEY` |
| `jsm request comment` | `api call createRequestComment --issueIdOrKey ISSUE_KEY --body @body.json` |
| `jsm request comments` | `api call getRequestComments --issueIdOrKey ISSUE_KEY` |
| `jsm request participants` | `api call getRequestParticipants --issueIdOrKey ISSUE_KEY` |
| `jsm request add-participant` | `api call addRequestParticipants --issueIdOrKey ISSUE_KEY --body @body.json` |
| `jsm request remove-participant` | `api call removeRequestParticipants --issueIdOrKey ISSUE_KEY --body @body.json` |
| `jsm customer list` | `api call getCustomers --serviceDeskId SERVICE_DESK_ID` |
| `jsm customer add` | `api call addCustomers --serviceDeskId SERVICE_DESK_ID --body @body.json` |
| `jsm customer remove` | `api call removeCustomers --serviceDeskId SERVICE_DESK_ID --body @body.json` |
| `jsm organization list` | `api call getOrganizations` |
| `jsm organization get` | `api call getOrganization --organizationId ORGANIZATION_ID` |
| `jsm organization create` | `api call createOrganization --body @body.json` |
| `jsm organization delete` | `api call deleteOrganization --organizationId ORGANIZATION_ID` |
| `jsm organization add-customer` | `api call addUsersToOrganization --organizationId ORGANIZATION_ID --body @body.json` |
| `jsm organization remove-customer` | `api call removeUsersFromOrganization --organizationId ORGANIZATION_ID --body @body.json` |
| `jsm queue list` | `api call getQueues --serviceDeskId SERVICE_DESK_ID` |
| `jsm queue get` | `api call getQueue --serviceDeskId SERVICE_DESK_ID --queueId QUEUE_ID` |
| `jsm queue issues` | `api call getIssuesInQueue --serviceDeskId SERVICE_DESK_ID --queueId QUEUE_ID` |
| `jsm sla get` | `api call getSlaInformation --issueIdOrKey ISSUE_KEY` |
| `jsm sla check-breach` | `api call getSlaInformation --issueIdOrKey ISSUE_KEY` |
| `jsm approval list` | `api call getApprovals --issueIdOrKey ISSUE_KEY` |
| `jsm approval approve` | `api call answerApproval --issueIdOrKey ISSUE_KEY --approvalId APPROVAL_ID --body @body.json` |
| `jsm approval decline` | `api call answerApproval --issueIdOrKey ISSUE_KEY --approvalId APPROVAL_ID --body @body.json` |
| `jsm kb search` | `api call getServiceDeskArticles --serviceDeskId SERVICE_DESK_ID --query QUERY` |
| `jsm kb get` | `api call viewArticle --pageId PAGE_ID` |
| `lifecycle assign` | `api call assignIssue --issueIdOrKey ISSUE_KEY --body @body.json` |
| `lifecycle version list` | `api call getProjectVersions --projectIdOrKey PROJECT_KEY` |
| `lifecycle version create` | `api call createVersion --body @body.json --project PROJECT_KEY` |
| `lifecycle version release` | `api call updateVersion --id ID --body @body.json --project PROJECT_KEY` |
| `lifecycle version archive` | `api call updateVersion --id ID --body @body.json --project PROJECT_KEY` |
| `lifecycle component list` | `api call getProjectComponents --projectIdOrKey PROJECT_KEY` |
| `lifecycle component create` | `api call createComponent --body @body.json --project PROJECT_KEY` |
| `lifecycle component update` | `api call updateComponent --id ID --body @body.json --project PROJECT_KEY` |
| `lifecycle component delete` | `api call deleteComponent --id ID` |
| `relationships get-blockers` | `api call getIssue --issueIdOrKey ISSUE_KEY` |
| `relationships get-dependencies` | `api call getIssue --issueIdOrKey ISSUE_KEY` |
| `search validate` | `api call parseJqlQueries --validation VALIDATION --body @body.json` |
| `search filter list` | `api call getFiltersPaginated --projectId PROJECT_KEY` |
| `search filter create` | `api call createFilter --body @body.json` |
| `search filter run` | `api call searchAndReconsileIssuesUsingJql --jql PROJECT_KEY` |
| `search filter update` | `api call updateFilter --id ID --body @body.json` |
| `search filter delete` | `api call deleteFilter --id ID` |
| `search filter share` | `api call addSharePermission --id ID --body @body.json` |
| `search filter favourite` | `api call setFavouriteForFilter --id ID` |
| `time worklogs` | `api call getIssueWorklog --issueIdOrKey ISSUE_KEY` |
| `time update-worklog` | `api call updateWorklog --issueIdOrKey ISSUE_KEY --id ID --body @body.json` |
| `time delete-worklog` | `api call deleteWorklog --issueIdOrKey ISSUE_KEY --id ID` |
| `time estimate` | `api call editIssue --issueIdOrKey ISSUE_KEY --field fields.timetracking.originalEstimate=VALUE --field fields.timetracking.remainingEstimate=VALUE` |
| `time tracking` | `api call getIssue --issueIdOrKey ISSUE_KEY` |

#### Compatibility Contract verbs kept (14)

- `agile estimate`
- `collaborate comment add`
- `collaborate comment list`
- `issue get`
- `issue create`
- `issue update`
- `lifecycle transition`
- `lifecycle transitions`
- `relationships link`
- `relationships unlink`
- `relationships get-links`
- `relationships link-types`
- `search query`
- `time log`

#### Surviving Wrapper Verbs kept (35)

- `agile sprint manage`
- `agile sprint move-issues`
- `agile velocity`
- `bulk transition`
- `bulk assign`
- `bulk set-priority`
- `bulk clone`
- `bulk delete`
- `dev branch-name`
- `dev pr-description`
- `dev parse-commits`
- `fields list`
- `jsm request transition`
- `jsm customer create`
- `jsm sla report`
- `jsm approval pending`
- `jsm kb suggest`
- `lifecycle resolve`
- `lifecycle reopen`
- `ops cache-status`
- `ops cache-clear`
- `ops cache-warm`
- `ops discover-project`
- `relationships clone`
- `relationships bulk-link`
- `relationships stats`
- `search export`
- `search build`
- `search suggest`
- `search fields`
- `search functions`
- `search bulk-update`
- `time report`
- `time export`
- `time bulk-log`

#### Deferred on the legacy client pending JAS-64 (16)

- `admin automation list`
- `admin automation get`
- `admin automation search`
- `admin automation enable`
- `admin automation disable`
- `admin automation toggle`
- `admin automation invoke`
- `admin automation-template list`
- `admin automation-template get`
- `dev get-commits`
- `jsm asset list`
- `jsm asset get`
- `jsm asset create`
- `jsm asset update`
- `jsm asset link`
- `jsm asset find-affected`

Decision 31 ships the rc with these 16 deferred verbs; JAS-64 is required
before 2.0.0 final. The legacy client and mock remain whole because existing
configuration, exports, helpers and tests still import them. Their retention
supports the deferred CLI path and compatibility dependencies; it does not
reintroduce the 143 removed verbs.

### Rename table

These 20 identity-overlay renames disambiguate published operationIds across
and within the three Base Documents. The document and route identify the old
operation unambiguously; use the new name with `api call`. They are distinct
from the removed-verb replacements above.

| Document | Published operationId | Route | Indexed operationId |
|---|---|---|---|
| servicedesk | `createCustomer` | `POST /rest/servicedeskapi/customer/skip-permission-check` | `createCustomerWithoutPermissionCheck` |
| servicedesk | `getPropertiesKeys` | `GET /rest/servicedeskapi/organization/{organizationId}/property` | `getOrganizationPropertyKeys` |
| servicedesk | `deleteProperty` | `DELETE /rest/servicedeskapi/organization/{organizationId}/property/{propertyKey}` | `deleteOrganizationProperty` |
| servicedesk | `getProperty` | `GET /rest/servicedeskapi/organization/{organizationId}/property/{propertyKey}` | `getOrganizationProperty` |
| servicedesk | `setProperty` | `PUT /rest/servicedeskapi/organization/{organizationId}/property/{propertyKey}` | `setOrganizationProperty` |
| servicedesk | `getAttachmentContent` | `GET /rest/servicedeskapi/request/{issueIdOrKey}/attachment/{attachmentId}` | `getRequestAttachmentContent` |
| servicedesk | `getAttachmentThumbnail` | `GET /rest/servicedeskapi/request/{issueIdOrKey}/attachment/{attachmentId}/thumbnail` | `getRequestAttachmentThumbnail` |
| servicedesk | `addCustomers` | `POST /rest/servicedeskapi/servicedesk/{serviceDeskId}/customer/skip-permission-check` | `addCustomersWithoutPermissionCheck` |
| servicedesk | `getArticles` | `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/knowledgebase/article` | `getServiceDeskArticles` |
| servicedesk | `getOrganizations` | `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/organization` | `getServiceDeskOrganizations` |
| servicedesk | `getPropertiesKeys` | `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property` | `getRequestTypePropertyKeys` |
| servicedesk | `deleteProperty` | `DELETE /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property/{propertyKey}` | `deleteRequestTypeProperty` |
| servicedesk | `getProperty` | `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property/{propertyKey}` | `getRequestTypeProperty` |
| servicedesk | `setProperty` | `PUT /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property/{propertyKey}` | `setRequestTypeProperty` |
| software | `getConfiguration` | `GET /rest/agile/1.0/board/{boardId}/configuration` | `getBoardConfiguration` |
| software | `getIssue` | `GET /rest/agile/1.0/issue/{issueIdOrKey}` | `getSoftwareIssue` |
| software | `getPropertiesKeys` | `GET /rest/agile/1.0/sprint/{sprintId}/properties` | `getSprintPropertyKeys` |
| software | `deleteProperty` | `DELETE /rest/agile/1.0/sprint/{sprintId}/properties/{propertyKey}` | `deleteSprintProperty` |
| software | `getProperty` | `GET /rest/agile/1.0/sprint/{sprintId}/properties/{propertyKey}` | `getSprintProperty` |
| software | `setProperty` | `PUT /rest/agile/1.0/sprint/{sprintId}/properties/{propertyKey}` | `setSprintProperty` |

### Migration from 1.2.0

- The configuration chain and existing names remain unchanged: environment
  variables override Keychain, `settings.local.json`, `settings.json` and
  defaults. Continue using `JIRA_SITE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN`.
  No credential migration is needed.
- New instance-field metadata uses `~/.cache/jira-as/v2/instance-fields.json`
  with a 24-hour TTL. `JIRA_FIELDS_CACHE_DIR` or `jira.fields_cache_dir` chooses
  its directory. This cache does not import 1.x cache contents; run `fields
  cache warm` explicitly. Existing legacy cache affordances remain available.
- Replace removed wrappers with `jira-as api call <operationId>`. Use `api
  search` and `api describe` to discover operations, exact parameter names,
  required schemas and help. Supply JSON via `--body @file`, `--body -` or
  repeated `--field path=value`; attachment file parts use `@path`, and
  binary responses use `--output PATH`. `--all` pages supported operations;
  `--limit` caps the total. Parameter/body and output shapes follow the spec,
  so wrapper flags are not automatically interchangeable with API parameters.
- Set `JIRA_ALLOWED_PROJECTS` (or `jira.allowed_projects`) explicitly. Keyed
  identities must be allowed; body-only identities require a matching
  `--project KEY`. An absent allowlist refuses project calls. Site-wide
  operations additionally require `JIRA_ALLOW_SITE_OPERATIONS=true`; that
  opt-in does not waive project checks. These guards also run offline.
- Generic errors are JSON on stderr: usage/validation 2, authentication 3,
  permission/scope 4, not found 5, server/transport 6 and conflict 7; success
  is 0. The fourteen [Compatibility Contract](docs/compatibility-contract.md)
  verbs keep their output and legacy exits (success 0, operational failure 1,
  Click usage 2). Destructive generic operations return a zero-request preview
  until `--confirm` is supplied.
- The complete [1.2.0 public client method mapping](docs/client-method-mapping.md)
  covers 259/259 JiraClient methods and 21/21 AutomationClient public members.
  It distinguishes operation targets, surviving workflows, deferred Assets and
  Automation, local helpers, and APIs without an indexed replacement. Python
  consumers must migrate signatures and result handling deliberately; a listed
  operation is not a drop-in replacement for a legacy method.

### Fixed
- JAS-62: `test_real_worktree_identity_does_not_follow_cwd` skips outside a git checkout (a `git archive` export, as the Promotion dry run builds); cherry-picked from 1.2.1.
- JAS-73: the live SBX suite waits for Jira's JQL index before a search that
  follows a create (the bulk-update dry run, `contract:search:0` and the
  generic JQL search case): `SbxSession.wait_for_index` polls the gated
  search at most 5 times 3 s apart, reports the lag in the test output and
  names the key and attempts on exhaustion; the assertions are unchanged.

## [1.2.0] - 2026-09-06

### Added
- JAS-2: `jira-as --version` identifies the imported package with its version
  and checkout commit (marked dirty when modified), or a source-content build
  stamp for directory installs. Missing build metadata is reported explicitly.
- `scripts/check_release_tag.py v<version>` refuses a release tag unless it
  matches the package, runtime version, and top changelog release.
- JAS-1: `admin project create --style classic|team-managed`. The `scrum`,
  `kanban` and `basic` shorthands still map to the team-managed (simplified)
  templates by default and map to the company-managed templates with
  `--style classic`; a full key or fixed alias that contradicts an explicit
  style is refused before creation; the create output (text and JSON) reports
  the project's actual style read back from Jira. Reference:
  `docs/project-templates.md`, including the trashed key/name reservation.
- JAS-4: optional `jira.allowed_projects` setting and `JIRA_ALLOWED_PROJECTS`
  override refuse outside-project issue keys, explicit project values and
  literal JQL project operands before the shared CLI client is created,
  mock mode included. Documented in `docs/allowed-projects.md` as defence in
  depth with its coverage limits; the organization's boundary remains its
  wrappers.

### Fixed
- JAS-5: `admin permission check` no longer crashes; `JiraClient.get_my_permissions`
  calls `/rest/api/3/mypermissions` with a non-empty default permission set
  (Jira Cloud requires one), the mock matches the real signature, and the
  mock-parity test now also flags mock-only methods (84 legacy ones are
  listed as named exceptions).

### Changed
- Every landing consumed by a Promotion must bump the package version and add
  a changelog entry; its release tag must be `v<version>`. This wave targets
  1.2.0, with later wave entries appended here before release.
- The CLI reads the package's own version, so editable installs report version
  changes immediately without reinstalling stale distribution metadata.

## [1.1.3] - 2026-08-18

### Added
- **Issue parent handling**: `issue create --parent` and `issue update --parent`
  set the modern `parent` field instead of smuggling a key into the epic-link
  custom field. `issue create --parent-via-update` creates the issue first and
  sets the parent in a follow-up update, for workflows whose validators reject
  a parent at create time.
- **ADF auto-wrap**: plain-string values for rich-text fields are converted to
  ADF on create and update; values that are already ADF pass through unchanged.
  `JIRA_ADF_CUSTOM_FIELDS` (comma-separated field IDs) extends the built-in
  `description`/`environment` set.
- `issue create --dry-run` builds and prints the payload without calling the API.
- **Issue group aliases**: `issue transitions` (read-only), `issue transition`
  (same options as `lifecycle transition`), and `issue comment` (alias for
  `collaborate comment add`, with `--format text|markdown|adf`). Each delegates
  to the canonical implementation so behaviour cannot drift.
- **Per-project agile fields**: `get_agile_fields()` and `get_agile_field()`
  take an optional `project_key`, and the new `get_project_agile_fields()`
  reads `jira.projects.<KEY>.agile_fields` from settings, which outranks the
  global and environment values. `issue create --story-points` resolves its
  field ID against the target project rather than a global custom field ID.
- **Remote links**: `JiraClient.create_remote_link()`, `get_remote_links()` and
  `delete_remote_link()`, surfaced as `relationships link --remote-url` with
  `--remote-title` and `--remote-relationship`. A native link rejected with 404
  or 403 now hints at `--remote-url`, which reaches cross-project and JSM
  targets that a native link cannot.
- **`agile board list`**: lists boards from `/rest/agile/1.0/board` with
  `isLast` pagination and `--project`, `--type scrum|kanban`, `--output
  text|json`. An unscoped listing warns that it covers every board on the site.
- `fields list --project` and `--issue-type` scope the listing to a project's
  create-screen fields instead of the whole instance catalogue.
- `ops discover-project` reports field fill rates, value distributions for the
  low-cardinality fields, and parent-hierarchy hints.
- `request create` gains `--priority` and `--labels`; `request comment` gains
  `--format text|wiki` and `--dry-run`.
- `JiraClient.get_statuses()`, `get_project_notification_scheme()`,
  `get_board_issues()`, `move_issues_to_backlog()`, and scheme-to-project
  enumeration for permission and workflow schemes, with mock counterparts.

### Changed
- **Search pagination**: `/rest/api/3/search/jql` caps a page at 100 issues.
  `search_issues()` now caps each request accordingly and, when `max_results`
  exceeds the cap and the caller is not paging manually, walks `nextPageToken`
  until the requested count or the last page. Explicit `next_page_token` or
  `start_at` paging stays single-page.
- `search export` keeps nested field values as real JSON in JSON exports; CSV
  collapses objects to their display name or to compact JSON rather than a
  Python repr.
- `request create --summary` is now optional, and the request type's field
  metadata is checked first so required fields the API cannot set (portal-only
  and asset-backed pickers) are named explicitly instead of returning an opaque
  400. `--dry-run` respects `-o json`.
- `issue-type-scheme create` requires `--issue-types`; the API rejects a scheme
  with no issue types.
- Ruff is the sole import sorter. The isort pre-commit hook and `[tool.isort]`
  config are removed.
- Coverage `fail_under` lowered from 70 to 60. The 70 target had never been met
  (main sat at 59.8%); the suite now clears 62%, so the gate is enforceable
  rather than permanently red.

### Fixed
- **13 admin commands** called `JiraClient` methods that do not exist or used
  the wrong signature: notification scheme create/add/remove, permission scheme
  assign and project listing, issue type create, issue type scheme
  get/create/assign/project lookup, workflow scheme get/assign, workflow for
  issue, and `status list`. Screen and screen scheme IDs are coerced to int at
  the CLI boundary with a clear error for non-numeric input.
- `admin project config --show-schemes` crashed on a missing
  `get_project_notification_scheme()`.
- **JSM envelope handling**: `request comments`, `request participants`,
  `approval list`, `request-type fields` and `asset affected` returned the raw
  `{"values": [...]}` envelope where a list was declared. `request comments`
  also ignored `--internal-only` entirely.
- `request status` read `status` off the status-history envelope, so its text
  output always showed `N/A`. It now reports the most recent entry.
- Repaired JSM client calls that would have failed at runtime: `service-desk
  create` (wrong parameters), `request remove-participant` (singular method
  name), `customer create` (service desk passed as the email positional, and an
  API-required display name that could be omitted), `kb search` (result cap
  passed as `highlight`), `kb suggest` (nonexistent method), and `request
  create` (int IDs where the API expects strings).
- `search export` with no matching issues raised `KeyError: 'output_file'`. An
  empty result now writes a header-only CSV or an empty JSON envelope, exit 0.
- `sprint close --move-incomplete-to` passed a sprint ID where a list of issue
  keys belongs and read a return value from a method that returns `None`.
- `agile backlog` falls back to the board's issues when the board exposes no
  backlog endpoint, as Kanban and team-managed boards often do not. Resolving a
  project to a board now warns when the project has several, naming the one
  chosen.
- `issue update --no-notify` returned 403 for non-administrators, losing the
  edit along with the notification suppression. It now retries with
  `notifyUsers` omitted so the update still applies, and warns on stderr. The
  mock accepts `notify_users` for parity.
- `testing.py` called `client.post(json=...)` four times; `post()` takes
  `data`, so every `IssueBuilder.build()` and search assertion raised
  `TypeError`. These now use the typed client methods.
- `jira_client.py` and `automation_client.py` contained
  `from error_handler import ...` statements that would have raised
  `ModuleNotFoundError` when reached.
- Bulk and issue commands passed `issue.get("key")` into client calls, sending
  `None` to the API instead of failing loudly on a malformed result.
- The mock's screen `--scope` filter read a key no seeded screen carried, so it
  silently returned nothing.
- The mock's `get_request_participants()` returned a bare list where the real
  client returns a paginated envelope, breaking mock-mode callers that unwrap
  `values`.
- `JiraClient.post()` accepted a raw string body in its implementation (the
  watcher API needs one) but not in its type annotation.
- `mypy src` passes clean; the branch started with 91 errors.

---

## [1.1.2] - 2026-08-18

### Fixed
- `version list` and `component list` called `JiraClient.get_versions()` and
  `get_components()`, which do not exist. They now use `get_project_versions()`
  and `get_project_components()`.
- The mock's `get_all_boards()` now leads with `project_key` in the same order
  as the real client, keeping `project_key_or_id` as a compatibility alias.
- `relationships get-blockers --include-done` was accepted but ignored.
  Completed blockers are now filtered out by default, with `statusCategory`
  preferred over the status name so non-English workflows classify correctly.

---

## [1.0.0] - 2025-01-20

### Changed
- **BREAKING**: Package renamed from `jira-assistant-skills` to `jira-as`
- **BREAKING**: Module renamed from `jira_assistant_skills_lib` to `jira_as`
- All imports must be updated: `from jira_as import ...`
- Updated dependency to `assistant-skills-lib>=1.0.0`

---

## Previous Releases (as jira-assistant-skills)

## [1.2.0] - 2025-01-20

### Changed
- **BREAKING**: Removed profile feature from `ConfigManager`
  - Removed `profile` parameter from `get_client()`, `get_default_project()`, `get_agile_fields()`, `get_agile_field()`, `get_automation_client()`
  - Removed `get_profile_config()` method
  - Removed `JIRA_PROFILE` environment variable support and deprecation warning
- Updated dependency to `assistant-skills-lib>=1.0.0`

## [1.1.0-pre] - 2025-01-18

### Added
- Comprehensive test coverage for CLI and helper modules
  - `cli/main.py`: 0% → 93% coverage
  - `mock/factories.py`: 0% → 100% coverage
  - `search_helpers.py`: 23% → 100% coverage
  - `user_helpers.py`: 32% → 100% coverage
  - `permission_helpers.py`: 17% → 99% coverage
  - `mock_responses.py`: 0% → 100% coverage
- Ruff linter configuration in `pyproject.toml`
- Explicit `__all__` exports in `formatters.py`

### Fixed
- All mypy type errors resolved (strict type checking now passes)
- Missing re-exports in `formatters.py` (export_csv, format_json, etc.)
- Type annotations for collection variables across codebase

### Changed
- Updated dev tools: black 26.1.0, ruff 0.14.13, uv 0.9.26
- Import ordering standardized with ruff

## [1.0.0] - 2025-01-17

### Added
- `jira-as` CLI with 13 command groups (issue, search, lifecycle, fields, ops, bulk, dev, relationships, time, collaborate, agile, jsm, admin)
- Context manager pattern for `JiraClient` and `MockJiraClient`
- Mixin-based mock client architecture for better maintainability
- Shared factories for mock response building

### Changed
- **BREAKING**: Package renamed from `jira-as` to `jira-as`
- **BREAKING**: Requires Python 3.10+ (dropped 3.8/3.9 support)
- Refactored to use `assistant-skills-lib` base library

### Fixed
- Exception hierarchy alignment (UserNotFoundError, BatchError)
- Deprecation warnings in board lookup

## [0.2.2] - 2025-01-10

### Added
- Mock client support via `JIRA_MOCK_MODE=true` environment variable
- `next_page_token` support in mock `search_issues`

### Fixed
- MockJiraClient returned correctly when mock mode enabled

## [0.2.1] - 2025-01-09

### Added
- Mixin-based mock client architecture
- Consolidated scenario support in mock client

## [0.1.5] - 2025-01-08

### Added
- Initial mock_responses.py implementation

## [0.1.0] - 2025-01-01

### Added
- Initial release
- JiraClient with retry logic and error handling
- ConfigManager for multi-source configuration
- Validators for JIRA-specific formats
- Formatters for tables, JSON, CSV output
- ADF helper for Atlassian Document Format conversion
- Time utilities for JIRA time format parsing
- SQLite-based caching with TTL support
- Credential manager with keychain support

[1.2.0]: https://github.com/grandcamel/jira-as/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/grandcamel/jira-as/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/grandcamel/jira-as/compare/v0.2.2...v1.0.0
[0.2.2]: https://github.com/grandcamel/jira-as/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/grandcamel/jira-as/compare/v0.1.5...v0.2.1
[0.1.5]: https://github.com/grandcamel/jira-as/compare/v0.1.0...v0.1.5
[0.1.0]: https://github.com/grandcamel/jira-as/releases/tag/v0.1.0
