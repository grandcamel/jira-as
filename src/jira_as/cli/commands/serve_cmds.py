"""Run the same Jira package as an authoritative Split Mode sidecar."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import click
from as_engine.errors import SurfaceError
from as_engine.serve import decode_frame, tcp_address, token_prelude
from as_engine.serve import serve as run_server
from as_engine.surface import Surface

from jira_as.cli.main import get_version
from jira_as.config_manager import ConfigManager
from jira_as.engine import create_surface
from jira_as.error_handler import ValidationError


def _binding(seat_home: Path) -> list[str]:
    path = seat_home / "jira-binding.json"
    try:
        with path.open("rb") as stream:
            data = stream.read(65537)
        if len(data) > 65536:
            raise ValueError("binding is too large")
        record = decode_frame(data)
        if (
            not isinstance(record, dict)
            or set(record) != {"schema_version", "primary", "permitted"}
            or type(record["schema_version"]) is not int
            or record["schema_version"] != 1
            or not isinstance(record["primary"], str)
            or not isinstance(record["permitted"], list)
            or not record["permitted"]
            or any(
                not isinstance(key, str)
                or re.fullmatch(r"[A-Z][A-Z0-9_]*", key) is None
                for key in record["permitted"]
            )
            or len(set(record["permitted"])) != len(record["permitted"])
            or record["primary"] not in record["permitted"]
        ):
            raise ValueError("invalid binding record")
    except (OSError, ValueError, SurfaceError) as exc:
        raise click.UsageError(f"Missing or malformed binding: {path}") from exc
    return record["permitted"]


def _token(path: Path) -> str:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise ValueError("unsafe token file")
            value = stream.read(4097).decode("ascii").removesuffix("\n")
        token_prelude(value)
        return value
    except (OSError, ValueError, SurfaceError) as exc:
        raise click.UsageError(
            "--token-file must be an owned regular 0600 file containing one ASCII token"
        ) from exc


@click.group(invoke_without_command=True)
@click.version_option(version=get_version(), prog_name="jira-as")
@click.option("--socket", "socket_path", type=click.Path(path_type=Path), default=None)
@click.option("--tcp", metavar="127.0.0.1:PORT", default=None)
@click.option("--token-file", type=click.Path(path_type=Path), default=None)
@click.option("--binding", type=click.Path(path_type=Path), default=None)
@click.option("--call-log", type=click.Path(path_type=Path), required=True)
@click.option("--allow-site/--no-allow-site", default=None)
def serve(
    socket_path: Path | None,
    tcp: str | None,
    token_file: Path | None,
    binding: Path | None,
    call_log: Path,
    allow_site: bool | None,
) -> None:
    """Serve validated Jira calls in the foreground using this installed build.

    The host holds credentials. Mount its Unix socket into the credential-free
    client. Binary downloads and multipart uploads are unsupported in Split Mode.
    """
    try:
        permitted = _binding(binding) if binding is not None else None
        config = ConfigManager.get_instance()
        if "JIRA_ALLOWED_PROJECTS" in os.environ:
            allowlist, source = config.get_allowed_projects(), "JIRA_ALLOWED_PROJECTS"
        elif permitted is not None:
            allowlist, source = permitted, "binding"
        else:
            allowlist, source = config.get_allowed_projects(), "configured policy"
            if allowlist is None:
                allowlist, source = [], "empty default"
        if allowlist is None:
            allowlist = []
        site = config.get_allow_site_operations() if allow_site is None else allow_site
        address = None
        token = None
        if tcp is not None:
            if socket_path is not None or token_file is None:
                raise click.UsageError(
                    "--tcp requires --token-file and excludes --socket"
                )
            try:
                host, port = tcp.rsplit(":", 1)
                address = tcp_address((host.strip("[]"), int(port)))
            except ValueError as exc:
                raise click.UsageError(
                    "--tcp requires a literal loopback address and port"
                ) from exc
            token = _token(token_file)
        else:
            if token_file is not None:
                raise click.UsageError("--token-file requires --tcp")
            if socket_path is None:
                runtime = os.environ.get("XDG_RUNTIME_DIR")
                socket_path = (
                    Path(runtime) / "jira-as.sock"
                    if runtime
                    else Path(f"/tmp/jira-as-{os.getuid()}.sock")
                )

        def factory() -> Surface:
            direct = create_surface(transport="http")
            # The CLI resolved policy at startup; the serving Surface must not
            # re-read and override it on the first request.
            return Surface(
                direct.indexes,
                direct.transport_factory,
                scope_allowlist=allowlist,
                scope_allow_site=site,
                scope_resolution_rules=direct.scope_resolution_rules,
            )

        click.echo(
            f"serve: allowlist source={source}; count={len(allowlist)}", err=True
        )
        run_server(
            factory,
            socket_path=socket_path,
            tcp=address,
            token=token,
            call_log=call_log,
            allowlist=allowlist,
            allow_site=site,
        )
    except (OSError, ValueError, ValidationError) as exc:
        # Configuration/OS exceptions may contain endpoint/token values.
        raise click.UsageError(
            "Unable to start serve: check endpoint, policy and private file permissions"
        ) from exc
