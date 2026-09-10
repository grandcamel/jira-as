"""Lazy product adapter for the optional, shared indexed-read workflow contract."""

from __future__ import annotations

import hashlib
import json
from importlib import import_module, metadata, resources
from pathlib import Path
from types import ModuleType
from typing import Any

import click


class _Unavailable(Exception):
    def __init__(self, result: dict[str, Any], runtime: ModuleType | None = None):
        self.result = result
        self.runtime = runtime


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "unknown"


def _unavailable(raw: bytes | None = None) -> dict[str, Any]:
    """Only the absent optional module/resource needs an adapter-owned envelope."""
    definition_digest = hashlib.sha256(raw).hexdigest() if raw is not None else None
    return {
        "product": "jira-as",
        "product_version": _version("jira-as"),
        "engine_version": _version("as-engine"),
        "schema_version": None,
        "required_schema_version": 1,
        "runtime_capabilities": [],
        "required_capabilities": ["indexed-read-v1"],
        "definition_digest": definition_digest,
        "catalog_revision": None,
        "workflow": None,
        "revision": None,
        "support": None,
        "availability": "blocked",
        "status": "blocked",
        "exit_code": 2,
        "inputs": {},
        "items": [],
        "returned_count": 0,
        "limit": None,
        "offset": None,
        "range": None,
        "complete": None,
        "continuation": None,
        "evidence": {},
        "reason": {
            "code": "incompatible-definition-or-runtime",
            "message": "Workflow metadata or the optional engine capability is unavailable; check installed package alignment.",
        },
        "next_actions": [{"action": "inspect-configuration-or-definition"}],
    }


def _load() -> tuple[ModuleType, Any]:
    try:
        raw = resources.files("jira_as").joinpath("workflows.json").read_bytes()
    except OSError:
        raise _Unavailable(_unavailable()) from None
    try:
        runtime = import_module("as_engine.workflows")
    except ModuleNotFoundError as exc:
        if exc.name != "as_engine.workflows":
            raise
        raise _Unavailable(_unavailable(raw)) from None
    try:
        catalog = runtime.Catalog.load(
            raw, product="jira-as", product_version=_version("jira-as")
        )
    except runtime.WorkflowError as exc:
        raise _Unavailable(exc.result, runtime) from None
    return runtime, catalog


def workflow_hint() -> str | None:
    """Derived help is absent when the installed catalog cannot be supported."""
    try:
        _, catalog = _load()
    except _Unavailable:
        return None
    return catalog.hint()


def _format(ctx: click.Context) -> str:
    explicit = ctx.params.get("output_format") or ctx.meta.get("workflow_format")
    if explicit in {"markdown", "json"}:
        return explicit
    return "json" if (ctx.find_root().obj or {}).get("OUTPUT") == "json" else "markdown"


def _emit(
    ctx: click.Context, result: dict[str, Any], runtime: ModuleType | None
) -> None:
    output_format = _format(ctx)
    if runtime is not None:
        text = runtime.render_result(result, format=output_format)
    else:
        # This envelope contains no provider/argv text. Keep the existing help
        # schema usable even with an engine that has no workflows module.
        text = json.dumps(result, ensure_ascii=True, sort_keys=True)
        if output_format == "markdown":
            from as_engine.help import render_help

            text = render_help(
                {
                    "level": 1,
                    "title": "Workflow result",
                    "sections": [{"examples": [{"kind": "json", "value": text}]}],
                }
            )
    code = result["exit_code"]
    click.echo(text, err=code != 0)
    ctx.exit(code)


def _input_failure(ctx: click.Context) -> None:
    try:
        runtime, catalog = _load()
    except _Unavailable as exc:
        _emit(ctx, exc.result, exc.runtime)
        return
    provenance = catalog.provenance
    workflow = ctx.params.get("workflow") or ctx.meta.get("workflow_id")
    if workflow:
        try:
            provenance = catalog.get(workflow).provenance
        except runtime.WorkflowError as exc:
            _emit(ctx, exc.result, runtime)
            return
    result = runtime.failure_result(
        provenance, reason="invalid-input", status="needs-input"
    )
    _emit(ctx, result, runtime)


