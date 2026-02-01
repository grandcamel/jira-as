# JIRA REST API Compliance Report
Generated: 2026-02-01 15:31:52

## Summary

| API | Spec Status | Categories | Methods | Matched | Compliant | Issues |
|-----|-------------|------------|---------|---------|-----------|--------|
| Platform v3 | ✅ Loaded | 29 | 178 | 128 | 92 | 36 |
| Agile | ✅ Loaded | 3 | 12 | 12 | 8 | 4 |
| Service Management | ✅ Loaded | 10 | 44 | 32 | 25 | 7 |
| Assets/Insight | ❌ Not Available | 1 | 15 | 0 | 0 | 0 |

## Critical Issues (Priority Fix)

1. **create_issues_bulk**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
2. **assign_issue**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
3. **create_issue_type**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
4. **update_issue_type**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
5. **create_issue_type_scheme**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
6. **update_issue_type_scheme**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
7. **get_issue_type_scheme_for_projects**: Missing required parameter: projectId
   - Expected: `projectId`
   - Actual: `['max_results', 'start_at', 'project_ids']`
8. **assign_issue_type_scheme**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
9. **add_issue_types_to_scheme**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
10. **reorder_issue_types_in_scheme**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
11. **get_project_issue_type_screen_schemes**: Missing required parameter: projectId
   - Expected: `projectId`
   - Actual: `['max_results', 'start_at', 'project_ids']`
12. **get_users_bulk**: Missing required parameter: accountId
   - Expected: `accountId`
   - Actual: `['max_results', 'account_ids']`
13. **create_sprint**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
14. **update_sprint**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
15. **move_issues_to_sprint**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
16. **rank_issues**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
17. **create_link**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
18. **create_project**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`
19. **get_workflow_scheme_for_project**: Missing required parameter: projectId
   - Expected: `projectId`
   - Actual: `['project_key_or_id']`
20. **assign_workflow_scheme_to_project**: Spec requires request body but method doesn't accept one
   - Expected: `required: true`
   - Actual: `No body parameter found`

... and 27 more critical issues

## Category Details

### Agile Boards ✅

- **API Type**: agile
- **Total Methods**: 4
- **Matched to Spec**: 4
- **Fully Compliant**: 4

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_board_backlog` | `/rest/agile/1.0/board/{board_id}/backlog` | GET | ✅ | - |
| `get_board` | `/rest/agile/1.0/board/{board_id}` | GET | ✅ | - |
| `get_all_boards` | `/rest/agile/1.0/board` | GET | ✅ | - |
| `delete_board` | `/rest/agile/1.0/board/{board_id}` | DELETE | ✅ | - |

### Agile Ranking ⚠️

- **API Type**: agile
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 0

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `rank_issues` | `/rest/agile/1.0/issue/rank` | PUT | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Agile Sprints ⚠️

- **API Type**: agile
- **Total Methods**: 7
- **Matched to Spec**: 7
- **Fully Compliant**: 4

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_sprint` | `/rest/agile/1.0/sprint/{sprint_id}` | GET | ✅ | - |
| `get_sprint_issues` | `/rest/agile/1.0/sprint/{sprint_id}/issue` | GET | ✅ | - |
| `create_sprint` | `/rest/agile/1.0/sprint` | POST | ⚠️ | 1 |
| `update_sprint` | `/rest/agile/1.0/sprint/{sprint_id}` | PUT | ⚠️ | 1 |
| `move_issues_to_sprint` | `/rest/agile/1.0/sprint/{sprint_id}/issue` | POST | ⚠️ | 1 |
| `get_board_sprints` | `/rest/agile/1.0/board/{board_id}/sprint` | GET | ✅ | - |
| `delete_sprint` | `/rest/agile/1.0/sprint/{sprint_id}` | DELETE | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Assets/Insight ❓

- **API Type**: assets
- **Total Methods**: 15
- **Matched to Spec**: 0
- **Fully Compliant**: 0

### JSM Approvals ⚠️

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_request_approvals` | `/rest/servicedeskapi/request/{issue_key}/approval` | GET | ✅ | - |
| `get_request_approval` | `/rest/servicedeskapi/request/{issue_key}/approval/{approval_id}` | GET | ✅ | - |
| `answer_approval` | `/rest/servicedeskapi/request/{issue_key}/approval/{approval_id}` | POST | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### JSM Comments ✅

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `add_request_comment` | `/rest/servicedeskapi/request/{issue_key}/comment` | POST | ✅ | - |
| `get_request_comments` | `/rest/servicedeskapi/request/{issue_key}/comment` | GET | ✅ | - |
| `get_request_comment` | `/rest/servicedeskapi/request/{issue_key}/comment/{comment_id}` | GET | ✅ | - |

