# Cassettes, the SBX live suite and Base Document drift

The committed `tests/cassettes/compatibility.json` is **synthetic**. The local
fake service in `tests/test_cassette_contract.py` receives requests serialized
by `HTTPTransport`, including Basic authentication, and deliberately echoes
secret strings. The scrub-parity test records again to a temporary path, checks
that no registered credential or discovered account/cloud/cookie value survives,
and requires byte parity with the committed cassette and invocation sidecar.
This proves scrubbing and offline replay; it does not establish live Jira
compatibility.

## Offline replay

```bash
JIRA_ALLOWED_PROJECTS=SBX JIRA_AS_TRANSPORT=cassette \
  JIRA_AS_CASSETTE=tests/cassettes/compatibility.json \
  jira-as issue get SBX-1
python -m pytest -q tests/test_cassette_contract.py tests/test_devhost_argv.py
```

The test invokes every Compatibility Contract operation and all 25 variants
through CLI argv, including the labels pair, enrich fan-out, typed-link
preflights and transport prerequisites. It also invokes generic issue
read/create/edit/search, an owned deleted-key 404, and API search/describe/topics.
Socket connections, HTTP sends and credential loading are forbidden in replay.
These tests have no `live` marker and run in normal CI. An unmatched request
fails explicitly; playback has no network fallback.

`compatibility.argv.json` is an invocation sidecar, **not a Player cassette**.
It contains portable argv, private synthetic body-file contents, expected output
shapes and a SHA256 over the canonical invocation list. It deliberately has no
`format_version` or `interactions`. `scripts/record_cassettes.py` and the offline
test use the same `tests/live/scenarios.py` list. A host recording uses different
SBX keys and a unique prefix, so its own sidecar is required for exact replay.
Never point `JIRA_AS_CASSETTE` at an argv sidecar.

## Recording on the authorized host

After approval for the live SBX mutations, the supervisor runs one command:

```bash
scripts/jira-dev-host /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as --suite /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as/.venv/bin/python /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as/scripts/record_cassettes.py --out tests/cassettes/host.json
```

`--suite` runs in the wrapper's private CWD, so Python, script and test paths
must be absolute; the recorder resolves relative `--out` under the product root.

The recorder refuses an existing cassette or sidecar, non-HTTP transport,
conflicting cassette settings, or an allowed-project configuration other than
exactly SBX, or enabled site operations. The two host entrypoints require
`JIRA_DEFAULT_PROJECT=SBX`, reject explicitly wider policy, and bootstrap an
omitted allowlist to `JIRA_ALLOWED_PROJECTS=SBX` for the run. Every argv passes the same local gate mirror used by the property
test before invocation. Project-bearing bodies use JSON `@file` arguments;
`--field fields.project.key=SBX` remains a named GC-278 refusal. Body filenames
are relative to private directories so path names cannot be mistaken for issue
keys by the gate. The host wrapper cannot inspect file contents; the profile
independently limits its create bodies to SBX and its own run prefix/label.

One `create_surface()` instance records all measured calls. Separate
nonrecording surfaces create prerequisites and clean them up. Each mutable
variant uses its own disposable issue; link scenarios get two. This keeps the
engine's reusable request-key matching valid: a repeated key with a different
response is refused rather than silently overwritten. Read-only metadata calls
with identical responses coalesce. The engine registers site URL, email, token
and the encoded Basic credential before the first recorded request, then scrubs
recognized sensitive response fields recursively. See as-engine's
`docs/cassettes.md` for matching and scrub limitations.

All summaries and labels identify one unique run. The recorder caps creations
at 40, retains created keys, deletes its resources in `finally`, recovers
lost-response creations using the run label, and checks deletion by key and
an empty label search. The 404 probe uses an issue created and deleted by the
same run. Comments, worklogs and links belong only to these disposable issues.
A failure exits nonzero and prints the retained SBX key ledger and run label
for supervisor cleanup; partial files are not accepted fixtures.

