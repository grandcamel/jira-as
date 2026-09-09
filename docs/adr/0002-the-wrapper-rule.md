# The wrapper rule

**Status: Accepted 2026-09-09**

A named Wrapper Verb exists only when it makes more than one HTTP call with a
decision or loop between them, performs a transform that the spec cannot express
and no tag covers, or provides an auth, config, cache or paging affordance.
Prerequisite-only chains do not justify a verb: paging, identity resolution and
tagged rich-text conversion belong to the Generic Surface. Surviving HTTP
workflows use Surface.call for every request and keep their existing group and
verb names. This records JAS-31's rule, JAS-49's frozen decision 21 and decision
31's bounded 2.0.0rc1 exception.

The [decision table](../wrapper-verbs.md), backed by tests/wrapper_verbs.json,
classifies 208 original Jira verbs: 35 survivors, 143 dropped, fourteen kept by
the [Compatibility Contract](../compatibility-contract.md), and sixteen deferred
on the legacy client pending JAS-64. The contract is an explicit organizational
exception to the ordinary wrapper rule. The deferred Automation, Assets and
dev-status commands stay on their legacy guard and client for this rc; JAS-64
must close before 2.0.0 final.

We chose this over one command per operation and a private client inside every
wrapper, both of which let command behavior, help and guard enforcement drift
from the Enriched Spec. Retaining a Python export is not authority to reintroduce
a removed single-operation CLI verb.

## Consequences

- The 143 removed verbs remain migration shims. They send no requests, name the
  indexed api call replacement and exit 2; help remains available. The changelog
  records every dropped, retained and deferred verb and the twenty operationId
  identity renames. The public-client migration table accounts for every 1.2.0
  public member, including explicit no-equivalent and local-helper dispositions.
- The fourteen contract commands preserve output and legacy exits while using
  the shared guarded call path. Their narrowly bounded internal allowances stay
  documented and tested; generic API defaults remain unchanged.
- Surviving workflows use the same scope, paging, rich-text and risk transforms
  as api call. Bulk dry-run may read its targets, but does not send writes.
  Instance-field and autocomplete caches are explicit affordances.
- Decisions and loops are tested with stateful simulation; responder and cassette
  tests use the same transport seam. Per-wrapper tests cannot replace the
  contract suite and downstream release validation.
- The rc retains whole legacy client/mock modules because configuration,
  exports, helpers and tests still import them. Removal cannot silently broaden
  into those consumers. This dependency retention supports the sixteen deferred
  verbs; it does not claim that every retained method is an approved wrapper.
