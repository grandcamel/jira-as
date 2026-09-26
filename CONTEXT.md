# Jira CLI scope

The CLI has a local scope policy in addition to the permissions Atlassian applies to a caller's token.

## Language

**Interactive profile**:
An explicitly selected posture for a trusted human's direct CLI invocation. It lets Jira decide project and site access from the caller's token while retaining the CLI's input validation and risk confirmation.
_Avoid_: Admin token, unrestricted token

**Enforcing posture**:
The default posture that checks project and site scope locally before sending a request. It is the posture for automation and served calls.
_Avoid_: Sandbox mode

**Project allowlist**:
A local set of project keys that narrows which projects an enforcing call may touch. It is separate from Jira permissions.
_Avoid_: Token scope
