# Project allowlist

`jira.allowed_projects` is an optional defence-in-depth check for projects
explicitly named in CLI commands that use `get_client_from_context`.
The organization's boundary is its wrappers.

## Configuration

Add the setting to `.claude/settings.json` (team defaults) or
`.claude/settings.local.json` (local overrides):

```json
{
  "jira": {
    "allowed_projects": ["DEMO", "SBX"]
  }
}
```

`ConfigManager` searches upward from the current directory for the nearest
`.claude` directory. It loads `settings.json`, then `settings.local.json`;
a local list replaces the team list. Settings use the existing process-wide
configuration singleton, so restart a long-running process after editing them.

The optional environment variable overrides the list:

```bash
JIRA_ALLOWED_PROJECTS=DEMO,SBX jira-as issue get DEMO-85
```

Keys are trimmed, normalized to uppercase and deduplicated. Each must start
with a letter and contain only letters, digits or underscores. This setting
does not validate that a project exists; use project **keys**, not display
names or numeric IDs. A malformed list, including JSON `null`, raises a
validation error naming `jira.allowed_projects`. Empty entries in a nonempty
comma-separated environment value are also invalid.

When the setting and environment override are both absent, there is no
restriction. An explicit `[]` or empty/whitespace-only environment override
permits no **named** project references. It does not prohibit operations
that have no visible project reference. This preserves the difference
between an absent setting and an intentionally empty list.

## What is checked

The check runs on each call to the shared CLI client helper, before creating
or returning a cached client. It scans the invoking command's `ctx.params`:

- Every string, including strings nested in lists, tuples and mapping values,
  is scanned for issue keys such as `DEMO-85`, including keys in URLs or prose.
  Matching is case-insensitive, accepts single-letter and long project prefixes,
  and also covers comma-separated issue lists and repeated Click options.
- Parameters named `project`, `projects`, `project_key`, `project_keys`,
  `project_id`, `project_ids`, `project_key_or_id`, `to_project`,
  `target_project`, `source_project`, `share_project`, `project_filter` and
  `project_key_filter` are checked as project references, including
  comma-separated values. `key_or_project` accepts either an issue key or a
  project key. The `key` parameter when accompanied by `project_type` covers
  `admin project create --key`. Project type, template and description values
  are not treated as project names.
- Literal JQL `project` operands are extracted from strings: `=`, `!=`, `~`,
  `!~`, `IN`, `NOT IN`, `WAS`, `WAS NOT`, `WAS IN` and `WAS NOT IN`.
  Quoted field names, quoted values, escaped characters and parenthesized
  lists are supported. Every named operand must be allowed, including ones
  mentioned in negative or historical clauses and separate `OR` branches.
- Numeric project references in these fields are refused because the check
  cannot resolve IDs to keys. Numeric issue IDs are not recognizable as
  issue keys and are outside this check.

Refusal raises the existing `ValidationError` and names both the offending
project and `jira.allowed_projects`; the normal CLI error handling exits 1.
For example, this works offline and is refused before even a mock client exists:

```bash
JIRA_MOCK_MODE=true JIRA_ALLOWED_PROJECTS=DEMO jira-as issue get OTHER-1
# Error includes: Project 'OTHER' is not permitted by jira.allowed_projects
```

## Coverage and limits

This is a literal-reference scan, not a JQL parser or authorization system.
For example, `project != DEMO` and `project = DEMO OR status = Open` can
return other projects, even though the only named project is allowed.
Unconstrained queries, saved filters, functions that determine projects,
and projects inferred from boards, sprints, service desks, issue IDs or server
responses are not resolved or bounded. Use the wrappers for that boundary.

The scan can refuse issue-key-like prose such as `UTF-8`, even in a summary
or filename, and project-clause-like text inside a quoted JQL text search.
It does not read file/stdin contents, parse JSON strings for project objects,
inspect parent Click contexts, inspect values generated after the helper call,
or constrain raw HTTP requests. Default projects resolved later are similarly
outside the scan. Existing ConfigManager behavior for malformed JSON settings
files is unchanged: its loader ignores them. The allowlist does not harden
that loader or prevent a caller from changing configuration.

