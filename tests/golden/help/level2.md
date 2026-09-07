# getIssue

GET `/rest/api/3/issue/{issueIdOrKey}`

Get issue

Returns the details for an issue.

## Parameters

- `--issue-id-or-key` (path, string) (required)
- `--fields` (query, array)
- `--fields-by-keys` (query, boolean)
- `--expand` (query, string)
- `--properties` (query, array)
- `--update-history` (query, boolean)
- `--fail-fast` (query, boolean)

## Body

No top-level body properties.

## Behavior

- Risk: safe.
- scope: {'in': 'key', 'name': 'issueIdOrKey', 'separator': '-'}
- x-atlassian-connect-scope: "READ"
- x-atlassian-oauth2-scopes: [{"scheme": "OAuth2", "scopes": ["read:jira-work"], "state": "Current"}, {"scheme": "OAuth2", "scopes": ["read:issue-meta:jira", "read:issue-security-level:jira", "read:issue.vote:jira", "read:issue.changelog:jira", "read:avatar:jira", "read:issue:jira", "read:status:jira", "read:user:jira", "read:field-configuration:jira"], "state": "Beta"}]
- Use --full for the complete description; --examples for examples.
