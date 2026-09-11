# Private Jira workflow pilot in personal ChatGPT

This pilot exposes four MCP tools backed by one fixed installed `jira-as` console
script. Only `list-projects` can execute, through the existing CLI parser,
configuration manager, indexed GET binding and Surface guards. Search and describe
help select that task; they do not authorize access or execute examples.

**Native activation is blocked.** As of the 2026-09-11 source charge, no approved
current route delivers the required account identity, explicit project policy and
site-read permission to this adapter. The existing Grand Camel development broker
is SBX-scoped and is not an authorization route for account-visible project
listing. No successful fixture test grants access or removes this prerequisite.

The target is the user's personal ChatGPT workspace. A user-supplied existing
tunnel is recorded in the supervisor's `jas83-evidence/tunnel-binding.json`; its
workspace/Platform-organization association is unverified. Use that operator
record to identify it. This document contains no tunnel credential and does not
authorize tunnel creation, configuration or startup, account changes, broker
edits, `.env` sourcing, publication, or public hosting.

## Acceptance boundaries

The supervisor accepted the preceding shared-scenario extraction with exact
ordered parity for 126 existing CLI cases and a full run of that CLI workflow
file. That result applies to the preceding source snapshot only.

The new `tests/test_workflow_mcp.py` is source-authored and **NOT RUN** at this
phase boundary. It requires the MCP SDK at collection; absence is a failure,
not a skip. The tests use public SDK initialization, tools/list and tools/call
over an in-memory connection and an SDK stdio connection. A test-owned fixed
launcher executes the current installed console script with `runpy`, controlling
only local configuration sources and HTTP transport construction. Real product
parsing, index validation, configuration, guards, projection and paging remain
active. Recorded requests must be GET-only and match exact operation, path,
parameters and body expectations. Requests Session.send, DNS and unexpected
socket connections fail immediately; `.env`, settings and Keychain fallback are
disabled in that fixture.

Every paired call compares the complete product CLI JSON object with MCP
structured content, the decoded text block, isError and the advertised output
schema. Child import origins, actual console-script hash and installed catalog
digest are checked. Ordinary/reduced/default-bound, incomplete/malformed,
duplicate/overflow, links/hostile text, scope and HTTP-error inputs come from
`tests/workflow_scenarios.py`. Missing context and mismatched identity tests
verify the earlier adapter admission boundary independently of product errors.

These tests can run against an editable test installation. They do not establish
noneditable packaging, unmodified console behavior, authenticated account
identity, live provider responses, ChatGPT connectivity, tunnel containment, or
native readiness. A controlled wrong profile expectation checks compatibility
refusal against real installed metadata; it never forges a passing catalog.

## Prepare the fixed installation

The supervisor owns this sequence after the source review and required test
Clearance. Do not run these steps from the dispatched source-only worker.

1. Run the complete engine and Jira suites, required static checks and builds
   under the canonical validation reservation. Keep the original CLI suite and
   its parameterizations; do not narrow collection to obtain a green result.
   Verify the mandatory MCP tests on Python 3.10 and 3.11. Full suites must pass
   before committing; landing and any publication remain separately authorized.
2. Build and freeze the exact candidate engine and Jira wheels. In a separate
   noneditable environment, install those local artifacts and the engine's
   optional `mcp` extra: `mcp==2.2.0` and `jsonschema>=4.18`. The ordinary engine
   installation does not require MCP. Use the matching interpreter and installed
   console script; do not resolve an unrelated published engine during a build.
3. Record wheel hashes, resolved package versions, dependency-check results,
   interpreter path, module import origins, canonical console-script path and
   SHA-256, and the exact installed `jira_as/workflows.json` digest. Record its
   schema version, catalog revision and the `list-projects` revision. Freeze
   those values before building the operator profile.
