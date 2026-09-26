# Project scope

In 2.x, project scope is enforced by the engine's scope guard. Every operation
in the platform, Software and Service Management indexes carries an `x-as-scope`
tag, shown by `api describe`, and the Generic Surface checks it before any
transport send. The guard covers `jira-as api call`, `jira-as workflows run`,
the compatibility verbs that delegate to the Generic Surface, and the
`jira-as serve` sidecar.

The guard is on by default and does not depend on an allowlist. With nothing
configured it still refuses JQL that names no project or joins clauses with OR,
and refusals then report `allowlist=null`. The project allowlist only narrows
which projects pass. A trusted human can select the
[interactive profile](#interactive-profile) for one direct CLI invocation.

Surviving legacy verbs that still use the hand-written `JiraClient` are outside
the engine guard. They keep an older argv pre-check, described under
[legacy verbs](#legacy-verbs).

## Configuration

Settings live under `jira` in `.claude/settings.json` (team defaults) or
`.claude/settings.local.json` (local overrides). Environment variables take
precedence over both:

```json
{
  "jira": {
    "allowed_projects": ["DEMO", "SBX"],
    "allow_site_operations": false,
    "scope_enforcement": "enforcing"
  }
}
```

| Setting | Environment override | Default | Meaning |
| --- | --- | --- | --- |
| `allowed_projects` | `JIRA_ALLOWED_PROJECTS=DEMO,SBX` | absent | Projects a scoped call may touch. |
| `allow_site_operations` | `JIRA_ALLOW_SITE_OPERATIONS=true\|false` | `false` | Whether site-level operations may run. |
| `scope_enforcement` | `JIRA_SCOPE_ENFORCEMENT=enforcing\|permissive` | `enforcing` | Whether the guard runs at all. |

`ConfigManager` searches upward from the current directory for the nearest
`.claude` directory. It loads `settings.json`, then `settings.local.json`; a
local value replaces the team value. Its loader silently ignores malformed
settings JSON files. Policy is read once, at the first call of
a command. Discovery and help never read settings or credentials, and none of
these settings retrieves credentials. Restart a long-running process after
editing them.

Allowlist keys are trimmed, uppercased and deduplicated. Each must start with a
letter and contain only letters, digits or underscores; use project **keys**,
not display names or numeric IDs. The setting does not check that a project
exists. A malformed list, including JSON `null`, raises a validation error
naming `jira.allowed_projects`; empty entries in a nonempty comma-separated
environment value are invalid too.

An absent allowlist removes project-membership restrictions but keeps every
structural check below. An explicit `[]`, or an empty or whitespace-only
`JIRA_ALLOWED_PROJECTS`, allows no scoped operation. Invalid site-policy or
scope-enforcement values are usage errors (exit 2) and nothing is sent.

```sh
JIRA_ALLOWED_PROJECTS=SBX jira-as api --transport responder call getIssue --issueIdOrKey SBX-1
JIRA_ALLOWED_PROJECTS=SBX jira-as api --transport responder call createIssue --project SBX --field fields.project.key=SBX --field fields.summary=x --field fields.issuetype.name=Task
```

## What the guard checks

Body-only identity requires `--project KEY`, including `--body @file` and JQL
bodies. It must match the body's key or id; multiple present key/id alternatives
must agree. The flag is also accepted on keyed/path/query calls and must agree
with their identity. All members of project or issue-key arrays are checked.
Numeric-only issue IDs cannot establish a project; numeric project IDs cannot
prove membership in this key-only allowlist, and there is no implicit resolver.
Key/id spellings compare exactly; configured project keys are uppercased.

JQL is checked with a deliberately small grammar rather than a general parser:

- Every query must contain a complete `project = KEY` or `project IN (KEY, ...)`
  restriction, even with no allowlist.
- Other predicates may be added only with AND, using literal values:
  `project = SBX AND statusCategory = Done`.
- One trailing `ORDER BY key|created|updated [ASC|DESC]` is accepted on
  `searchAndReconsileIssuesUsingJql` and its POST twin:
  `project = SBX ORDER BY updated DESC`.
- OR, NOT, functions such as `currentUser()`, saved filters, boolean grouping,
  other ordering and malformed syntax refuse. So does
  `assignee = currentUser()`, which also names no project.
- JQL bodies additionally require the matching `--project` flag.

Numeric board, sprint, desk and organization routes are site-level until a
project resolver is designed. Site metadata and ambiguous nested/bulk bodies
also require explicit site permission; `--project SBX` alone does not prove a
board's or desk's project membership. Bulk nested issueUpdates extraction is
deferred. For keyed editIssue/doTransition calls, an optional body project must
agree with the issue key, preventing a file body from silently changing scope.

For `api call` and `workflows run`, local scope refusals exit 4 and emit the
Generic Surface JSON error object on stderr: `status` is null, `messages`
explain the identity/allowlist refusal, `operation` identifies the call and
`note` preserves its enrichment note. Compatibility verbs that delegate to
the Generic Surface translate these errors to their legacy exit code 1.
No requested operation is sent on refusal. `jira-as api call` has no flag that
skips the guard. The development host wrapper still owns the external boundary
and can refuse shapes outside its own argv grammar. The replayable forty-shape
fixture records explicit site opt-ins separately.

## Permissive mode

The underlying scope switch remains available for existing direct clients and
settings. For a human using the CLI, prefer the explicit interactive profile
below because it scopes the choice to one invocation.

A trusted interactive user whose Atlassian token already carries the needed
permissions can switch the guard off:

```sh
JIRA_SCOPE_ENFORCEMENT=permissive jira-as api call searchAndReconsileIssuesUsingJql \
  --jql 'assignee = currentUser() ORDER BY updated DESC'
```

or set `"scope_enforcement": "permissive"` under `jira`. The environment value
is trimmed and case-insensitive; the setting must be exactly `"enforcing"` or
`"permissive"`, and the environment overrides the setting in both directions.

In permissive mode the Generic Surface skips `x-as-scope` entirely: no JQL
grammar, project identity, site gate, `--project` agreement or scope-resolution
read. Parameter and body validation, risk confirmation and every other
transform still apply. Jira checks the token's permissions for requests that
reach the API.

- The mode is never silent on a Generic Surface. Before its first permissive
  send, stderr receives `Warning: scope enforcement is permissive ...` once
  per Surface.
- On Generic Surface paths, it cannot be combined with a project allowlist.
  If `allowed_projects` or `JIRA_ALLOWED_PROJECTS` is present, even empty,
  the call is a usage error (exit 2 for `api call` and `workflows run`; legacy
  exit 1 for compatibility verbs) and nothing is sent. Remove the allowlist,
  or run from a directory whose settings do not set one.
- It requires an as-engine release with `scope_enforcement` support. An older
  engine is a usage error rather than a mode that claims to be permissive
  while it keeps enforcing.
- `jira-as serve` never reads the setting and always enforces, and the engine
  forces enforcement on every served call. A permissive socket-transport client
  therefore skips only its local check; the sidecar still refuses.
- The workflow MCP adapter pins `JIRA_SCOPE_ENFORCEMENT=enforcing` for the
  commands it launches.
- Do not use it in a sandbox or agent seat. The default exists so that an
  automated run gets a narrow, auditable surface.

## Interactive profile

For a trusted human using the CLI directly outside a sandbox, put the profile
before the command:

```sh
jira-as --profile interactive api call searchAndReconsileIssuesUsingJql \
  --jql 'assignee = currentUser() ORDER BY updated DESC'
jira-as --profile interactive workflows run list-projects
jira-as --profile interactive issue get EX-1
```

The profile applies only to that process. It skips local project, JQL and site
scope checks, including the older argv scan on surviving legacy commands. It
also ignores scope settings in the nearest workspace `.claude/settings.json`
and `.claude/settings.local.json`. Jira still applies the caller's token
permissions. Input and body validation, risk previews and `--confirm` remain
in effect. A Generic Surface warns once before its first permissive send.

An exported policy signals an automation boundary. The profile refuses an
exported `JIRA_ALLOWED_PROJECTS` even when empty, and refuses
`JIRA_SCOPE_ENFORCEMENT=enforcing` or `JIRA_ALLOW_SITE_OPERATIONS=false`.
Unset those variables only in a trusted human shell, outside the sandbox.
Malformed environment values are usage errors. A classic personal API token
uses the normal `JIRA_SITE_URL` for its Jira Cloud site; the profile does not
change authentication or grant any Jira permission.

The profile is unavailable for `serve` and socket transport. The workflow MCP
adapter continues to pin enforcing scope for its commands. The profile is a
direct CLI choice, not a server or agent setting.

## Legacy verbs

Before any metadata or transport access, surviving legacy verbs run a
literal-reference scan. The shared CLI helper (`get_client_from_context`)
scans all of the invoking command's `ctx.params`; the compatibility client
helper (`compat.client.get_client`) scans only `issue_key`, `project`,
`source_issue`, `target_issue`, `target` and `jql`. Both scan only when an
allowlist is configured; with no allowlist they permit everything. Refusal
raises `ValidationError` naming the offending project and
`jira.allowed_projects`, and the CLI exits 1:

```bash
JIRA_MOCK_MODE=true JIRA_ALLOWED_PROJECTS=DEMO jira-as issue get OTHER-1
# Error includes: Project 'OTHER' is not permitted by jira.allowed_projects
```

The scan checks:

- Issue keys such as `DEMO-85` in every string, including nested lists, tuples
  and mapping values, URLs, prose, comma-separated lists and repeated options.
- Parameters that name projects (`project`, `projects`, `project_key`,
  `project_id`, `to_project`, `target_project` and similar), including
  comma-separated values.
- Literal JQL `project` operands for `=`, `!=`, `~`, `!~`, `IN`, `NOT IN`, `WAS`
  and `WAS NOT` forms, in every branch, including negative and historical ones.
- Numeric project references, which are refused because they cannot be
  resolved to keys.

It is not a JQL parser or an authorization system. `project != DEMO` and
`project = DEMO OR status = Open` can return other projects. Saved filters,
JQL functions and projects inferred from boards, sprints, service desks, issue
IDs or responses are not bounded. It can also refuse issue-key-like prose such
as `UTF-8`. It does not read file or stdin contents, parse JSON strings for
project objects, inspect parent Click contexts, or inspect values generated
after the helper call. Default projects resolved later are outside the scan.

Verbs that call `get_jira_client()` directly (including every `jsm` command)
bypass the scan, and neither the scan nor the engine guard intercepts
programmatic `get_jira_client()`, `ConfigManager.get_client()` or direct
`JiraClient` use. Prefer `jira-as api call`, which the engine guard covers.
Permissive mode does not change this scan. Hand-written `JiraClient` verbs
can run with both permissive mode and an allowlist configured; their legacy
scan still enforces literal references. Generic Surface paths refuse that
combination as described above.