### JSM Customers ⚠️

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 2
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_service_desk_customers` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/customer` | GET | ✅ | - |
| `add_customers_to_service_desk` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/customer` | POST | ⚠️ | 1 |

#### Unmatched Methods (not found in spec)

- `remove_customers_from_service_desk()` - DELETE N/A

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### JSM Knowledge Base ❓

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 0
- **Fully Compliant**: 0

#### Unmatched Methods (not found in spec)

- `get_kb_article()` - GET /rest/servicedeskapi/knowledgebase/article/{article_id}
- `suggest_kb_for_request()` - GET currentStatus
- `get_knowledge_base_spaces()` - GET /rest/servicedeskapi/servicedesk/{service_desk_id}/knowledgebase/category

### JSM Organizations ⚠️

- **API Type**: jsm
- **Total Methods**: 10
- **Matched to Spec**: 8
- **Fully Compliant**: 5

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_organizations` | `/rest/servicedeskapi/organization` | GET | ✅ | - |
| `create_organization` | `/rest/servicedeskapi/organization` | POST | ⚠️ | 1 |
| `get_organization` | `/rest/servicedeskapi/organization/{organization_id}` | GET | ✅ | - |
| `delete_organization` | `/rest/servicedeskapi/organization/{organization_id}` | DELETE | ✅ | - |
| `add_users_to_organization` | `/rest/servicedeskapi/organization/{organization_id}/user` | POST | ⚠️ | 1 |
| `get_service_desk_organizations` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/organization` | GET | ✅ | - |
| `add_organization_to_service_desk` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/organization` | POST | ⚠️ | 1 |
| `get_organization_users` | `/rest/servicedeskapi/organization/{organization_id}/user` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `remove_organization_from_service_desk()` - DELETE N/A
- `update_organization()` - POST /rest/servicedeskapi/organization/{organization_id}/property/name

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### JSM Participants ⚠️

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 2
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_request_participants` | `/rest/servicedeskapi/request/{issue_key}/participant` | GET | ✅ | - |
| `add_request_participants` | `/rest/servicedeskapi/request/{issue_key}/participant` | POST | ⚠️ | 1 |

#### Unmatched Methods (not found in spec)

- `remove_request_participants()` - DELETE N/A

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### JSM Queues ✅

- **API Type**: jsm
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_service_desk_queues` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/queue` | GET | ✅ | - |
| `get_queue` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/queue/{queue_id}` | GET | ✅ | - |
| `get_queue_issues` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/queue/{queue_id}/issue` | GET | ✅ | - |

### JSM Requests ⚠️

- **API Type**: jsm
- **Total Methods**: 9
- **Matched to Spec**: 7
- **Fully Compliant**: 6

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_request_types` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype` | GET | ✅ | - |
| `get_request_type` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype/{request_type_id}` | GET | ✅ | - |
| `get_request_type_fields` | `/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype/{request_type_id}/field` | GET | ✅ | - |
| `create_request` | `/rest/servicedeskapi/request` | POST | ✅ | - |
| `get_request` | `/rest/servicedeskapi/request/{issue_key}` | GET | ✅ | - |
| `get_request_status` | `/rest/servicedeskapi/request/{issue_key}/status` | GET | ✅ | - |
| `transition_request` | `/rest/servicedeskapi/request/{issue_key}/transition` | POST | ⚠️ | 1 |

#### Unmatched Methods (not found in spec)

- `get_request_transitions()` - GET values
- `link_asset_to_request()` - GET label

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### JSM SLAs ✅

- **API Type**: jsm
- **Total Methods**: 2
- **Matched to Spec**: 2
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_request_slas` | `/rest/servicedeskapi/request/{issue_key}/sla` | GET | ✅ | - |
| `get_request_sla` | `/rest/servicedeskapi/request/{issue_key}/sla/{sla_metric_id}` | GET | ✅ | - |

### JSM Service Desks ✅

- **API Type**: jsm
- **Total Methods**: 5
- **Matched to Spec**: 2
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_service_desks` | `/rest/servicedeskapi/servicedesk` | GET | ✅ | - |
| `get_service_desk` | `/rest/servicedeskapi/servicedesk/{service_desk_id}` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `create_service_desk()` - POST /rest/servicedeskapi/servicedesk
- `lookup_service_desk_by_project_key()` - GET projectKey
- `get_service_desk_agents()` - GET actors

### Async Tasks ✅