4. From a scratch working directory, run credential-free discovery through the
   **unmodified installed** console script. Keep the exact command/exit/stream
   evidence. These are the business argv (replace only the absolute executable):

   ```text
   <fixed-venv>/bin/jira-as workflows list --format=json
   <fixed-venv>/bin/jira-as workflows search --format=json -- "What Jira projects can I see?"
   <fixed-venv>/bin/jira-as workflows describe --format=json -- list-projects
   ```

   A separately controlled denied or missing-runtime run uses
   `workflows run --limit=25 --offset=0 --format=json -- list-projects` and must
   perform no HTTP request. Verify the ordinary install and help/discovery still
   work without the optional SDK; explicit adapter launch without the extra
   must fail with the short missing-dependency diagnostic.

The fixed executable for production is the installed console script itself.
Do not use the test launcher, fixture credential values, a source checkout, a
shell command string, a model-supplied path, or PATH discovery for this binding.
The fixture pins its launcher separately because fixture injection is part of
its controlled test boundary.

## Bind an operator profile and approved context

The adapter accepts a nonsecret operator profile, schema version 1. Store it at
a canonical absolute path as a regular nonsymlink file owned by the launching
account, mode 0600. The profile is read once; each validated instance snapshots
the admitted environment. Later ambient changes do not silently change that
instance's identity or scope. A new approved context requires a new profile/server
lifetime with normal ownership cleanup first.

| Profile field | Required operator evidence |
| --- | --- |
| `schema_version`, `product`, `adapter_id` | `1`, `jira-as`, and a stable private name matching `[a-z][a-z0-9-]{0,79}`. |
| `executable`, `executable_sha256` | Canonical absolute installed console-script path and exact SHA-256 from the frozen install. No shell, executable arguments, symlink or PATH lookup. |
| `expected.product_version`, `expected.engine_version` | Exact installed versions from the same environment. |
| `expected.schema_version`, `expected.catalog_revision` | Supported schema 1 and the actual installed catalog revision. |
| `expected.definition_digest` | SHA-256 of the actual installed catalog bytes, including whitespace. |
| `expected.workflow_revisions` | Exactly the installed `list-projects` revision under that key. |
| `context.source` | `approved-env-v1`; naming this source is not approval. |
| `context.account_email`, `context.site_url` | Approved configured account email and canonical lowercase HTTPS origin. Independently verify the authenticated identity behind the credential. |
| `context.home`, `context.cwd`, `context.tmpdir` | Canonical existing directories owned by the launching account and not group/world writable; verify the product's installed configuration precedence there. |
| `context.scope.allowed_projects` | Explicit sorted unique project list. Missing scope defaults to `[]` in the profile, but the matching environment variable must still be present. |
| `context.scope.allow_site_operations` | Explicit approved boolean, default false. Account-visible project search requires separately granted site-read authority. |
| `context.scope.default_project` | Approved default in the list, or null with no default variable present. |

Unknown profile keys, duplicate JSON keys, nonfinite values, malformed identity,
unsafe file ownership, excessive depth/size and unsupported scopes fail closed.
No credential belongs in the profile, argv, catalog, test evidence or repository.

For a run, the existing approved host route must provide `JIRA_SITE_URL`,
`JIRA_EMAIL`, `JIRA_API_TOKEN`, **present** `JIRA_ALLOWED_PROJECTS` and
`JIRA_ALLOW_SITE_OPERATIONS`, plus a matching `JIRA_DEFAULT_PROJECT` only when
the profile has one. This document does not supply that route or prescribe
permission-setting exports. Explicit `JIRA_ALLOWED_PROJECTS=""` represents an
empty list; omission is refused because product omission may mean unrestricted
access. Empty project policy cannot grant site access. A matching false site flag
is forwarded unchanged and the product guard refuses the read before HTTP.

The profile binds configured identity and scope, not the authenticated token
owner. The supervisor must verify account, site, authorized operation, effective
configuration and package origins before any live call. A tunnel identifier or
successful discovery supplies none of these proofs.

Execution supports direct HTTP only: `JIRA_AS_TRANSPORT` must be absent or
literal `http`. Selected proxy/CA routing, alternate transports and unsupported
configuration refuse admission. The child environment starts empty, then adds
fixed execution directories/locale/PATH and only admitted Jira values for runs.
Discovery receives no Jira credentials or policy. Platform/tunnel credentials,
bare credential aliases, arbitrary JIRA settings and Python path overrides are
not passed to the product child. No `.env` or Keychain lookup is performed by
the adapter; product fallback behavior still needs host acceptance.

