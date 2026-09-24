# Discover and read visible Jira projects

The product-owned catalog currently supports one agent task, `list-projects`.
It reads one bounded page through the existing indexed `searchProjects` GET and
current operator scope. These are agent tasks, distinct from Jira issue status
workflows. Broader operation discovery remains available through `api`.

```sh
jira-as --help
jira-as workflows list
jira-as workflows search "What Jira projects can I see?" --format json
jira-as workflows describe list-projects
jira-as workflows describe list-projects --examples
jira-as workflows run list-projects --format json
```

For user tasks, first check supported workflows. Root `--help` places this
guidance before the catalog hint: search your request, then describe a matching
workflow ID for its run command. A match is not guaranteed for every task;
broader operation discovery remains available through `api`. The default
description includes its first authored run invocation as a `{kind,value}` entry
under `examples`, ready to pass to the CLI. `--examples` returns all authored
examples; it is not required before running.

List, search and describe require no credentials, configuration, Surface or
transport. They report declared support and `availability=unknown`; discovery
does not establish account access. Search accepts a quoted ordinary question,
returns explicit empty matches for unrelated words, and bounds queries to 512
characters. Both list and search accept `--offset` for catalog pagination.
Escaped queries must also fit the 800-token output proxy; an oversized query
returns `needs-input`, reason `query-output-too-large`, and `shorten-query`.
The query is neither echoed nor silently truncated in that refusal.

The human default is Markdown containing a JSON data block. `--format json`
returns the same values directly. Root `--output json` selects JSON unless a
workflow `--format` overrides it; root text/table select Markdown. An exit-zero
result is the sole stdout output. A nonzero result is the sole stderr output,
with no success stdout. Parser failures within the four commands are structured
too, including missing values, invalid types and duplicate scalar options.

## Inputs and current authority

Run accepts only `--limit` (integer, default 25, range 1–100) and `--offset`
(integer, default 0, range 0–9223372036854775807), plus the output format.
Duplicate values are rejected even when equal. Inputs cannot select a transport,
site, policy, executable, credentials, arbitrary operation, request body or an
automatic all-pages loop. The existing operator configuration remains authoritative.

Each invocation creates a fresh product Surface and calls its real indexed,
validated and guarded path. The binding fixes `orderBy=key` and `action=view`,
maps offset to `startAt` and limit to `maxResults`, and sends no body. One logical
read may have multiple wire attempts under the existing transport retry policy.

This operation has site scope. In enforcing mode, a project allowlist alone
does not grant site permission; permissive mode skips the scope check.
Discovering the task never changes `JIRA_ALLOW_SITE_OPERATIONS`.
Configuration and scope are checked at execution; credential resolution stays
inside the existing product factory. Missing credentials are blocked before HTTP
construction. The adapter preserves local credential-validation errors as exit 2,
without including exception text or changing other commands' error semantics.

## Reading a result and continuing

Results identify the product/version, engine version, schema and required runtime
capability, catalog/workflow revisions and the SHA-256 of installed definition
bytes. A run includes normalized inputs and bounds, compact items, returned count,
limit/offset, range, completeness, evidence, a reason and safe next actions.
There is no write-verification claim or run receipt in this read slice.

Items preserve exact IDs, keys and names; equal names remain separate identities.
`url` is a canonical provider `self` link only when it is valid HTTPS, has no
userinfo/query/fragment/control characters, and identifies the returned ID or key
at `/rest/api/3/project/{identity}`. Otherwise the URL and its source are null.
A project's documentation `url` is not substituted. Provider text is escaped as
data in human output, and links are never followed to choose execution or paging.

`complete` answers whether another page follows the returned range. It does not
claim that earlier offsets were fetched. For example, a server-reduced first
page returning two items for limit 25 can report:

```json
{"complete":false,"continuation":{"workflow":"list-projects","inputs":{"limit":25,"offset":2}}}
```

The next explicit call uses those bounded inputs:

```sh
jira-as workflows run list-projects --limit 25 --offset 2 --format json
```