- **API Type**: platform
- **Total Methods**: 2
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_task_status` | `/rest/api/3/task/{task_id}` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `delete_project_async()` - GET taskId

### Components ⚠️

- **API Type**: platform
- **Total Methods**: 5
- **Matched to Spec**: 5
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `create_component` | `/rest/api/3/component` | POST | ⚠️ | 1 |
| `get_component` | `/rest/api/3/component/{component_id}` | GET | ✅ | - |
| `update_component` | `/rest/api/3/component/{component_id}` | PUT | ⚠️ | 1 |
| `get_project_components` | `/rest/api/3/project/{project_key}/components` | GET | ✅ | - |
| `get_component_issue_counts` | `/rest/api/3/component/{component_id}/relatedIssueCounts` | GET | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Filters ⚠️

- **API Type**: platform
- **Total Methods**: 12
- **Matched to Spec**: 12
- **Fully Compliant**: 9

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `create_filter` | `/rest/api/3/filter` | POST | ⚠️ | 1 |
| `get_filter` | `/rest/api/3/filter/{filter_id}` | GET | ✅ | - |
| `update_filter` | `/rest/api/3/filter/{filter_id}` | PUT | ⚠️ | 1 |
| `delete_filter` | `/rest/api/3/filter/{filter_id}` | DELETE | ✅ | - |
| `get_my_filters` | `/rest/api/3/filter/my` | GET | ✅ | - |
| `get_favourite_filters` | `/rest/api/3/filter/favourite` | GET | ✅ | - |
| `search_filters` | `/rest/api/3/filter/search` | GET | ✅ | - |
| `add_filter_favourite` | `/rest/api/3/filter/{filter_id}/favourite` | PUT | ✅ | - |
| `remove_filter_favourite` | `/rest/api/3/filter/{filter_id}/favourite` | DELETE | ✅ | - |
| `get_filter_permissions` | `/rest/api/3/filter/{filter_id}/permission` | GET | ✅ | - |
| `add_filter_permission` | `/rest/api/3/filter/{filter_id}/permission` | POST | ⚠️ | 1 |
| `delete_filter_permission` | `/rest/api/3/filter/{filter_id}/permission/{permission_id}` | DELETE | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Groups ⚠️

- **API Type**: platform
- **Total Methods**: 4
- **Matched to Spec**: 4
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `find_groups` | `/rest/api/3/groups/picker` | GET | ✅ | - |
| `get_group` | `/rest/api/3/group` | GET | ✅ | - |
| `create_group` | `/rest/api/3/group` | POST | ⚠️ | 1 |
| `get_group_members` | `/rest/api/3/group/member` | GET | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Issue Changelog ✅

- **API Type**: platform
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_changelog` | `/rest/api/3/issue/{issue_key}/changelog` | GET | ✅ | - |

### Issue Comments ✅

- **API Type**: platform
- **Total Methods**: 6
- **Matched to Spec**: 6
- **Fully Compliant**: 6

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `add_comment` | `/rest/api/3/issue/{issue_key}/comment` | POST | ✅ | - |
| `get_comments` | `/rest/api/3/issue/{issue_key}/comment` | GET | ✅ | - |
| `get_comment` | `/rest/api/3/issue/{issue_key}/comment/{comment_id}` | GET | ✅ | - |
| `update_comment` | `/rest/api/3/issue/{issue_key}/comment/{comment_id}` | PUT | ✅ | - |
| `delete_comment` | `/rest/api/3/issue/{issue_key}/comment/{comment_id}` | DELETE | ✅ | - |
| `add_comment_with_visibility` | `/rest/api/3/issue/{issue_key}/comment` | POST | ✅ | - |

### Issue Links ⚠️