Once every gate is satisfied, the operator's fixed adapter command is:

```text
<adapter-venv>/bin/python -I -m as_engine.workflow_mcp --profile <absolute-private-profile.json>
```

The profile path is an operator launch argument. No tool accepts an environment,
command, executable, file, credential, site, account, permission or transport.
Before activation, an unavailable approved context remains a blocker; do not
replace it with the test fixture's values or change a broker to make admission
appear successful.

## Four tools and interpretation

| Tool | Arguments | Meaning |
| --- | --- | --- |
| `workflows_list` | Optional `offset`, default 0 | Inspect the installed catalog without account availability checks. |
| `workflows_search` | Required `query`, optional discovery `offset` | Search task descriptions; query is 1–512 characters, nonblank and NUL-free. |
| `workflows_describe` | Required `workflow: "list-projects"`, optional boolean `examples` | Inspect metadata, bounds and examples without executing an example. |
| `workflows_run` | Required `workflow: "list-projects"`, optional `inputs` | One bounded read. `inputs.limit` defaults to 25, range 1–100; `inputs.offset` defaults to 0, range 0–9223372036854775807. |

Discovery offsets use the same nonnegative 64-bit bound. Input objects are closed,
including nested inputs. Integers exclude booleans and integral floats; nulls
and strings do not coerce. Unsupported workflows produce `unsupported-workflow`;
unknown tool names produce protocol invalid-params `-32602`. Other invalid
arguments produce adapter `invalid-input`, without a child.

The SDK's Python fields use snake_case; wire fields use `structuredContent`,
`isError`, `inputSchema` and `outputSchema`. SDK 2.2.0 legacy initialization uses
handshake version **2025-11-25**, despite its overall latest version being
2026-07-28. The supervisor's earlier engine tools/list observation was 130951
bytes, above asyncio's default 64 KiB line limit. The Jira tests use the public
SDK stdio reader; a separate raw reader must declare a suitable bounded capacity
before reading. Do not discard an oversized frame or raise a limit after failure
and count that as the original observation.

`structuredContent` is the full validated product object. Its single text block
decodes to the same object, with dangerous rendering characters escaped.
`isError` is true for a nonzero product exit or an adapter error. Product errors
retain their status, reason, evidence and exit mapping: HTTP 400/401/403 map to
blocked exits 2/3/4; 404/409 map to failed exits 5/7; 429/503 map to failed exit6.
Provider messages and credential markers are sanitized by the product/adapter;
raw child diagnostics are never shown as tool results.

Exit zero does not imply a complete inventory. A reduced page may be incomplete
with an explicit continuation. A successful unknown-completion result may have
`complete: null` and no continuation. Malformed, contradictory, duplicate or
overflow pages preserve unknown status and received/omitted evidence. Never
infer exhaustiveness, discard retained items, invent a continuation or repair a
provider URL. A valid self link must identify the project; hostile names remain
inert data. Visible non-SBX projects are not silently filtered by the adapter.

Read `reason`, `complete`, `range`, `evidence`, `continuation` and `next_actions`
on each response. Request another page explicitly only when its scope is approved;
the adapter does not auto-traverse. Offset traversal is not a transactional
snapshot, so provider changes between reads can change results.

## Limits, errors and cleanup

| Limit | Default | Allowed override |
| --- | ---: | --- |
| Run deadline | 180 seconds | Integer 1–600 |
| Discovery deadline | 10 seconds per child | Integer 1–30 |
| stdout / stderr retention | 1 MiB each | Integer 4096–1048576 bytes each |
| Terminate / kill grace | 2 seconds each | Integer 1–5 seconds each |
| Pipe drain grace | 1 second | Integer 1–5 seconds |

The limit keys are `call_timeout_seconds`, `discovery_timeout_seconds`,
`stdout_max_bytes`, `stderr_max_bytes`, `terminate_grace_seconds`,
`kill_grace_seconds` and `drain_grace_seconds` in the optional `limits` object.
Profile input is bounded to 64 KiB, JSON depth to 32, decoded tool arguments to
16 KiB and serialized CallToolResult to 4 MiB. These are distinct from raw SDK
frame-memory limits. No product data is silently truncated to fit.