class WorkflowCommand(click.Command):
    """Keep public parser errors structured and reject scalar information loss."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        options = {
            option: parameter
            for parameter in self.params
            if isinstance(parameter, click.Option)
            for option in parameter.opts
        }
        seen: set[str] = set()
        duplicate = False
        position = 0
        if self.name in {"run", "describe"} and args and not args[0].startswith("-"):
            ctx.meta["workflow_id"] = args[0]
        while position < len(args):
            argument = args[position]
            if argument == "--":
                break
            spelling, equal, value = argument.partition("=")
            parameter = options.get(spelling)
            if parameter is not None:
                name = parameter.name or spelling
                duplicate |= name in seen
                seen.add(name)
                if (
                    not parameter.is_flag
                    and not equal
                    and position + 1 < len(args)
                    and args[position + 1].partition("=")[0] not in options
                ):
                    position += 1
                    value = args[position]
                if name == "output_format" and value in {"markdown", "json"}:
                    ctx.meta["workflow_format"] = value
            position += 1
        try:
            if duplicate:
                raise click.UsageError("Duplicate scalar workflow option")
            return super().parse_args(ctx, args)
        except click.UsageError:
            _input_failure(ctx)
            return []


def _execute(ctx: click.Context, action: str, **inputs: Any) -> None:
    try:
        runtime, catalog = _load()
    except _Unavailable as exc:
        _emit(ctx, exc.result, exc.runtime)
        return
    try:
        if action == "list":
            result = catalog.list(**inputs)
        elif action == "search":
            result = catalog.search(**inputs)
        elif action == "describe":
            result = catalog.describe(**inputs)
        else:
            definition = catalog.get(inputs.pop("workflow"))
            normalized = runtime.normalize_inputs(definition, inputs)
            from as_engine.index import ProductIndexes

            # Index compatibility is a local prerequisite, before configuration.
            try:
                indexes = ProductIndexes(Path(__file__).parents[2] / "_generated")
            except (OSError, ValueError, KeyError):
                raise runtime.WorkflowError(
                    runtime.failure_result(
                        definition.provenance,
                        reason="incompatible-definition-or-runtime",
                    )
                ) from None
            runtime.validate_binding(definition, indexes)
            from as_engine.errors import SurfaceError
            from assistant_skills_lib.error_handler import ValidationError

            from jira_as.engine import create_surface

            try:
                surface = create_surface()
            except ValueError:
                result = runtime.failure_result(definition.provenance)
                result.update(inputs=normalized, **normalized, view="run")
            else:
                factory = surface.transport_factory

                def configured_transport(document: str, index: Any) -> Any:
                    try:
                        return factory(document, index)
                    except ValidationError:
                        # The existing credentials validator has no HTTP status;
                        # preserve its local validation meaning before Surface
                        # converts generic domain errors to HTTP-derived exits.
                        raise SurfaceError(None, [], code=2) from None

                surface.transport_factory = configured_transport
                result = runtime.run(definition, normalized, surface)
    except runtime.WorkflowError as exc:
        result = exc.result
    _emit(ctx, result, runtime)


@click.group()
def workflows() -> None:
    """Discover supported agent tasks and run a bounded, guarded read."""


@workflows.command("list", cls=WorkflowCommand)
@click.option("--offset", type=click.IntRange(min=0), default=0)
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]))
@click.pass_context
def list_workflows(ctx: click.Context, offset: int, output_format: str | None) -> None:
    """List supported tasks without checking account availability."""
    _execute(ctx, "list", offset=offset)


@workflows.command("search", cls=WorkflowCommand)
@click.argument("query")
@click.option("--offset", type=click.IntRange(min=0), default=0)
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]))
@click.pass_context
def search_workflows(
    ctx: click.Context, query: str, offset: int, output_format: str | None
) -> None:
    """Find supported tasks using ordinary task words."""
    _execute(ctx, "search", query=query, offset=offset)


@workflows.command("describe", cls=WorkflowCommand)
@click.argument("workflow")
@click.option("--examples", is_flag=True)
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]))
@click.pass_context
def describe_workflow(
    ctx: click.Context, workflow: str, examples: bool, output_format: str | None
) -> None:
    """Describe a task's inputs, prerequisites and bounded result contract."""
    _execute(ctx, "describe", workflow=workflow, examples=examples)


@workflows.command("run", cls=WorkflowCommand)
@click.argument("workflow")
@click.option("--limit", type=click.IntRange(1, 100), default=25, show_default=True)
@click.option("--offset", type=click.IntRange(0, 9223372036854775807), default=0)
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]))
@click.pass_context
def run_workflow(
    ctx: click.Context,
    workflow: str,
    limit: int,
    offset: int,
    output_format: str | None,
) -> None:
    """Read one page with current configuration and scope enforcement."""
    _execute(ctx, "run", workflow=workflow, limit=limit, offset=offset)
