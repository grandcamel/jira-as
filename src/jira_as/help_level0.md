# Jira Assistant Skills CLI

Discover and call Jira Cloud platform, Software and Service Management operations.

Usage: jira-as COMMAND. Use `--help` for command options.

API: `api search WORDS`, `api describe OPERATION [--full|--examples]`,
`api call OPERATION`, `api topics`.

Wrapper groups: issue, search, lifecycle, fields, ops, bulk, dev, relationships,
time, collaborate, agile, jsm, admin. Current wrappers remain; the wrapper rule
lands in JAS-49.

Topics: adf, paging, search, agile, fields, project-types, permissions, rate-limits,
representations, sandbox, auth, scope, risk, errors.

Learn: `help GROUP` or `help TOPIC`; `--format json`; `--examples`;
`--tier platform|software|servicedesk`; `--offset` for long lists.

Auth: `JIRA_SITE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and existing settings.
Discovery needs no credentials.

Sandbox: `JIRA_AS_TRANSPORT=http|responder|cassette|simulation`;
`api --transport responder`. Cassette uses `JIRA_AS_CASSETTE`;
simulation uses `JIRA_AS_SIMULATION_SEED`.

Risk-tagged calls preview by default; `--confirm` sends.
