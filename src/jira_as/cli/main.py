import os
from importlib import import_module
from pathlib import Path

import click
from as_engine.help import render_help

from jira_as import __version__
from jira_as._build import get_build_identifier
from jira_as.cli.commands.help_cmds import HelpGroup, surface_map


def get_version() -> str:
    """Identify the imported build, including edits after an editable install."""
    return f"{__version__} ({get_build_identifier()})"


class LazyGroups(HelpGroup):
    """Load a legacy command family only when it is selected."""

    modules = {
        "admin": ("admin_cmds", "admin"),
        "agile": ("agile_cmds", "agile"),
        "bulk": ("bulk_cmds", "bulk"),
        "collaborate": ("collaborate_cmds", "collaborate"),
        "dev": ("dev_cmds", "dev"),
        "fields": ("fields_cmds", "fields"),
        "issue": ("issue_cmds", "issue"),
        "jsm": ("jsm_cmds", "jsm"),
        "lifecycle": ("lifecycle_cmds", "lifecycle"),
        "ops": ("ops_cmds", "ops"),
        "relationships": ("relationships_cmds", "relationships"),
        "search": ("search_cmds", "search"),
        "time": ("time_cmds", "time"),
        "api": ("api_cmds", "api"),
        "serve": ("serve_cmds", "serve"),
        "help": ("help_cmds", "help_command"),
    }

    migration_groups = {
        "admin",
        "agile",
        "collaborate",
        "fields",
        "issue",
        "jsm",
        "lifecycle",
        "relationships",
        "search",
        "time",
    }

    def list_commands(self, ctx):
        return sorted(set(self.modules) | self.migration_groups | set(self.commands))

    def get_command(self, ctx, name):
        if name in self.commands:
            return self.commands[name]
        if name not in self.modules and name not in self.migration_groups:
            return None
        if name in self.modules:
            module_name, symbol = self.modules[name]
            module = import_module("jira_as.cli.commands." + module_name)
            command = getattr(module, symbol)
            if name == "collaborate":
                command.add_command(module.comment, name="comments")
            elif name == "search":
                command.add_command(module.search_query, name="jql")
        else:
            from jira_as.cli.legacy import MigrationGroup

            command = MigrationGroup(name, help="Legacy migration hints.")
        if name not in {"api", "help"}:
            from as_engine.index import ProductIndexes

            from jira_as.cli.legacy import records, register

            indexes = ProductIndexes(Path(__file__).parents[1] / "_generated")
            register(
                command, records(index for _, index in indexes.primary()), prefix=name
            )
        self.add_command(command, name)
        return command


# --- Global Options Design ---
@click.group(cls=LazyGroups, invoke_without_command=True)
@click.version_option(version=get_version(), prog_name="jira-as")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "table"]),
    default="text",
    help="Output format (default: text)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.pass_context
def cli(ctx, output: str, verbose: bool, quiet: bool):
    """Jira Assistant Skills CLI.

    Use --help on any command for more information.
    """
    ctx.ensure_object(dict)
    ctx.obj["OUTPUT"] = output
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["QUIET"] = quiet

    # Set environment variables for subprocess calls to inherit global options
    env_prefix = "JIRA"  # This will be dynamic for other services
    if output:
        os.environ[f"{env_prefix}_OUTPUT"] = output
    if verbose:
        os.environ[f"{env_prefix}_VERBOSE"] = "true"
    if quiet:
        os.environ[f"{env_prefix}_QUIET"] = "true"

    # Register cleanup callback to close HTTP client on exit
    def cleanup():
        if ctx.obj and "_client" in ctx.obj:
            client = ctx.obj["_client"]
            if hasattr(client, "close"):
                client.close()

    ctx.call_on_close(cleanup)

    if ctx.invoked_subcommand is None:
        click.echo(render_help(surface_map()))
