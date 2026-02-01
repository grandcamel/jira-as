#!/usr/bin/env python3
"""
JIRA REST API Compliance Review Script.

Downloads official OpenAPI specifications from Atlassian and compares
the jira_client.py implementation against them to generate compliance reports.

Usage:
    python scripts/api_compliance_review.py [--output reports/api_compliance_report.md]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# OpenAPI specification URLs
OPENAPI_SPECS = {
    "platform": {
        "name": "Platform v3",
        "url": "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json",
        "prefix": "/rest/api/3/",
    },
    "agile": {
        "name": "Agile",
        "url": "https://developer.atlassian.com/cloud/jira/software/swagger.v3.json",
        "prefix": "/rest/agile/1.0/",
    },
    "jsm": {
        "name": "Service Management",
        "url": "https://developer.atlassian.com/cloud/jira/service-desk/swagger.v3.json",
        "prefix": "/rest/servicedeskapi/",
    },
}

# API v2 endpoints (screens, etc.)
API_V2_PREFIX = "/rest/api/2/"

# Insight/Assets API prefix
INSIGHT_PREFIX = "/rest/insight/1.0/"


@dataclass
class MethodInfo:
    """Information about a client method."""

    name: str
    endpoint: str | None
    http_method: str | None
    params: list[str]
    optional_params: list[str]
    docstring: str
    line_number: int
    api_category: str = ""

    def __str__(self) -> str:
        return f"{self.name}() -> {self.http_method} {self.endpoint}"


@dataclass
class ComplianceIssue:
    """A compliance issue found during review."""

    method_name: str
    endpoint: str
    issue_type: str
    severity: str  # 'critical', 'warning', 'info'
    description: str
    spec_value: str = ""
    impl_value: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.method_name}: {self.description}"


@dataclass
class EndpointMatch:
    """Match between implementation and spec endpoint."""

    method: MethodInfo
    spec_path: str
    spec_operation: dict[str, Any]
    issues: list[ComplianceIssue] = field(default_factory=list)
    is_compliant: bool = True


@dataclass
class CategoryReport:
    """Report for a single API category."""

    name: str
    api_type: str  # 'platform', 'agile', 'jsm'
    implemented_methods: list[MethodInfo] = field(default_factory=list)
    matched_endpoints: list[EndpointMatch] = field(default_factory=list)
    unmatched_methods: list[MethodInfo] = field(default_factory=list)
    missing_from_spec: list[str] = field(default_factory=list)
    issues: list[ComplianceIssue] = field(default_factory=list)

    @property
    def total_methods(self) -> int:
        return len(self.implemented_methods)

    @property
    def compliant_count(self) -> int:
        return sum(1 for m in self.matched_endpoints if m.is_compliant)

    @property
    def compliance_percentage(self) -> float:
        if not self.matched_endpoints:
            return 0.0
        return (self.compliant_count / len(self.matched_endpoints)) * 100


def download_spec(url: str) -> dict[str, Any]:
    """Fetch and parse OpenAPI JSON spec."""
    print(f"  Downloading: {url}")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"  Warning: Failed to download spec: {e}")
        return {}


def extract_endpoint_from_code(node: ast.FunctionDef) -> tuple[str | None, str | None]:
    """
    Extract endpoint URL and HTTP method from a function's code.

    Returns (endpoint, http_method) tuple.
    """
    endpoint = None
    http_method = None

    for child in ast.walk(node):
        # Look for calls like self.get(), self.post(), etc.
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute):
                method_name = child.func.attr.lower()
                if method_name in ("get", "post", "put", "delete"):
                    http_method = method_name.upper()

                    # Try to find the endpoint argument
                    if child.args:
                        first_arg = child.args[0]
                        if isinstance(first_arg, ast.Constant):
                            endpoint = first_arg.value
                        elif isinstance(first_arg, ast.JoinedStr):
                            # f-string like f"/rest/api/3/issue/{issue_key}"
                            endpoint = _extract_fstring_pattern(first_arg)

    return endpoint, http_method


def _extract_fstring_pattern(node: ast.JoinedStr) -> str:
    """Extract a pattern from an f-string, replacing variables with {placeholders}."""
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            # Get the variable name if simple
            if isinstance(value.value, ast.Name):
                parts.append(f"{{{value.value.id}}}")
            else:
                parts.append("{param}")
    return "".join(parts)


def extract_client_methods(filepath: Path) -> list[MethodInfo]:
    """Extract method information from jira_client.py."""
    print(f"Parsing client methods from: {filepath}")

    with open(filepath, "r") as f:
        source = f.read()

    tree = ast.parse(source)
    methods: list[MethodInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "JiraClient":
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Skip private/magic methods
                    if item.name.startswith("_"):
                        continue

                    # Get parameters
                    params = []
                    optional_params = []
                    defaults_start = len(item.args.args) - len(item.args.defaults)

                    for i, arg in enumerate(item.args.args):
                        if arg.arg == "self":
                            continue
                        if i >= defaults_start:
                            optional_params.append(arg.arg)
                        else:
                            params.append(arg.arg)

                    # Add kwargs if present
                    if item.args.kwarg:
                        optional_params.append(f"**{item.args.kwarg.arg}")

                    # Get docstring
                    docstring = ast.get_docstring(item) or ""

                    # Extract endpoint and HTTP method from code
                    endpoint, http_method = extract_endpoint_from_code(item)

                    method_info = MethodInfo(
                        name=item.name,
                        endpoint=endpoint,
                        http_method=http_method,
                        params=params,
                        optional_params=optional_params,
                        docstring=docstring,
                        line_number=item.lineno,
                    )

                    # Categorize method based on endpoint
                    method_info.api_category = categorize_method(method_info)
                    methods.append(method_info)

    print(f"  Found {len(methods)} public methods")
    return methods


def categorize_method(method: MethodInfo) -> str:
    """Categorize a method based on its endpoint and name."""
    endpoint = method.endpoint or ""
    name = method.name.lower()

    # JSM / Service Desk
    if "servicedeskapi" in endpoint or "service_desk" in name or "request" in name:
        if "customer" in name:
            return "JSM Customers"
        if "organization" in name:
            return "JSM Organizations"
        if "queue" in name:
            return "JSM Queues"
        if "sla" in name:
            return "JSM SLAs"
        if "approval" in name:
            return "JSM Approvals"
        if "participant" in name:
            return "JSM Participants"
        if "comment" in name and "request" in endpoint:
            return "JSM Comments"
        if "kb" in name or "knowledge" in name:
            return "JSM Knowledge Base"
        if "request" in name:
            return "JSM Requests"
        return "JSM Service Desks"

    # Insight/Assets
    if "insight" in endpoint or "asset" in name:
        return "Assets/Insight"

    # Agile
    if "agile" in endpoint:
        if "sprint" in name:
            return "Agile Sprints"
        if "board" in name:
            return "Agile Boards"
        if "backlog" in name:
            return "Agile Backlog"
        if "epic" in name:
            return "Agile Epics"
        if "rank" in name:
            return "Agile Ranking"
        return "Agile General"

    # Platform API categories
    if "issue" in endpoint:
        if "comment" in name:
            return "Issue Comments"
        if "worklog" in name or "time" in name:
            return "Time Tracking"
        if "transition" in name:
            return "Issue Transitions"
        if "link" in name:
            return "Issue Links"
        if "attach" in name:
            return "Attachments"
        if "changelog" in name:
            return "Issue Changelog"
        if "watcher" in name:
            return "Issue Watchers"
        if "notify" in name:
            return "Notifications"
        return "Issue Management"

    if "search" in name and "jql" in endpoint:
        return "Search"

    if "filter" in endpoint or "filter" in name:
        return "Filters"

    if "jql" in endpoint:
        return "JQL"

    if "project" in endpoint:
        if "version" in endpoint:
            return "Versions"
        if "component" in endpoint:
            return "Components"
        if "status" in endpoint:
            return "Project Statuses"
        if "avatar" in endpoint:
            return "Project Avatars"
        if "category" in name:
            return "Project Categories"
        if "type" in name:
            return "Project Types"
        if "role" in name:
            return "Project Roles"
        return "Projects"

    if "user" in endpoint or "user" in name:
        if "group" in name:
            return "User Groups"
        return "Users"

    if "group" in endpoint:
        return "Groups"

    if "version" in endpoint:
        return "Versions"

    if "component" in endpoint:
        return "Components"

    if "workflow" in endpoint or "workflow" in name:
        if "scheme" in name:
            return "Workflow Schemes"
        return "Workflows"

    if "status" in endpoint:
        return "Statuses"

    if "notification" in name or "notificationscheme" in endpoint:
        return "Notification Schemes"

    if "screen" in endpoint or "screen" in name:
        if "scheme" in name:
            return "Screen Schemes"
        return "Screens"

    if "issuetype" in endpoint:
        if "scheme" in name:
            return "Issue Type Schemes"
        if "screenscheme" in name:
            return "Issue Type Screen Schemes"
        return "Issue Types"

    if "permission" in endpoint or "permission" in name:
        return "Permission Schemes"

    if "myself" in endpoint:
        return "Current User"

    if "task" in endpoint:
        return "Async Tasks"

    return "Other"


def normalize_path_pattern(path: str) -> str:
    """
    Normalize an OpenAPI path pattern to match implementation patterns.

    Converts {issueIdOrKey} style to {issue_key} etc.
    """
    # Common replacements
    replacements = [
        (r"\{issueIdOrKey\}", "{issue_key}"),
        (r"\{projectIdOrKey\}", "{project_key}"),
        (r"\{worklogId\}", "{worklog_id}"),
        (r"\{commentId\}", "{comment_id}"),
        (r"\{attachmentId\}", "{attachment_id}"),
        (r"\{filterId\}", "{filter_id}"),
        (r"\{permissionId\}", "{permission_id}"),
        (r"\{schemeId\}", "{scheme_id}"),
        (r"\{screenId\}", "{screen_id}"),
        (r"\{tabId\}", "{tab_id}"),
        (r"\{fieldId\}", "{field_id}"),
        (r"\{issueTypeId\}", "{issue_type_id}"),
        (r"\{versionId\}", "{version_id}"),
        (r"\{componentId\}", "{component_id}"),
        (r"\{sprintId\}", "{sprint_id}"),
        (r"\{boardId\}", "{board_id}"),
        (r"\{serviceDeskId\}", "{service_desk_id}"),
        (r"\{requestIdOrKey\}", "{issue_key}"),
        (r"\{organizationId\}", "{organization_id}"),
        (r"\{queueId\}", "{queue_id}"),
        (r"\{accountId\}", "{account_id}"),
        (r"\{groupId\}", "{group_id}"),
        (r"\{groupname\}", "{group_name}"),
        (r"\{transitionId\}", "{transition_id}"),
        (r"\{linkId\}", "{link_id}"),
    ]

    result = path
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def match_paths(impl_endpoint: str, spec_path: str) -> bool:
    """
    Check if an implementation endpoint matches a spec path.

    Handles path parameters like {issueIdOrKey}.
    """
    if not impl_endpoint or not spec_path:
        return False

    # Normalize both paths
    norm_impl = normalize_path_pattern(impl_endpoint)
    norm_spec = normalize_path_pattern(spec_path)

    # Convert to regex pattern for matching
    # Replace {param} with a regex group
    pattern = re.sub(r"\{[^}]+\}", r"[^/]+", norm_spec)
    pattern = f"^{pattern}$"

    return bool(re.match(pattern, norm_impl))


def find_spec_match(
    method: MethodInfo, spec: dict[str, Any]
) -> tuple[str, dict[str, Any]] | None:
    """Find the matching OpenAPI spec path/operation for a method."""
    if not method.endpoint or not method.http_method:
        return None

    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        if match_paths(method.endpoint, path):
            http_method = method.http_method.lower()
            if http_method in path_item:
                return path, path_item[http_method]

    return None


def check_parameter_compliance(
    method: MethodInfo, spec_operation: dict[str, Any]
) -> list[ComplianceIssue]:
    """Check if method parameters match spec requirements."""
    issues: list[ComplianceIssue] = []

    spec_params = spec_operation.get("parameters", [])

    # Get required spec parameters
    required_params = {
        p["name"]: p
        for p in spec_params
        if p.get("required", False) and p.get("in") != "path"
    }

    # Get optional spec parameters
    optional_params = {
        p["name"]: p
        for p in spec_params
        if not p.get("required", False) and p.get("in") != "path"
    }

    # Check for missing required parameters
    impl_all_params = set(method.params + method.optional_params)

    for param_name, param_spec in required_params.items():
        # Map spec param names to Python-style names
        python_name = param_name.replace("Id", "_id").replace("Key", "_key")
        python_name = re.sub(r"([a-z])([A-Z])", r"\1_\2", python_name).lower()

        found = any(
            p == python_name or p == param_name or param_name.lower() in p.lower()
            for p in impl_all_params
        )

        if not found:
            issues.append(
                ComplianceIssue(
                    method_name=method.name,
                    endpoint=method.endpoint or "",
                    issue_type="missing_required_param",
                    severity="critical",
                    description=f"Missing required parameter: {param_name}",
                    spec_value=param_name,
                    impl_value=str(list(impl_all_params)),
                )
            )

    return issues


def check_request_body_compliance(
    method: MethodInfo, spec_operation: dict[str, Any]
) -> list[ComplianceIssue]:
    """Check if request body matches spec requirements."""
    issues: list[ComplianceIssue] = []

    request_body = spec_operation.get("requestBody", {})
    if not request_body:
        return issues

    is_required = request_body.get("required", False)

    # Check if method accepts body data
    has_body_param = any(
        p in ["data", "fields", "payload", "body"]
        for p in method.params + method.optional_params
    )

    if is_required and not has_body_param:
        issues.append(
            ComplianceIssue(
                method_name=method.name,
                endpoint=method.endpoint or "",
                issue_type="missing_request_body",
                severity="critical",
                description="Spec requires request body but method doesn't accept one",
                spec_value="required: true",
                impl_value="No body parameter found",
            )
        )

    return issues


def analyze_compliance(
    methods: list[MethodInfo], specs: dict[str, dict[str, Any]]
) -> dict[str, CategoryReport]:
    """Analyze compliance of methods against OpenAPI specs."""
    print("\nAnalyzing compliance...")

    # Group methods by category
    categories: dict[str, CategoryReport] = {}

    for method in methods:
        cat = method.api_category
        if cat not in categories:
            api_type = "platform"
            if "JSM" in cat or "Service" in cat:
                api_type = "jsm"
            elif "Agile" in cat:
                api_type = "agile"
            elif "Asset" in cat or "Insight" in cat:
                api_type = "assets"

            categories[cat] = CategoryReport(name=cat, api_type=api_type)

        categories[cat].implemented_methods.append(method)

    # Match methods to spec endpoints
    for category in categories.values():
        spec_key = category.api_type
        if spec_key == "assets":
            # Assets/Insight doesn't have public OpenAPI spec
            continue

        spec = specs.get(spec_key, {})
        if not spec:
            continue

        for method in category.implemented_methods:
            match = find_spec_match(method, spec)

            if match:
                path, operation = match
                endpoint_match = EndpointMatch(
                    method=method, spec_path=path, spec_operation=operation
                )

                # Check parameter compliance
                param_issues = check_parameter_compliance(method, operation)
                endpoint_match.issues.extend(param_issues)

                # Check request body compliance
                body_issues = check_request_body_compliance(method, operation)
                endpoint_match.issues.extend(body_issues)

                if endpoint_match.issues:
                    endpoint_match.is_compliant = False
                    category.issues.extend(endpoint_match.issues)

                category.matched_endpoints.append(endpoint_match)
            else:
                category.unmatched_methods.append(method)

    return categories


def find_missing_spec_endpoints(
    categories: dict[str, CategoryReport], specs: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    """Find spec endpoints that aren't implemented."""
    missing: dict[str, list[str]] = {}

    for api_type, spec in specs.items():
        if not spec:
            continue

        paths = spec.get("paths", {})
        implemented_paths: set[str] = set()

        # Collect all implemented paths for this API type
        for category in categories.values():
            if category.api_type == api_type:
                for match in category.matched_endpoints:
                    implemented_paths.add(match.spec_path)

        # Find missing paths
        api_missing: list[str] = []
        for path, path_item in paths.items():
            if path not in implemented_paths:
                methods = [m.upper() for m in path_item.keys() if m in ("get", "post", "put", "delete")]
                if methods:
                    summary = ""
                    for m in ["get", "post", "put", "delete"]:
                        if m in path_item:
                            summary = path_item[m].get("summary", "")[:50]
                            break
                    api_missing.append(f"{', '.join(methods)} {path} - {summary}")

        if api_missing:
            missing[api_type] = api_missing

    return missing