- **API Type**: platform
- **Total Methods**: 4
- **Matched to Spec**: 3
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_link` | `/rest/api/3/issueLink/{link_id}` | GET | ✅ | - |
| `create_link` | `/rest/api/3/issueLink` | POST | ⚠️ | 1 |
| `delete_link` | `/rest/api/3/issueLink/{link_id}` | DELETE | ✅ | - |

#### Unmatched Methods (not found in spec)

- `get_link_types()` - GET issueLinkTypes

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Issue Management ⚠️

- **API Type**: platform
- **Total Methods**: 24
- **Matched to Spec**: 24
- **Fully Compliant**: 13

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_issue` | `/rest/api/3/issue/{issue_key}` | GET | ✅ | - |
| `create_issue` | `/rest/api/3/issue` | POST | ✅ | - |
| `create_issues_bulk` | `/rest/api/3/issue/bulk` | POST | ⚠️ | 1 |
| `get_create_issue_meta_issuetypes` | `/rest/api/3/issue/createmeta/{project_id_or_key}/issuetypes` | GET | ✅ | - |
| `get_create_issue_meta_fields` | `/rest/api/3/issue/createmeta/{project_id_or_key}/issuetypes/{issue_type_id}` | GET | ✅ | - |
| `assign_issue` | `/rest/api/3/issue/{issue_key}/assignee` | PUT | ⚠️ | 1 |
| `get_issue_types` | `/rest/api/3/issuetype` | GET | ✅ | - |
| `get_issue_type` | `/rest/api/3/issuetype/{issue_type_id}` | GET | ✅ | - |
| `create_issue_type` | `/rest/api/3/issuetype` | POST | ⚠️ | 1 |
| `update_issue_type` | `/rest/api/3/issuetype/{issue_type_id}` | PUT | ⚠️ | 1 |
| `get_issue_type_alternatives` | `/rest/api/3/issuetype/{issue_type_id}/alternatives` | GET | ✅ | - |
| `get_issue_type_schemes` | `/rest/api/3/issuetypescheme` | GET | ✅ | - |
| `get_issue_type_scheme_items` | `/rest/api/3/issuetypescheme/mapping` | GET | ✅ | - |
| `create_issue_type_scheme` | `/rest/api/3/issuetypescheme` | POST | ⚠️ | 1 |
| `update_issue_type_scheme` | `/rest/api/3/issuetypescheme/{scheme_id}` | PUT | ⚠️ | 1 |
| `delete_issue_type_scheme` | `/rest/api/3/issuetypescheme/{scheme_id}` | DELETE | ✅ | - |
| `get_issue_type_scheme_for_projects` | `/rest/api/3/issuetypescheme/project` | GET | ⚠️ | 1 |
| `assign_issue_type_scheme` | `/rest/api/3/issuetypescheme/project` | PUT | ⚠️ | 1 |
| `add_issue_types_to_scheme` | `/rest/api/3/issuetypescheme/{scheme_id}/issuetype` | PUT | ⚠️ | 1 |
| `remove_issue_type_from_scheme` | `/rest/api/3/issuetypescheme/{scheme_id}/issuetype/{issue_type_id}` | DELETE | ✅ | - |
| `reorder_issue_types_in_scheme` | `/rest/api/3/issuetypescheme/{scheme_id}/issuetype/move` | PUT | ⚠️ | 1 |
| `get_issue_type_screen_schemes` | `/rest/api/3/issuetypescreenscheme` | GET | ✅ | - |
| `get_issue_type_screen_scheme_mappings` | `/rest/api/3/issuetypescreenscheme/mapping` | GET | ✅ | - |
| `get_project_issue_type_screen_schemes` | `/rest/api/3/issuetypescreenscheme/project` | GET | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_required_param**: Missing required parameter: projectId
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- ... and 1 more issues

### Issue Transitions ✅

- **API Type**: platform
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `transition_issue` | `/rest/api/3/issue/{issue_key}/transitions` | POST | ✅ | - |

### JQL ⚠️

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_jql_autocomplete` | `/rest/api/3/jql/autocompletedata` | GET | ✅ | - |
| `get_jql_suggestions` | `/rest/api/3/jql/autocompletedata/suggestions` | GET | ✅ | - |
| `parse_jql` | `/rest/api/3/jql/parse` | POST | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Notification Schemes ⚠️

- **API Type**: platform
- **Total Methods**: 8
- **Matched to Spec**: 7
- **Fully Compliant**: 6

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_notification_schemes` | `/rest/api/3/notificationscheme` | GET | ✅ | - |
| `get_notification_scheme` | `/rest/api/3/notificationscheme/{scheme_id}` | GET | ✅ | - |
| `create_notification_scheme` | `/rest/api/3/notificationscheme` | POST | ✅ | - |
| `update_notification_scheme` | `/rest/api/3/notificationscheme/{scheme_id}` | PUT | ✅ | - |
| `add_notification_to_scheme` | `/rest/api/3/notificationscheme/{scheme_id}/notification` | PUT | ⚠️ | 1 |
| `delete_notification_scheme` | `/rest/api/3/notificationscheme/{scheme_id}` | DELETE | ✅ | - |
| `delete_notification_from_scheme` | `/rest/api/3/notificationscheme/{scheme_id}/notification/{notification_id}` | DELETE | ✅ | - |

#### Unmatched Methods (not found in spec)

- `lookup_notification_scheme_by_name()` - GET name

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Notifications ⚠️

- **API Type**: platform
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 0

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `notify_issue` | `/rest/api/3/issue/{issue_key}/notify` | POST | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Other ✅

