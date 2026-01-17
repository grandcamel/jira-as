# Gap Analysis: jira-assistant-skills-lib vs Atlassian ACLI

**Date:** 2026-01-17
**Reference:** https://developer.atlassian.com/cloud/acli/reference/commands/#acli

## Executive Summary

| Metric | Atlassian ACLI | jira-assistant-skills-lib |
|--------|----------------|---------------------------|
| Total JIRA Commands | ~41 | **165+** |
| Command Categories | 8 | **13** |
| Coverage Status | Baseline | **Superset** |

**Key Finding:** This library is a **superset** of ACLI functionality with approximately 4x more commands. However, there are **5 specific gaps** where ACLI has capabilities this library lacks.

---

## Gaps: ACLI Features Missing from This Library

### Summary Table

| # | ACLI Command | Description | Priority | Effort |
|---|--------------|-------------|----------|--------|
| 1 | `jira workitem archive` | Archive/soft-delete issues | Medium | Low |
| 2 | `jira workitem unarchive` | Restore archived issues | Medium | Low |
| 3 | `jira dashboard search` | Search dashboards | Low | Low |
| 4 | `jira field delete` | Delete custom fields | Medium | Low |
| 5 | `jira field cancel-delete` | Cancel pending field deletion | Low | Low |
| 6 | `jira filter change-owner` | Transfer filter ownership | Low | Low |

### Detailed Gap Analysis

#### 1. Issue Archive/Unarchive

**ACLI Commands:**
- `jira workitem archive` - Soft-delete issues without permanent removal
- `jira workitem unarchive` - Restore previously archived issues

**Current State:**
- Library has `archive_project()` and `restore_project()` in `jira_client.py:5317-5357`
- No equivalent methods for individual issues

**REST API Endpoints:**
```
PUT  /rest/api/3/issue/{issueIdOrKey}/archive
PUT  /rest/api/3/issue/{issueIdOrKey}/unarchive
POST /rest/api/3/issue/archive  (bulk archive)
```

**Note:** Issue archiving is a JIRA Premium feature.

**Implementation Required:**
- Add `archive_issue()` method to `JiraClient`
- Add `unarchive_issue()` method to `JiraClient`
- Add `jira-as issue archive ISSUE-KEY` CLI command
- Add `jira-as issue unarchive ISSUE-KEY` CLI command
- Add mock implementations in `mock/base.py`

---

#### 2. Dashboard Operations

**ACLI Commands:**
- `jira dashboard search` - Find dashboards by criteria

**Current State:**
- Library has zero dashboard functionality
- No `dashboard` command group in CLI

**REST API Endpoints:**
```
GET /rest/api/3/dashboard/search
GET /rest/api/3/dashboard/{dashboardId}
GET /rest/api/3/dashboard/{dashboardId}/gadget
```

**Implementation Required:**
- Add dashboard methods to `JiraClient`:
  - `search_dashboards()`
  - `get_dashboard()`
  - `get_dashboard_gadgets()`
- Add `jira-as dashboard` command group
- Add mock implementations

---

#### 3. Field Delete Operations

**ACLI Commands:**
- `jira field delete` - Delete custom fields
- `jira field cancel-delete` - Cancel a pending field deletion

**Current State:**
- Library has `delete_field_option()` for deleting field options (mock/mixins/fields.py:736)
- No top-level field delete capability

**REST API Endpoints:**
```
DELETE /rest/api/3/field/{fieldId}
POST   /rest/api/3/field/{fieldId}/restore
```

**Implementation Required:**
- Add `delete_field()` method to `JiraClient`
- Add `cancel_delete_field()` method to `JiraClient`
- Add `jira-as fields delete FIELD-ID` CLI command
- Add `jira-as fields cancel-delete FIELD-ID` CLI command
- Add mock implementations

---

#### 4. Filter Change-Owner

**ACLI Commands:**
- `jira filter change-owner` - Transfer filter ownership to another user

**Current State:**
- Library has comprehensive filter operations:
  - `create_filter()`, `get_filter()`, `update_filter()`, `delete_filter()`
  - `add_filter_favourite()`, `remove_filter_favourite()`
  - `get_filter_permissions()`, `add_filter_permission()`, `delete_filter_permission()`
- Missing: ownership transfer capability

**REST API Endpoint:**
```
PUT /rest/api/3/filter/{id}/owner
```

**Implementation Required:**
- Add `change_filter_owner()` method to `JiraClient`
- Add `jira-as search filter change-owner FILTER-ID --to USER` CLI command
- Add mock implementation

---

## Feature Parity Matrix

| ACLI Category | ACLI Commands | Library Status | Notes |
|---------------|---------------|----------------|-------|
| **auth** | login, logout, status, switch | ✅ Equivalent | Via env vars, keychain, config files |
| **board** | list-sprints, search | ✅ Superset | + backlog, velocity, ranking |
| **dashboard** | search | ❌ **Missing** | No dashboard support |
| **field** | create, delete, cancel-delete | ⚠️ Partial | Has create, missing delete operations |
| **filter** | list, search, add-favourite, change-owner | ⚠️ Partial | Missing change-owner only |
| **project** | create, list, view, update, archive, delete, restore | ✅ Superset | + categories, avatars, components |
| **sprint** | list-workitems | ✅ Superset | + create, start, close, update |
| **workitem** | 19 operations | ⚠️ Partial | Missing archive/unarchive |

---

## Library Capabilities Beyond ACLI

This library provides extensive functionality not available in ACLI:

