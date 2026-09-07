# search

## MigrationResource.workflowRuleSearch_post

Get workflow transition rule configurations

## search

Search statuses paginated

## searchAndReconsileIssuesUsingJql

Use /rest/api/3/search/jql and nextPageToken for issue search. A 429 is a rate limit: honor Retry-After and returned rate-limit headers; do not assume a universal requests-per-minute quota. --all follows the declared continuation and --limit caps collected issues.

```sh
jira-as api call searchAndReconsileIssuesUsingJql --jql 'project = SBX' --maxResults 25 --all --limit 50
```

## searchAndReconsileIssuesUsingJqlPost

Use /rest/api/3/search/jql and nextPageToken for issue search. A 429 is a rate limit: honor Retry-After and returned rate-limit headers; do not assume a universal requests-per-minute quota. --all follows the declared continuation and --limit caps collected issues.

```sh
jira-as api call searchAndReconsileIssuesUsingJqlPost --field 'jql=project = SBX' --field maxResults=25 --all --limit 50
```

## searchFieldAssociationSchemeFields

Search field scheme fields

## searchFieldAssociationSchemeProjects

Search field scheme projects

## searchForIssuesUsingJql

This removed /search operation is replaced by searchAndReconsileIssuesUsingJql at /rest/api/3/search/jql (CHANGE-2046). The replacement pages with nextPageToken, not startAt. The literal operationId search belongs to status discovery; use the full issue-search operationId.

## searchForIssuesUsingJqlPost

This removed /search operation is replaced by searchAndReconsileIssuesUsingJqlPost at /rest/api/3/search/jql (CHANGE-2046). The replacement pages with nextPageToken, not startAt. The literal operationId search belongs to status discovery; use the full issue-search operationId.

## searchPriorities

Search priorities

## searchProjects

Get projects paginated

## searchProjectsUsingSecuritySchemes

Get projects using issue security schemes

## searchResolutions

Search resolutions

## searchSecuritySchemes

Search issue security schemes

## searchWorkflows

Search workflows