- **API Type**: platform
- **Total Methods**: 35
- **Matched to Spec**: 2
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `delete_attachment` | `/rest/api/3/attachment/{attachment_id}` | DELETE | ✅ | - |
| `get_project_roles` | `/rest/api/3/role` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `get()` - GET N/A
- `post()` - POST N/A
- `put()` - PUT N/A
- `delete()` - DELETE N/A
- `upload_file()` - POST N/A
- `download_file()` - GET N/A
- `update_issue()` - PUT N/A
- `delete_issue()` - DELETE N/A
- `get_transitions()` - GET transitions
- `close()` - N/A N/A
- `get_issue_links()` - GET fields
- `delete_project()` - DELETE N/A
- `get_attachments()` - GET fields
- `add_worklog()` - POST N/A
- `update_worklog()` - PUT N/A
- `delete_worklog()` - DELETE N/A
- `get_time_tracking()` - GET fields
- `delete_version()` - DELETE N/A
- `delete_component()` - DELETE N/A
- `clone_issue()` - GET description
- `create_customer()` - GET accountId
- `get_pending_approvals()` - GET fields
- `search_kb_articles()` - GET values
- `get_my_approvals()` - N/A N/A
- `get_queues()` - N/A N/A
- `search_knowledge_base()` - N/A N/A
- `get_knowledge_base_article()` - N/A N/A
- `get_knowledge_base_suggestions()` - N/A N/A
- `link_knowledge_base_article()` - N/A N/A
- `attach_article_as_solution()` - N/A N/A
- `delete_group()` - DELETE N/A
- `upload_project_avatar()` - POST N/A
- `delete_issue_type()` - DELETE N/A

### Permission Schemes ⚠️

- **API Type**: platform
- **Total Methods**: 10
- **Matched to Spec**: 10
- **Fully Compliant**: 7

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_permission_schemes` | `/rest/api/3/permissionscheme` | GET | ✅ | - |
| `get_permission_scheme` | `/rest/api/3/permissionscheme/{scheme_id}` | GET | ✅ | - |
| `create_permission_scheme` | `/rest/api/3/permissionscheme` | POST | ⚠️ | 1 |
| `update_permission_scheme` | `/rest/api/3/permissionscheme/{scheme_id}` | PUT | ⚠️ | 1 |
| `delete_permission_scheme` | `/rest/api/3/permissionscheme/{scheme_id}` | DELETE | ✅ | - |
| `get_permission_scheme_grants` | `/rest/api/3/permissionscheme/{scheme_id}/permission` | GET | ✅ | - |
| `create_permission_grant` | `/rest/api/3/permissionscheme/{scheme_id}/permission` | POST | ⚠️ | 1 |
| `get_permission_grant` | `/rest/api/3/permissionscheme/{scheme_id}/permission/{permission_id}` | GET | ✅ | - |
| `delete_permission_grant` | `/rest/api/3/permissionscheme/{scheme_id}/permission/{permission_id}` | DELETE | ✅ | - |
| `get_all_permissions` | `/rest/api/3/permissions` | GET | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Project Avatars ⚠️

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_project_avatars` | `/rest/api/3/project/{project_key}/avatars` | GET | ✅ | - |
| `set_project_avatar` | `/rest/api/3/project/{project_key}/avatar` | PUT | ⚠️ | 1 |
| `delete_project_avatar` | `/rest/api/3/project/{project_key}/avatar/{avatar_id}` | DELETE | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Project Categories ⚠️

- **API Type**: platform
- **Total Methods**: 4
- **Matched to Spec**: 4
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_project_category` | `/rest/api/3/projectCategory/{category_id}` | GET | ✅ | - |
| `create_project_category` | `/rest/api/3/projectCategory` | POST | ⚠️ | 1 |
| `update_project_category` | `/rest/api/3/projectCategory/{category_id}` | PUT | ⚠️ | 1 |
| `delete_project_category` | `/rest/api/3/projectCategory/{category_id}` | DELETE | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Project Statuses ✅

- **API Type**: platform
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_project_statuses` | `/rest/api/3/project/{project_key}/statuses` | GET | ✅ | - |

### Project Types ✅