### Jira Service Management (JSM)
- Service desk management (list, get, create)
- Request types and fields
- Request lifecycle (create, transition, comments)
- Customer and organization management
- Queue management
- SLA tracking and reporting
- Approval workflows
- Knowledge base integration
- Asset management

### Advanced Agile
- Epic management (create, get, link issues)
- Sprint lifecycle (create, start, close, update)
- Backlog management (rank, move to sprint/backlog)
- Story point estimation
- Velocity calculation
- Board configuration

### Time Tracking
- Worklog CRUD operations
- Time estimates (original/remaining)
- Time tracking reports
- Bulk time logging
- Timesheet export

### Automation
- List and search automation rules
- Get rule details and templates
- Enable/disable rules
- Invoke manual rules
- Access automation templates

### Bulk Operations
- Bulk transitions (50+ issues)
- Bulk assignments
- Bulk priority changes
- Bulk cloning
- Bulk linking
- Bulk deletion
- Dry-run support with rollback safety

### Issue Relationships
- Link management (create, delete, list)
- Dependency analysis (blockers, blocked-by)
- Link type management
- Issue cloning with relationships
- Bulk linking operations

### Workflow Management
- List and search workflows
- Get workflow details
- Workflow scheme management
- Status management
- Transition helpers with fuzzy matching

### Permission & Notification Schemes
- Permission scheme CRUD
- Grant management
- Notification scheme CRUD
- Event handler configuration

### User & Group Management
- User search and lookup
- Group CRUD operations
- Membership management
- User resolution to account IDs

### Development Integration
- Generate branch names from issues
- Parse commit messages for issue keys
- Generate PR descriptions
- Link commits and PRs to issues

### Project Administration
- Project categories
- Project avatars
- Component management
- Version management
- Issue type schemes
- Screen configuration

### Search & Filtering
- JQL validation and suggestions
- JQL function reference
- Advanced field autocomplete
- Export to JSON/CSV
- Saved filter management

### Operations & Performance
- SQLite-based caching with TTL
- Request batching for concurrent API calls
- Project context discovery
- Checkpoint support for large operations

---

## Command Count Comparison

| Category | ACLI | This Library |
|----------|------|--------------|
| Authentication | 4 | 3 (env/keychain/config) |
| Board/Agile | 3 | 25+ |
| Dashboard | 1 | 0 |
| Field | 3 | 15+ |
| Filter | 4 | 12+ |
| Project | 7 | 20+ |
| Sprint | 1 | 10+ |
| Issue/WorkItem | 19 | 30+ |
| Comments | (in workitem) | 8+ |
| Attachments | (in workitem) | 6+ |
| JSM | 0 | 40+ |
| Time Tracking | 0 | 15+ |
| Relationships | 0 | 15+ |
| Automation | 0 | 10+ |
| Bulk Operations | 0 | 10+ |
| Users/Groups | 0 | 10+ |
| Workflows | 0 | 10+ |
| Permissions | 0 | 15+ |
| **Total** | **~41** | **165+** |

---

## Recommendations

### High Priority
1. **Add issue archive/unarchive** - Common operation for issue lifecycle management
2. **Add field delete operations** - Complete field management capability

### Medium Priority
3. **Add dashboard search** - Useful for dashboard discovery
4. **Add filter change-owner** - Complete filter management

### Low Priority
5. Consider adding more dashboard operations (gadgets, configuration) if user demand exists

---

## Implementation Checklist

### Issue Archive/Unarchive
- [ ] Add `archive_issue(issue_key: str)` to `JiraClient`
- [ ] Add `unarchive_issue(issue_key: str)` to `JiraClient`
- [ ] Add `archive_issues_bulk(issue_keys: list)` to `JiraClient`
- [ ] Add CLI commands to `issue_cmds.py`
- [ ] Add mock implementations to `mock/base.py`
- [ ] Add unit tests

### Dashboard Operations
- [ ] Add `search_dashboards()` to `JiraClient`
- [ ] Add `get_dashboard(dashboard_id: str)` to `JiraClient`
- [ ] Create `dashboard_cmds.py` CLI module
- [ ] Add mock implementations
- [ ] Add unit tests

### Field Delete Operations
- [ ] Add `delete_field(field_id: str)` to `JiraClient`
- [ ] Add `cancel_delete_field(field_id: str)` to `JiraClient`
- [ ] Add CLI commands to `fields_cmds.py`
- [ ] Add mock implementations to `mock/mixins/fields.py`
- [ ] Add unit tests

### Filter Change-Owner
- [ ] Add `change_filter_owner(filter_id: str, account_id: str)` to `JiraClient`
- [ ] Add CLI command to `search_cmds.py`
- [ ] Add mock implementation to `mock/mixins/search.py`
- [ ] Add unit tests

---

## Appendix: ACLI JIRA Commands Reference

```
jira auth login
jira auth logout
jira auth status
jira auth switch

jira board list-sprints
jira board search

jira dashboard search

jira field create
jira field delete
jira field cancel-delete

jira filter add-favourite
jira filter change-owner
jira filter list
jira filter search

jira project archive
jira project create
jira project delete
jira project list
jira project restore
jira project update
jira project view

jira sprint list-workitems

jira workitem archive
jira workitem assign
jira workitem attachment-delete
jira workitem attachment-list
jira workitem clone
jira workitem comment-create
jira workitem comment-delete
jira workitem comment-list
jira workitem comment-update
jira workitem comment-visibility
jira workitem create
jira workitem create-bulk
jira workitem delete
jira workitem edit
jira workitem link
jira workitem search
jira workitem transition
jira workitem unarchive
jira workitem view
jira workitem watcher-remove
```