Continuation advances by the actual received count, retains the requested limit
and never consumes a provider `nextPage` URL. Consistent total/isLast evidence can
establish completion; an empty page is final only with positive final evidence.
Missing completion signals leave `complete=null`. Missing offset evidence prevents
automatic continuation. Contradictory metadata, overflow, invalid identities,
duplicate IDs/keys or empty nonfinal pages yield `unknown` with no continuation.
Bounded usable items may remain, with explicit received/omitted counts in evidence.
Only an offset-zero-to-final traversal covers the fixture's full result set;
separate real reads are not a transactional snapshot of a changing Jira site.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | completed-read | Read/discovery succeeded; inspect completeness independently. |
| 2 | needs-input | Unsupported workflow, invalid/duplicate input or query budget. |
| 2 | blocked | Incompatible installed definition/runtime/index or invalid configuration/credentials/HTTP 400. |
| 3 | blocked | HTTP 401. |
| 4 | blocked | Current site guard refusal or HTTP 403. |
| 5 | failed | HTTP 404; never evidence of an empty result. |
| 6 | failed | Transport/network failure or exhausted 429/5xx retries. |
| 7 | failed | Existing HTTP 409 conflict semantics. |
| 1 | unknown / failed | Malformed read evidence / other Surface failure. |

## Installed compatibility and help

`src/jira_as/workflows.json` is the single product-owned definition resource.
The shared `as_engine.workflows` API owns schema validation, discovery, bounded
read dispatch, projection, paging interpretation and rendering. The Jira adapter
only loads the resource, parses public arguments and supplies the current Surface.
It verifies the exact indexed document/operation/method/path, effective parameter
schemas, scope and paging evidence before configuration or a task call. The shared
runner repeats binding validation immediately before execution.

The definition declares optional response evidence for `startAt`, `maxResults`,
`total` and `isLast`, checked against the compiled response schema. Only `total`
is declared in the current indexed paging tag; no overlay change is implied.
Execution-semantic changes require supported schema/capability and definition
revisions. Descriptive additions belong in the contract's `annotations` namespace.

Installed distribution metadata supplies the base product version (`2.0.0`),
without the CLI's appended Python build identifier. The definition digest is
separate because that build identifier does not hash JSON resources. No release
version or published rc1 artifact is changed by this slice.

The concise root hint derives from the same catalog and names its version,
revision, capability and actionable search/describe syntax, without supplying a
workflow or operation ID. Standard `--help` places the same hint before the
command list and retains the existing root options. `help workflows` uses the
existing `{level,title,sections}` schema; examples retain `{kind,value}`. Existing
output caps remain 400/800/1200/600 token proxies for root/group/detail/examples.

With an allowed older engine lacking `as_engine.workflows`, default root help
retains its previous bytes, standard `--help` omits the new hint, and existing
API/legacy groups remain usable. An unavailable catalog/capability also omits the
hint. Workflow commands return a structured incompatibility with installed
versions and required schema/capability. Unvalidated identity fields are null.
Only that specific absent
module is a compatibility fallback; unrelated nested import/programming failures
remain errors. The adapter never installs or upgrades packages.

## Acceptance boundary

The public CLI test source uses real ConfigManager validation, packaged indexes,
Surface guards and transforms over controlled transport; accidental HTTP fails
immediately. It covers discovery, examples, multiple pages and duplicate names,
empty/unknown evidence, policy/credential/config failures, error exits, installed
definition/index mismatches, missing module/capability, hostile data and budgets.

Source preparation is not test or installation proof. Supervisor acceptance
separately requires targeted and full product/engine suites, configured coverage,
applicable checks, wheel/sdist resource alignment and the unmodified old-engine
wheel pairing. A fresh-agent smoke using the supervisor's 27-project fixture,
with two equal names under distinct IDs and no supplied workflow/operation ID,
is mandatory before local close. That one smoke is separate from the later
20-trial certification, native-tool proof, live sandbox acceptance and release.