- **API Type**: platform
- **Total Methods**: 2
- **Matched to Spec**: 2
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_project_types` | `/rest/api/3/project/type` | GET | ✅ | - |
| `get_project_type` | `/rest/api/3/project/type/{type_key}` | GET | ✅ | - |

### Projects ⚠️

- **API Type**: platform
- **Total Methods**: 12
- **Matched to Spec**: 12
- **Fully Compliant**: 7

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `create_project` | `/rest/api/3/project` | POST | ⚠️ | 1 |
| `get_project` | `/rest/api/3/project/{project_key}` | GET | ✅ | - |
| `get_workflow_scheme_for_project` | `/rest/api/3/workflowscheme/project` | GET | ⚠️ | 1 |
| `assign_workflow_scheme_to_project` | `/rest/api/3/workflowscheme/project/switch` | POST | ⚠️ | 1 |
| `get_notification_scheme_projects` | `/rest/api/3/notificationscheme/project` | GET | ✅ | - |
| `update_project` | `/rest/api/3/project/{project_key}` | PUT | ⚠️ | 1 |
| `search_projects` | `/rest/api/3/project/search` | GET | ✅ | - |
| `archive_project` | `/rest/api/3/project/{project_key}/archive` | POST | ✅ | - |
| `restore_project` | `/rest/api/3/project/{project_key}/restore` | POST | ✅ | - |
| `get_project_categories` | `/rest/api/3/projectCategory` | GET | ✅ | - |
| `get_project_permission_scheme` | `/rest/api/3/project/{project_key_or_id}/permissionscheme` | GET | ✅ | - |
| `assign_permission_scheme_to_project` | `/rest/api/3/project/{project_key_or_id}/permissionscheme` | PUT | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_required_param**: Missing required parameter: projectId
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Screen Schemes ✅

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_screen_schemes` | `/rest/api/3/screenscheme` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `get_screen_scheme()` - GET values
- `get_issue_type_screen_scheme()` - GET values

### Screens ❓

- **API Type**: platform
- **Total Methods**: 7
- **Matched to Spec**: 0
- **Fully Compliant**: 0

#### Unmatched Methods (not found in spec)

- `get_screens()` - GET /rest/api/2/screens
- `get_screen()` - GET id
- `get_screen_tabs()` - GET /rest/api/2/screens/{screen_id}/tabs
- `get_screen_tab_fields()` - GET /rest/api/2/screens/{screen_id}/tabs/{tab_id}/fields
- `add_field_to_screen_tab()` - POST /rest/api/2/screens/{screen_id}/tabs/{tab_id}/fields
- `remove_field_from_screen_tab()` - DELETE /rest/api/2/screens/{screen_id}/tabs/{tab_id}/fields/{field_id}
- `get_screen_available_fields()` - GET /rest/api/2/screens/{screen_id}/availableFields

### Search ✅

- **API Type**: platform
- **Total Methods**: 1
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `search_issues` | `/rest/api/3/search/jql` | GET | ✅ | - |

### Statuses ✅

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_all_statuses` | `/rest/api/3/status` | GET | ✅ | - |
| `get_status` | `/rest/api/3/status/{status_id_or_name}` | GET | ✅ | - |
| `search_statuses` | `/rest/api/3/statuses/search` | GET | ✅ | - |

### Time Tracking ⚠️

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_worklogs` | `/rest/api/3/issue/{issue_key}/worklog` | GET | ✅ | - |
| `get_worklog` | `/rest/api/3/issue/{issue_key}/worklog/{worklog_id}` | GET | ✅ | - |
| `set_time_tracking` | `/rest/api/3/issue/{issue_key}` | PUT | ⚠️ | 1 |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### User Groups ✅

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 1
- **Fully Compliant**: 1

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_user_groups` | `/rest/api/3/user/groups` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `add_user_to_group()` - POST N/A
- `remove_user_from_group()` - DELETE N/A

### Users ⚠️

- **API Type**: platform
- **Total Methods**: 8
- **Matched to Spec**: 6
- **Fully Compliant**: 5

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `search_users` | `/rest/api/3/user/search` | GET | ✅ | - |
| `get_user` | `/rest/api/3/user` | GET | ✅ | - |
| `get_current_user` | `/rest/api/3/myself` | GET | ✅ | - |
| `find_assignable_users` | `/rest/api/3/user/assignable/search` | GET | ✅ | - |
| `get_all_users` | `/rest/api/3/users/search` | GET | ✅ | - |
| `get_users_bulk` | `/rest/api/3/user/bulk` | GET | ⚠️ | 1 |

#### Unmatched Methods (not found in spec)

- `get_current_user_id()` - GET accountId
- `remove_users_from_organization()` - DELETE N/A

#### Issues

- 🔴 **missing_required_param**: Missing required parameter: accountId

### Versions ⚠️

- **API Type**: platform
- **Total Methods**: 6
- **Matched to Spec**: 6
- **Fully Compliant**: 4

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `create_version` | `/rest/api/3/version` | POST | ⚠️ | 1 |
| `get_version` | `/rest/api/3/version/{version_id}` | GET | ✅ | - |
| `update_version` | `/rest/api/3/version/{version_id}` | PUT | ⚠️ | 1 |
| `get_project_versions` | `/rest/api/3/project/{project_key}/versions` | GET | ✅ | - |
| `get_version_issue_counts` | `/rest/api/3/version/{version_id}/relatedIssueCounts` | GET | ✅ | - |
| `get_version_unresolved_count` | `/rest/api/3/version/{version_id}/unresolvedIssueCount` | GET | ✅ | - |

#### Issues

- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one
- 🔴 **missing_request_body**: Spec requires request body but method doesn't accept one

### Workflow Schemes ✅

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 3
- **Fully Compliant**: 3

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_workflow_schemes_for_workflow` | `/rest/api/3/workflow/{workflow_id}/workflowSchemes` | GET | ✅ | - |
| `get_workflow_schemes` | `/rest/api/3/workflowscheme` | GET | ✅ | - |
| `get_workflow_scheme` | `/rest/api/3/workflowscheme/{scheme_id}` | GET | ✅ | - |

