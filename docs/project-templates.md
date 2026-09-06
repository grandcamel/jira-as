# Project templates and management style

`jira-as admin project create` accepts `--template` as a shorthand or a full
Jira template key. The software shorthands `scrum`, `kanban`, and `basic`
default to **team-managed** projects (Jira's `style: next-gen`). Use
`--style classic` for a **company-managed** project. Omitting `--style`
preserves the existing template mapping; it does not change an explicit
classic template into a team-managed one.

## Software mappings

Every suffix below has the full prefix `com.pyxis.greenhopper.jira:`.

| Shorthand | Default or `--style team-managed` suffix | `--style classic` suffix |
| --- | --- | --- |
| `scrum` | `gh-simplified-agility-scrum` | `gh-scrum-template` |
| `kanban` | `gh-simplified-agility-kanban` | `gh-kanban-template` |
| `basic` | `gh-simplified-basic` | `basic-software-development-template` |

For example, the full company-managed Kanban key is
`com.pyxis.greenhopper.jira:gh-kanban-template`.

```bash
jira-as admin project create -k EXAMPLE -n "Example project" -t software \
  --template kanban --style classic -o json

jira-as admin project create -k EXAMPLE -n "Example project" -t software \
  --template kanban --style team-managed -o json
```

These are alternative examples: choose the desired style before creating
the project. With `-t software` and no `--template`, the template is `scrum`;
`--style classic` selects classic Scrum, and omission selects team-managed Scrum.

The existing fixed aliases remain supported:

| Alias | Full template key |
| --- | --- |
| `classic-scrum` | `com.pyxis.greenhopper.jira:gh-scrum-template` |
| `classic-kanban` | `com.pyxis.greenhopper.jira:gh-kanban-template` |
| `simplified-scrum` | `com.pyxis.greenhopper.jira:gh-simplified-agility-scrum` |
| `simplified-kanban` | `com.pyxis.greenhopper.jira:gh-simplified-agility-kanban` |

A known full key or fixed alias must agree with an explicit `--style`.
For example, `--template com.pyxis.greenhopper.jira:gh-kanban-template
--style team-managed` raises a validation error before project creation.
Custom full keys still work without `--style`. An explicit style with an
unclassified full key is rejected because the CLI cannot verify that mapping.

## Other project types

`--style` is supported for software projects only. Business and service desk
templates keep their existing mappings and defaults without the option:

| Shorthand | Full template key |
| --- | --- |
| `project-management` (business default) | `com.atlassian.jira-core-project-templates:jira-core-project-management` |
| `task-management` | `com.atlassian.jira-core-project-templates:jira-core-task-management` |
| `it-service-desk` (service desk default) | `com.atlassian.servicedesk:simplified-it-service-desk` |
| `general-service-desk` | `com.atlassian.servicedesk:simplified-general-service-desk` |

## Creation output

Jira's create response supplies `id`, `key`, and `self`. The CLI reads the
created project with GET and adds its reported `style` to the response,
preserving all existing response keys. JSON uses Jira's values: `classic`
for company-managed and `next-gen` for team-managed. Text displays, for
example, `Style: classic (company-managed)` or `Style: next-gen (team-managed)`.
The reported style comes from Jira, rather than being inferred from the request.

If the follow-up read fails or returns no style, the command exits with an
error explicitly stating that the project was created. Inspect it with
`jira-as admin project get EXAMPLE` before retrying creation.

## Trashed project keys and names

A trashed project still reserves its key and name. Creating the wrong style
and moving it to trash does not make either available for immediate reuse;
recovery may require a Jira administrator to permanently delete the project.
Choose the management style deliberately before running create.