At this revision the shared helper has 151 call sites across 12 of the 13
command groups. Counts below are actual calls, excluding imports; direct
factory counts include optional-client helper fallbacks.

| Command module | Shared helper calls | Direct `get_jira_client()` sites |
| --- | ---: | ---: |
| admin | 56 | 55 |
| agile | 15 | 20 |
| bulk | 5 | 5 |
| collaborate | 11 | 14 |
| dev | 5 | 5 |
| fields | 4 | 4 |
| issue | 7 | 5 |
| jsm | 0 | 46 |
| lifecycle | 13 | 13 |
| ops | 2 | 2 |
| relationships | 9 | 11 |
| search | 15 | 15 |
| time | 9 | 9 |

Most direct factories are private helpers called with the shared client by
guarded commands. Calling these helpers without that client bypasses the
check. All `jsm` commands bypass the shared helper. Admin `automation`
(`list`, `get`, `search`, `enable`, `disable`, `toggle`, `invoke`) and
`automation-template` (`list`, `get`) use `get_automation_client` and also
bypass it. `search build` only obtains a client when validation is requested;
without validation it constructs JQL locally. Other local-only operations
need not obtain a client either.

Programmatic `get_jira_client()`, `ConfigManager.get_client()`,
`get_automation_client()` and direct `JiraClient` use are not intercepted.
Mock mode follows the same shared-helper check and the same bypasses.
This setting is an additional check against accidental references; its
presence does not make direct clients or unguarded commands safe to use
outside the organization's wrappers.

## Generic Surface project scope (2.0)

Every operation in the platform, Software and Service Management indexes has an
`x-as-scope` tag, shown by `api describe`. The Generic Surface checks it before
any transport send. It reuses `jira.allowed_projects` and
`JIRA_ALLOWED_PROJECTS`, loading policy once at the first call. Discovery and
help do not read settings or credentials. The legacy checks described above
remain in place for legacy verbs.

An absent allowlist removes project-membership restrictions; an explicit empty
list allows no scoped operation. Identity structure and body/argv agreement
still apply in unrestricted mode. Site-level operations independently require
`jira.allow_site_operations: true` (a boolean, default false), overridden by
`JIRA_ALLOW_SITE_OPERATIONS=true|false`. Invalid site-policy values are usage
errors. These settings do not retrieve credentials.

```sh
JIRA_ALLOWED_PROJECTS=SBX jira-as api --transport responder call getIssue --issueIdOrKey SBX-1
JIRA_ALLOWED_PROJECTS=SBX jira-as api --transport responder call createIssue --project SBX --field fields.project.key=SBX --field fields.summary=x --field fields.issuetype.name=Task
```

Body-only identity requires `--project KEY`, including `--body @file` and JQL
bodies. It must match the body's key or id; multiple present key/id alternatives
must agree. The flag is also accepted on keyed/path/query calls and must agree
with their identity. All members of project or issue-key arrays are checked.
Numeric-only issue IDs cannot establish a project; numeric project IDs cannot
prove membership in this key-only allowlist, and there is no implicit resolver.
Key/id spellings compare exactly; configured project keys are uppercased.

JQL calls require a complete `project = SBX` or `project IN (SBX)` restriction.
They accept additional literal AND predicates, for example
`project = SBX AND status = Open`. OR, NOT, saved filters, functions, ORDER BY,
boolean grouping, malformed syntax, and missing project restrictions refuse.
This is deliberately a small grammar rather than general JQL parsing. JQL
bodies additionally require the matching `--project` flag.

Numeric board, sprint, desk and organization routes are site-level until a
project resolver is designed. Site metadata and ambiguous nested/bulk bodies
also require explicit site permission; `--project SBX` alone does not prove a
board's or desk's project membership. Bulk nested issueUpdates extraction is
deferred. For keyed editIssue/doTransition calls, an optional body project must
agree with the issue key, preventing a file body from silently changing scope.

Local scope refusals exit 4 and emit the Generic Surface JSON error object on
stderr: `status` is null, `messages` explain the identity/allowlist refusal,
`operation` identifies the call and `note` preserves its enrichment note.
No requested operation is sent on refusal. The development host wrapper still
owns the external boundary and can refuse shapes outside its own argv grammar.
The replayable forty-shape fixture records explicit site opt-ins separately.