### Workflows ✅

- **API Type**: platform
- **Total Methods**: 3
- **Matched to Spec**: 2
- **Fully Compliant**: 2

#### Implemented Methods

| Method | Endpoint | HTTP | Status | Issues |
|--------|----------|------|--------|--------|
| `get_workflows` | `/rest/api/3/workflow` | GET | ✅ | - |
| `search_workflows` | `/rest/api/3/workflow/search` | GET | ✅ | - |

#### Unmatched Methods (not found in spec)

- `get_workflow_bulk()` - POST N/A

## Missing Endpoints (from spec)

These endpoints exist in the OpenAPI spec but are not implemented:

### Platform v3

- `GET, PUT /rest/api/3/announcementBanner - Get announcement banner configuration`
- `POST /rest/api/3/app/field/context/configuration/list - Bulk get custom field configurations`
- `POST /rest/api/3/app/field/value - Update custom fields`
- `GET, PUT /rest/api/3/app/field/{fieldIdOrKey}/context/configuration - Get custom field configurations`
- `PUT /rest/api/3/app/field/{fieldIdOrKey}/value - Update custom field value`
- `GET /rest/api/3/application-properties - Get application property`
- `GET /rest/api/3/application-properties/advanced-settings - Get advanced settings`
- `PUT /rest/api/3/application-properties/{id} - Set application property`
- `GET /rest/api/3/applicationrole - Get all application roles`
- `GET /rest/api/3/applicationrole/{key} - Get application role`
- `GET /rest/api/3/attachment/content/{id} - Get attachment content`
- `GET /rest/api/3/attachment/meta - Get Jira attachment settings`
- `GET /rest/api/3/attachment/thumbnail/{id} - Get attachment thumbnail`
- `GET /rest/api/3/attachment/{id}/expand/human - Get all metadata for an expanded attachment`
- `GET /rest/api/3/attachment/{id}/expand/raw - Get contents metadata for an expanded attachment`
- `GET /rest/api/3/auditing/record - Get audit records`
- `GET /rest/api/3/avatar/{type}/system - Get system avatars by type`
- `POST /rest/api/3/bulk/issues/delete - Bulk delete issues`
- `GET, POST /rest/api/3/bulk/issues/fields - Get bulk editable fields`
- `POST /rest/api/3/bulk/issues/move - Bulk move issues`
- `GET, POST /rest/api/3/bulk/issues/transition - Get available transitions`
- `POST /rest/api/3/bulk/issues/unwatch - Bulk unwatch issues`
- `POST /rest/api/3/bulk/issues/watch - Bulk watch issues`
- `GET /rest/api/3/bulk/queue/{taskId} - Get bulk issue operation progress`
- `POST /rest/api/3/changelog/bulkfetch - Bulk fetch changelogs`
- `GET /rest/api/3/classification-levels - Get all classification levels`
- `POST /rest/api/3/comment/list - Get comments by IDs`
- `GET /rest/api/3/comment/{commentId}/properties - Get comment property keys`
- `DELETE, GET, PUT /rest/api/3/comment/{commentId}/properties/{propertyKey} - Get comment property`
- `GET, POST /rest/api/3/config/fieldschemes - Get field schemes`

... and 289 more endpoints

### Agile

