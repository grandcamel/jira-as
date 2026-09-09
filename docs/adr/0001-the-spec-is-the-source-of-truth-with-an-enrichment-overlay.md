# The spec is the source of truth with an enrichment overlay

**Status: Accepted 2026-09-09**

Jira-as takes its operation surface from three pinned, pristine Base Documents:
Jira platform v3, Jira Software and Jira Service Management. Corrections, unique
operation identities, scope, paging, rich text, risk, binary-response metadata,
advisory notes and help live in evidence-bearing OpenAPI Overlay actions. The
product records each action's reason, evidence, origin and test. As-engine
applies the supported targets and compiles the Enriched Spec into the catalog
and three operation indexes at build time. The Generic Surface and help read
those same indexes at runtime. This records the JAS-31 architecture as applied
by JAS-45, JAS-46, JAS-47 and JAS-65.

We chose this over editing upstream documents, which obscures upstream drift,
and over separately maintaining client methods, command definitions and help,
which creates competing sources of truth. Jira-as owns its documents, overlays,
configuration, scope policy and Wrapper Verbs. As-engine owns the shared compiler,
Generic Surface, transforms and transport seam. The organizational
[Compatibility Contract](../compatibility-contract.md) additionally preserves
fourteen Jira-host commands' invocation, output and legacy exit behavior.

## Consequences

- Each Base Document has a recorded version, SHA256 and fetch date. Refreshes
  are deliberate reviewed diffs; install and runtime do not fetch documents.
- Unsupported overlay targets fail closed. Provenance and generated entry tests
  are release evidence; the independent overlay check does not introduce another
  runtime applier. Twenty identity renames preserve distinct colliding routes.
- Source documents and overlays are committed; generated indexes are build
  artifacts shipped in the wheel. All three Jira documents are primary.
- Generated scope tags enforce the configured project allowlist before transport,
  including hidden body identities and bounded JQL. Body-only identities require
  matching project context. Site operations need explicit opt-in. Wrapper
  workflows use the same guard, with the contract's narrowly documented internal
  metadata allowances; an offline transport does not bypass policy.
- Help and replacement hints derive from the same compiled surface. Enrichment,
  argv, transport and build tests protect behavior and request shape. Responder,
  simulation and scrubbed cassette tests share the transport seam.
- The drift job compares all three pinned documents with upstream and reports
  breaking or enriched-operation changes. Live SBX evidence and downstream-main
  validation are separate acceptance steps; offline tests cannot substitute.
- The release records its engine dependency and preserves the Compatibility
  Contract. The 2.0.0rc1 legacy exception for JAS-64 does not authorize a second
  source of truth for newly implemented operations.