One child is admitted at a time; concurrent calls return `busy`. The adapter
neither queues calls nor retries the CLI. Product retries/Retry-After may exceed
the configured deadline; timeout is an interruption, not proof retries exhausted.
Startup, stream overflow, cancellation and deadline cleanup retain the actual
owned handle, wait for it and require both stream endpoints to settle. Signals
target only that handle. There are no new process groups, borrowed PIDs or
general descendant-containment guarantees.

Missing or malformed context yields `runtime-context-unavailable`; mismatched
identity or scope yields `identity-binding-mismatch`, before a run child.
Executable drift, incompatible catalog/output, invalid JSON, unexpected streams,
unsafe output, launch failures and output bounds yield sanitized adapter errors.
Each error includes phase, observed child exit, stdout/stderr byte counts,
counts_complete, cleanup and dispatch_blocked. Predispatch refusals have no
child/bytes; postexecution failures retain the actual invocation's observation.
Saved failures describe their original invocation, not a fresh attempt.

Unresolved spawn, reap or streams yield `cleanup-unresolved` and permanently
refuse further child dispatch in that instance. Tools/list remains inspectable.
Do not automatically restart or treat a late cleanup as a new grant. Resolve
the exact owned state through the approved host process before a new lifetime.
Client cancellation may suppress its response; orderly server shutdown and a
quiet task are not hard-death containment proof. The actual fixed HTTP CLI and
tunnel child/descendant behavior must be assessed before native use.

## Native gate and bounded comparison

The supervisor/operator must complete all of these before configuring or starting
the existing tunnel:

1. Accept the final source, full suites, both Python versions, static/package
   checks, frozen-wheel discovery, denied-run smoke and both-root landing.
2. Establish an explicitly approved account-visible `searchProjects` site-read
   scope and an existing authorized way to deliver the exact adapter context.
   This route is currently missing. If no route exists, obtain a separately
   scoped decision; no broker edits are included here.
3. Verify authenticated account/site identity, explicit project/default/site
   policy, installed configuration precedence and immutable package/profile
   identity. Confirm the fixed HTTP child does not spawn unmanaged descendants
   in that configuration.
4. Read back the existing tunnel's association with the intended personal
   ChatGPT workspace and Platform organization. Verify developer-mode eligibility,
   runtime authentication and Tunnels Read+Use. Read+Manage is only needed for a
   separately authorized creation/edit. Keep runtime tunnel authentication out of
   the product environment. No runtime API key has been supplied to this worker.
5. Verify the client's actual schema-size, deadline, cancellation and connection
   behavior. The supplied documentation described developer mode under Settings
   → Security and a Plugins/Tunnel connection, but this UI/access path must be
   checked for the actual account at the authorized native step. A previously
   supplied tunnel ID is not a successful connection test.

Only after those proofs and activation approval, bind the existing tunnel to the
fixed adapter command, keep its client running, inspect all four discovered tool
schemas, and use a fresh personal ChatGPT conversation. Ask for the supported
project-listing task, inspect its description, then approve exactly one
`workflows_run` call with `{"workflow":"list-projects","inputs":{"limit":25,"offset":0}}`.
Record actual arguments and the complete result/error.

Compare it in the same account, approved scope and bounded time window with the
unmodified fixed CLI's `workflows run --limit=25 --offset=0 --format=json -- list-projects`.
Compare provenance, status/reason/exit, identity/order of items, range,
received/omitted counts, completeness and continuation. Preserve full envelopes
as private evidence and explain observed provider drift rather than fabricating
parity. An incomplete first page is a valid bounded result, not permission for an
unbounded traversal. No write, extra workflow, account provisioning or public
service is part of the comparison.

Capture the exact evidence paths and unrun boundaries in the supervisor report.
A fixture pass, installed smoke, connection test and real native read are four
separate observations. Native completion requires the final real comparison;
until then the native gate remains blocked or unvalidated as recorded above.