- `POST /rest/agile/1.0/backlog/issue - Move issues to backlog`
- `POST /rest/agile/1.0/backlog/{boardId}/issue - Move issues to backlog for board`
- `GET /rest/agile/1.0/board/filter/{filterId} - Get board by filter id`
- `GET /rest/agile/1.0/board/{boardId}/configuration - Get configuration`
- `GET /rest/agile/1.0/board/{boardId}/epic - Get epics`
- `GET /rest/agile/1.0/board/{boardId}/epic/none/issue - Get issues without epic for board`
- `GET /rest/agile/1.0/board/{boardId}/epic/{epicId}/issue - Get board issues for epic`
- `GET, PUT /rest/agile/1.0/board/{boardId}/features - Get features for board`
- `GET, POST /rest/agile/1.0/board/{boardId}/issue - Get issues for board`
- `GET /rest/agile/1.0/board/{boardId}/project - Get projects`
- `GET /rest/agile/1.0/board/{boardId}/project/full - Get projects full`
- `GET /rest/agile/1.0/board/{boardId}/properties - Get board property keys`
- `DELETE, GET, PUT /rest/agile/1.0/board/{boardId}/properties/{propertyKey} - Get board property`
- `GET /rest/agile/1.0/board/{boardId}/quickfilter - Get all quick filters`
- `GET /rest/agile/1.0/board/{boardId}/quickfilter/{quickFilterId} - Get quick filter`
- `GET /rest/agile/1.0/board/{boardId}/reports - Get reports for board`
- `GET /rest/agile/1.0/board/{boardId}/sprint/{sprintId}/issue - Get board issues for sprint`
- `GET /rest/agile/1.0/board/{boardId}/version - Get all versions`
- `GET, POST /rest/agile/1.0/epic/none/issue - Get issues without epic`
- `GET, POST /rest/agile/1.0/epic/{epicIdOrKey} - Get epic`
- `GET, POST /rest/agile/1.0/epic/{epicIdOrKey}/issue - Get issues for epic`
- `PUT /rest/agile/1.0/epic/{epicIdOrKey}/rank - Rank epics`
- `GET /rest/agile/1.0/issue/{issueIdOrKey} - Get issue`
- `GET, PUT /rest/agile/1.0/issue/{issueIdOrKey}/estimation - Get issue estimation for board`
- `GET /rest/agile/1.0/sprint/{sprintId}/properties - Get properties keys`
- `DELETE, GET, PUT /rest/agile/1.0/sprint/{sprintId}/properties/{propertyKey} - Get property`
- `POST /rest/agile/1.0/sprint/{sprintId}/swap - Swap sprint`
- `POST /rest/devinfo/0.10/bulk - Store development information`
- `GET, DELETE /rest/devinfo/0.10/repository/{repositoryId} - Get repository`
- `DELETE /rest/devinfo/0.10/bulkByProperties - Delete development information by properties`

... and 30 more endpoints

### Service Management

- `GET /rest/servicedeskapi/assets/workspace - Get assets workspaces`
- `POST /rest/servicedeskapi/customer - Create customer`
- `PUT /rest/servicedeskapi/customer/user/{accountId}/revoke-portal-only-access - Revoke portal only access for user`
- `GET /rest/servicedeskapi/info - Get info`
- `GET /rest/servicedeskapi/insight/workspace - Get insight workspaces`
- `GET /rest/servicedeskapi/knowledgebase/article - Get articles`
- `GET /rest/servicedeskapi/organization/{organizationId}/property - Get properties keys`
- `DELETE, GET, PUT /rest/servicedeskapi/organization/{organizationId}/property/{propertyKey} - Get property`
- `GET, POST /rest/servicedeskapi/request/{issueIdOrKey}/attachment - Get attachments for request`
- `GET /rest/servicedeskapi/request/{issueIdOrKey}/attachment/{attachmentId} - Get attachment content`
- `GET /rest/servicedeskapi/request/{issueIdOrKey}/attachment/{attachmentId}/thumbnail - Get attachment thumbnail`
- `GET /rest/servicedeskapi/request/{issueIdOrKey}/comment/{commentId}/attachment - Get comment attachments`
- `DELETE, GET, PUT /rest/servicedeskapi/request/{issueIdOrKey}/notification - Get subscription status`
- `DELETE, GET, POST /rest/servicedeskapi/request/{requestIdOrKey}/feedback - Get feedback`
- `GET /rest/servicedeskapi/requesttype - Get all request types`
- `POST /rest/servicedeskapi/servicedesk/{serviceDeskId}/attachTemporaryFile - Attach temporary file`
- `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/knowledgebase/article - Get articles`
- `POST /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/permissions/check - Check request type permissions`
- `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property - Get properties keys`
- `DELETE, GET, PUT /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttype/{requestTypeId}/property/{propertyKey} - Get property`
- `GET /rest/servicedeskapi/servicedesk/{serviceDeskId}/requesttypegroup - Get request type groups`

## Recommendations

### High Priority

1. Fix 47 critical issues (missing required parameters)
2. Review unmatched methods for potential spec updates
3. Consider implementing high-value missing endpoints

### Future Enhancements

- Add response schema validation
- Implement deprecation warnings for deprecated endpoints
- Add type hints that match spec schemas