def generate_report(
    categories: dict[str, CategoryReport],
    missing_endpoints: dict[str, list[str]],
    specs_loaded: dict[str, bool],
) -> str:
    """Generate markdown compliance report."""
    lines: list[str] = []

    lines.append("# JIRA REST API Compliance Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary section
    lines.append("## Summary")
    lines.append("")
    lines.append("| API | Spec Status | Categories | Methods | Matched | Compliant | Issues |")
    lines.append("|-----|-------------|------------|---------|---------|-----------|--------|")

    api_stats: dict[str, dict[str, int]] = {}
    for api_type in ["platform", "agile", "jsm", "assets"]:
        api_stats[api_type] = {
            "categories": 0,
            "methods": 0,
            "matched": 0,
            "compliant": 0,
            "issues": 0,
        }

    for category in categories.values():
        api_type = category.api_type
        api_stats[api_type]["categories"] += 1
        api_stats[api_type]["methods"] += len(category.implemented_methods)
        api_stats[api_type]["matched"] += len(category.matched_endpoints)
        api_stats[api_type]["compliant"] += category.compliant_count
        api_stats[api_type]["issues"] += len(category.issues)

    for api_type, stats in api_stats.items():
        if stats["methods"] == 0:
            continue
        spec_status = "✅ Loaded" if specs_loaded.get(api_type, False) else "❌ Not Available"
        api_name = {
            "platform": "Platform v3",
            "agile": "Agile",
            "jsm": "Service Management",
            "assets": "Assets/Insight",
        }.get(api_type, api_type)

        lines.append(
            f"| {api_name} | {spec_status} | {stats['categories']} | {stats['methods']} | "
            f"{stats['matched']} | {stats['compliant']} | {stats['issues']} |"
        )

    lines.append("")

    # Critical issues section
    critical_issues = [
        issue for cat in categories.values() for issue in cat.issues if issue.severity == "critical"
    ]

    if critical_issues:
        lines.append("## Critical Issues (Priority Fix)")
        lines.append("")
        for i, issue in enumerate(critical_issues[:20], 1):
            lines.append(f"{i}. **{issue.method_name}**: {issue.description}")
            if issue.spec_value:
                lines.append(f"   - Expected: `{issue.spec_value}`")
            if issue.impl_value:
                lines.append(f"   - Actual: `{issue.impl_value}`")
        if len(critical_issues) > 20:
            lines.append(f"\n... and {len(critical_issues) - 20} more critical issues")
        lines.append("")

    # Category details
    lines.append("## Category Details")
    lines.append("")

    # Sort categories by API type and name
    sorted_categories = sorted(categories.values(), key=lambda c: (c.api_type, c.name))

    for category in sorted_categories:
        total = len(category.implemented_methods)
        matched = len(category.matched_endpoints)
        compliant = category.compliant_count

        status_icon = "✅" if compliant == matched and matched > 0 else "⚠️" if matched > 0 else "❓"

        lines.append(f"### {category.name} {status_icon}")
        lines.append("")
        lines.append(f"- **API Type**: {category.api_type}")
        lines.append(f"- **Total Methods**: {total}")
        lines.append(f"- **Matched to Spec**: {matched}")
        lines.append(f"- **Fully Compliant**: {compliant}")
        lines.append("")

        if category.matched_endpoints:
            lines.append("#### Implemented Methods")
            lines.append("")
            lines.append("| Method | Endpoint | HTTP | Status | Issues |")
            lines.append("|--------|----------|------|--------|--------|")

            for match in category.matched_endpoints:
                status = "✅" if match.is_compliant else "⚠️"
                issue_count = len(match.issues)
                issues_str = str(issue_count) if issue_count > 0 else "-"
                lines.append(
                    f"| `{match.method.name}` | `{match.method.endpoint}` | "
                    f"{match.method.http_method} | {status} | {issues_str} |"
                )

            lines.append("")

        if category.unmatched_methods:
            lines.append("#### Unmatched Methods (not found in spec)")
            lines.append("")
            for method in category.unmatched_methods:
                lines.append(f"- `{method.name}()` - {method.http_method or 'N/A'} {method.endpoint or 'N/A'}")
            lines.append("")

        if category.issues:
            lines.append("#### Issues")
            lines.append("")
            for issue in category.issues[:10]:
                severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
                    issue.severity, "⚪"
                )
                lines.append(f"- {severity_icon} **{issue.issue_type}**: {issue.description}")
            if len(category.issues) > 10:
                lines.append(f"- ... and {len(category.issues) - 10} more issues")
            lines.append("")

    # Missing endpoints section
    if missing_endpoints:
        lines.append("## Missing Endpoints (from spec)")
        lines.append("")
        lines.append("These endpoints exist in the OpenAPI spec but are not implemented:")
        lines.append("")

        for api_type, endpoints in missing_endpoints.items():
            api_name = OPENAPI_SPECS.get(api_type, {}).get("name", api_type)
            lines.append(f"### {api_name}")
            lines.append("")

            # Group by path prefix for readability
            shown = 0
            for endpoint in endpoints[:30]:
                lines.append(f"- `{endpoint}`")
                shown += 1

            if len(endpoints) > 30:
                lines.append(f"\n... and {len(endpoints) - 30} more endpoints")
            lines.append("")

    # Recommendations section
    lines.append("## Recommendations")
    lines.append("")
    lines.append("### High Priority")
    lines.append("")
    if critical_issues:
        lines.append(f"1. Fix {len(critical_issues)} critical issues (missing required parameters)")
    lines.append("2. Review unmatched methods for potential spec updates")
    lines.append("3. Consider implementing high-value missing endpoints")
    lines.append("")
    lines.append("### Future Enhancements")
    lines.append("")
    lines.append("- Add response schema validation")
    lines.append("- Implement deprecation warnings for deprecated endpoints")
    lines.append("- Add type hints that match spec schemas")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Review jira_client.py compliance with JIRA REST API specs"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="reports/api_compliance_report.md",
        help="Output file for compliance report",
    )
    parser.add_argument(
        "--client",
        "-c",
        default="src/jira_as/jira_client.py",
        help="Path to jira_client.py",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading specs (use cached)",
    )

    args = parser.parse_args()

    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    client_path = project_root / args.client
    output_path = project_root / args.output

    if not client_path.exists():
        print(f"Error: Client file not found: {client_path}")
        sys.exit(1)

    # Download OpenAPI specs
    print("Downloading OpenAPI specifications...")
    specs: dict[str, dict[str, Any]] = {}
    specs_loaded: dict[str, bool] = {}

    for key, spec_info in OPENAPI_SPECS.items():
        spec = download_spec(spec_info["url"])
        specs[key] = spec
        specs_loaded[key] = bool(spec)

    # Assets/Insight doesn't have a public OpenAPI spec
    specs_loaded["assets"] = False

    # Extract client methods
    methods = extract_client_methods(client_path)

    # Analyze compliance
    categories = analyze_compliance(methods, specs)

    # Find missing endpoints
    missing_endpoints = find_missing_spec_endpoints(categories, specs)

    # Generate report
    report = generate_report(categories, missing_endpoints, specs_loaded)

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"\nCompliance report written to: {output_path}")

    # Print summary to console
    total_methods = sum(len(c.implemented_methods) for c in categories.values())
    total_matched = sum(len(c.matched_endpoints) for c in categories.values())
    total_compliant = sum(c.compliant_count for c in categories.values())
    total_issues = sum(len(c.issues) for c in categories.values())

    print(f"\nSummary:")
    print(f"  Total methods: {total_methods}")
    print(f"  Matched to spec: {total_matched}")
    print(f"  Fully compliant: {total_compliant}")
    print(f"  Issues found: {total_issues}")


if __name__ == "__main__":
    main()