Before adopting a host recording:

1. Verify `SBX cleanup verified: ... remaining=0` and the recorder's zero exit.
2. Inspect all scrubbed cassette and sidecar bytes, including opaque text.
3. Diff against the synthetic fixture, accounting for the host's unique keys.
4. Replay the host sidecar against its cassette with sockets and credential
   loading disabled using the command below from the product root.
5. Replace a committed fixture only after review. The recorder never replaces it.

```bash
.venv/bin/python -c 'from pathlib import Path; import pytest; import tests.test_cassette_contract as replay; replay.CASSETTE = Path("tests/cassettes/host.json").resolve(); raise SystemExit(pytest.main(["-q", "tests/test_cassette_contract.py", "-k", "all_contract_and_generic_invocations_replay_without_network"]))'
```

The frozen create-output URL regex is checked after replacing only the known
`<as-site-1>` placeholder with `https://cassette.invalid` in the assertion.
Stored bytes and emitted stdout remain scrubbed.

## The live suite

```bash
python -m pytest -q tests/live
JIRA_AS_TRANSPORT=simulation JIRA_ALLOWED_PROJECTS=SBX \
  python -m pytest -q tests/live --live
scripts/jira-dev-host /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as --suite /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as/.venv/bin/python -m pytest -q /Users/jasonkrueger/projects/lanes/jas-ab-w28/jira-as/tests/live --live
```

The first command collects and skips live tests. The second exercises the
session profile and CLI callbacks against one shared simulation store, with
explicit capability skips where the simulator cannot supply host data: full
issue JSON envelopes, absolute browse URLs, comment-list and link-type
operations, label-filtered JQL, and rendered worklog durations. Simulation
teardown verifies each retained key is absent; label-based lost-response
recovery remains a host check. The
third is the separately approved host step. Live assertions use observable
output shapes, and teardown failures fail the suite. The inventory includes
all contract/generic cases, an owned delete preview/confirmation round trip,
`search bulk-update --dry-run`, and `fields cache warm`.

`tests/devhost_shapes.json` is the supervisor's replayable argv export. Its
first forty examples retain their responder execution checks. Additional rows
come from contract operations and variants, the recorder and live inventories,
and a deterministic sample of compiled issue/project-parameter operations.
The generated sample checks the argv gate without sending arbitrary operations
to Jira. Hypothesis is not required. Gate findings remain negative regression
cases; the actual host `jira-dev-host --explain` replay is supervisor-owned.

## Base Document drift

The drift command checks the platform, software and servicedesk documents in
`src/jira_as/specs/manifest.json`, without refreshing any vendored document or
pin. `--from-file` selects only local replacements and makes no downloads:

```bash
python scripts/check_base_document_drift.py --oasdiff ../bin/oasdiff \
  --dry-run --from-file platform=/path/to/altered-platform.json
python scripts/check_base_document_drift.py --oasdiff ../bin/oasdiff \
  --dry-run --from-file platform=src/jira_as/specs/jira-platform-swagger-v3.json
```

An unchanged copy exits zero silently. Breaking changes or changes to enriched
operations produce a JSON Jira Task payload with a Markdown diff description
and component `jira-as`. Shared component/security/server changes conservatively
flag operation enrichments; unsupported enrichment selectors and invalid pins
fail explicitly. Offline tests include changed and unchanged actual vendored
copies and fake ticket filing.

`.github/workflows/drift.yml` runs weekly, on manual dispatch, and on prerelease
and published release events. It supplies `--file-ticket`, which submits an ADF
description to Jira. Repository secrets `JIRA_SITE_URL`, `JIRA_EMAIL` and
`JIRA_API_TOKEN` need authority to create JAS Tasks with component `jira-as`.
Missing configuration and rejected filing fail the job. No live filing is part
of worker validation. Repeated runs can file repeat tickets until a reviewed
Base Document refresh resolves the finding.
