# Jira Assistant Skills CLI

Discover and call Jira Cloud platform, Software and Service Management operations.

Usage: jira-as COMMAND. Use `--help` for command options.

API: `api search WORDS`, `api describe OPERATION [--full|--examples]`,
`api call OPERATION`, `api topics`.

Survivor groups: bulk, lifecycle, fields, ops, relationships, search, time,
dev, agile and jsm. Compatibility groups: issue and collaborate.
Migration hints: `help migration`, or invoke an old group or verb. 143 wrappers
are dropped; 14 compatibility verbs remain. Deferred legacy client commands:
admin automation and automation-template, dev get-commits, and jsm assets
(16 total; JAS-64).

Topics: adf, paging, search, agile, fields, project-types, permissions, rate-limits,
representations, sandbox, auth, scope, risk, errors, migration.

Learn: `help GROUP` or `help TOPIC`; `--format json`; `--examples`;
`--tier platform|software|servicedesk`; `--offset` for long lists.

Auth: `JIRA_SITE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and existing settings.
Discovery needs no credentials.

Fields: `fields list`, `fields get`, and `fields cache warm` use cached instance
metadata. `api call --adf-field customfield_ID` explicitly converts Markdown to ADF;
a warm textarea cache enables automatic conversion. Sandbox:
`JIRA_AS_TRANSPORT=http|responder|cassette|simulation`; simulation is stateful for
survivor workflows. Cassette uses `JIRA_AS_CASSETTE`.

Risk-tagged calls preview by default; `--confirm` sends. Attachment transport and
generic risk enrichment remain pending JAS-65.
