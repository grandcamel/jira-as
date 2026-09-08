# Compatibility Contract

`src/jira_as/compat/contract.json` records the fourteen operations emitted by
Grand Camel's `scripts/jira-host`. Each operation has its host flag allowlists,
ordered invocation variants, exit codes, output grammar, and provenance. Labels
uses a read/merge/update pair; enrich emits estimate, worklog, then comment. A
typed link/unlink also reads `relationships link-types --output json` before
its main command. These nested calls do not introduce additional host operations.

The evidence is pinned **1.1.3 read captures via jira-host** and **1.2.1 full
captures via the SBX development wrapper**, recorded September 7, 2026. There
was no captured 1.2.0 binary. The contract names the 1.2.x line and the comparable
1.1.3 read shapes honestly. Data values differ between the two target projects;
structural output, rather than particular issue contents, is the contract.
Scrubbed representative captures and source hashes live under
`tests/compat/captures/`; CI needs no other repository or private lane evidence.

Contract command callbacks use the compiled Generic Surface for their requests.
Existing output formatters retain text tables, success messages and raw JSON.
The compatibility adapter maps API failures and local scope refusal to legacy
exit **1**, while Click usage errors remain **2** and success is **0**. The
`api` group retains its separate, more detailed exit codes. jira-host's enrich
aggregate exit **3** describes advisory child failures and is not a CLI error
code. jira-host passes no project allowlist environment setting: its child
resolves policy from configuration; the compatibility suite explicitly sets
`JIRA_ALLOWED_PROJECTS=SBX` and disables site operations.

Both `time log SBX-1 --time 2h30m` and `--time '2h 30m'` send
`timeSpentSeconds: 9000`. CLI parsing is independent of jira-host's separate
h/m/s flooring-to-whole-minutes and sub-minute skip policy. Description Markdown
auto-detection remains available; `issue update --format markdown|text|adf`
selects an explicit input format. Comment body/file/stdin sources retain their
literal newline rules. Markdown conversion uses the engine's tagged converter;
explicit literal text is wrapped in schema-validated ADF without empty text
nodes. The rebuilt paths do not use the legacy adf_helper converter.

Create sends `issuetype.name` as in 1.x; the free-map create body does not require
an issue-type ID lookup. Story points first consults configured project metadata
or the existing field cache; on a miss it makes one generic `getFields` call and
requires an unambiguous instance field ID. It does not guess a hardcoded ID.
Transition retains the issue context read, name/ID selection, and bounded
comment/resolution screen-rejection retry. A transport observer retains only
sanitized field rejection diagnostics for that existing decision. Surface still
validates and guards every attempt, including the separate fallback comment.

## Scope and bounded internal allowances

Every keyed read or write goes through the same scope guard as `api`. The new
`platform.compat.overlay.json` opts only replacement GET/POST issue search into
single-field trailing ordering (`key`, `created`, `updated`). The AND-only
project filter is proved first; OR/NOT/functions, unapproved or multiple ordering
fields and trailing syntax refuse. `linkIssues` has required `key_paths` for
both issue keys. Each project must independently be allowed, including links
between two different allowed projects. Missing or malformed keys refuse.

These internal allowances are limited to the compatibility workflow; they never
change the configured Surface default or public `api` permission:

| Operation | Internal allowance and prerequisite |
|---|---|
| `getFields` | One instance-field metadata read on story-point cache miss; no project content. The explicit `fields cache warm` affordance also permits this one metadata read and persists it under the v2 instance cache; public `api call getFields` remains refused. |
| `getIssueLinkTypes` | Instance link-type metadata for link-types and typed link validation. |
| `deleteIssueLink` | Only after guarded `getIssue(source, fields=issuelinks)`, one unambiguous link matches the explicit source/target keys, and both keys pass membership. The numeric ID alone grants nothing. |
| `getCurrentUser` | Caller account ID only for `issue create --assignee self`. The update helper does not receive this allowance. |

`api call getFields`, `getIssueLinkTypes`, `deleteIssueLink`, and `getCurrentUser`
remain site-refused unless site operations are explicitly enabled. The suite
checks these refusals and the allowed workflow sequences at the transport seam.

## Validation and remaining migration

Default pytest discovers the compatibility suite. It drives command argv through
seeded genuine Responders and validates output against the package contract. A
green negative test removes required `fields.labels` and asserts validation
fails. Separate checks exercise Markdown wire bodies, both duration forms,
metadata lookup/cache paths, cross-project links, numeric deletion proof, and
legacy errors. Captures provide the shape baseline; responder fixtures provide
small deterministic issue data, never fabricated output in production code.

Non-contract commands and their legacy helpers remain for JAS-49. Shared legacy
helpers used by those paths are retained; migrated callbacks select the generic
contract implementations locally. Issue get --comments, native link flags, remote-link and unlink-all affordances remain
on their existing paths. No version, release workflow, legacy client or mock
implementation is changed by this contract migration. Contract behavior changes
require a major version; the duration and explicit-format additions are the
specific additive quirks recorded for this migration.
