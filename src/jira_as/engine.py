"""Jira configuration and packaged indexes for the Generic Surface."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from as_engine.errors import SurfaceError
from as_engine.index import OperationIndex, ProductIndexes
from as_engine.responder import Responder
from as_engine.surface import Surface
from as_engine.transport import HTTPTransport, Response, Transport

if TYPE_CHECKING:
    from as_engine.cassette import Recorder
    from as_engine.simulation import SimulationStore


class _ConfiguredSurface(Surface):
    """Load project policy once, before the first guard or transport send."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._scope_loaded = False
        self._scope_overrides: set[str] = set()

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"scope_allowlist", "scope_allow_site"}:
            overrides = self.__dict__.get("_scope_overrides")
            if overrides is not None:
                overrides.add(name)
        super().__setattr__(name, value)

    def call(self, *args: Any, **kwargs: Any) -> Response:
        if not self._scope_loaded:
            from jira_as.config_manager import ConfigManager
            from jira_as.error_handler import ValidationError

            try:
                config = ConfigManager.get_instance()
                allowed = config.get_allowed_projects()
                scope = {
                    "scope_allowlist": None if allowed is None else tuple(allowed),
                    "scope_allow_site": config.get_allow_site_operations(),
                }
            except (ValueError, ValidationError) as exc:
                raise SurfaceError(None, [str(exc)], code=2) from exc
            for name, value in scope.items():
                if name not in self._scope_overrides:
                    setattr(self, name, value)
            self._scope_loaded = True
        try:
            return super().call(*args, **kwargs)
        except SurfaceError as exc:
            if exc.code == 4 and any(
                "explicit command identity" in message for message in exc.messages
            ):
                raise SurfaceError(
                    exc.status,
                    [*exc.messages, "Body-only project scope requires --project KEY."],
                    exc.operation,
                    exc.note,
                    code=exc.code,
                ) from exc
            raise


def create_surface(
    *,
    transport: str | None = None,
    respond_with: int = 200,
    store: SimulationStore | None = None,
) -> Surface:
    """Keep discovery and responder mode credential-free; configure HTTP at call time."""
    mode = transport or os.environ.get("JIRA_AS_TRANSPORT", "http")
    if mode not in ("http", "responder", "cassette", "simulation"):
        raise ValueError(
            "JIRA_AS_TRANSPORT must be http, responder, cassette or simulation"
        )
    cassette_path = os.environ.get("JIRA_AS_CASSETTE")
    record_path = os.environ.get("JIRA_AS_RECORD")
    if mode == "cassette" and not cassette_path:
        raise ValueError("cassette transport requires JIRA_AS_CASSETTE")
    if record_path and mode != "http":
        raise ValueError("JIRA_AS_RECORD requires http transport")
    if cassette_path and mode != "cassette":
        raise ValueError("JIRA_AS_CASSETTE requires cassette transport")
    seed_path = os.environ.get("JIRA_AS_SIMULATION_SEED")
    if seed_path and mode != "simulation":
        raise ValueError("JIRA_AS_SIMULATION_SEED requires simulation transport")
    if store is not None and mode != "simulation":
        raise ValueError("simulation store requires simulation transport")
    if not 100 <= respond_with <= 599:
        raise ValueError("--respond-with must be an HTTP status from 100 to 599")
    if respond_with != 200 and mode != "responder":
        raise ValueError("--respond-with requires responder transport")
    indexes = ProductIndexes(Path(__file__).parent / "_generated")
    simulation_store = store
    if mode == "simulation" and simulation_store is None:
        from as_engine.simulation import SimulationStore

        if seed_path:
            try:
                seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("unable to load JIRA_AS_SIMULATION_SEED") from exc
            simulation_store = SimulationStore(seed)
        else:
            simulation_store = SimulationStore()

    recorder: Recorder | None = None

    def factory(document: str, index: OperationIndex) -> Transport:
        nonlocal recorder
        if mode == "cassette":
            if cassette_path is None:
                raise ValueError("cassette transport requires JIRA_AS_CASSETTE")
            from as_engine.cassette import Player

            return Player(cassette_path)
        if mode == "responder":
            return Responder(index, status=respond_with)
        if mode == "simulation":
            if simulation_store is None:
                raise AssertionError("simulation store was not initialized")
            from as_engine.simulation import Simulation

            return Simulation(simulation_store)
        from jira_as.config_manager import ConfigManager
        from jira_as.error_handler import handle_jira_error

        config = ConfigManager.get_instance()
        site_url, email, api_token = config.get_credentials()
        settings = config.get_api_config()
        site = site_url.rstrip("/")
        base = site
        live = HTTPTransport(
            base,
            auth=(email, api_token),
            timeout=settings.get("timeout", 30),
            max_retries=settings.get("max_retries", 3),
            retry_backoff=settings.get("retry_backoff", 2),
            verify_ssl=settings.get("verify_ssl", True),
            error_handler=(lambda *_: None) if record_path else handle_jira_error,
        )

        if not record_path:
            return live
        from as_engine.cassette import Recorder, Scrubber

        scrubber = recorder.scrubber if recorder is not None else Scrubber()
        scrubber.register(site, "site")
        scrubber.register(email)
        scrubber.register(api_token)
        # Register the wire's Basic value too, including echoes in free text.
        basic = base64.b64encode((email + ":" + api_token).encode()).decode()
        scrubber.register(basic)
        if recorder is None:
            try:
                recorder = Recorder(live, record_path, scrubber=scrubber)
            except (ValueError, OSError):
                live.close()
                raise
        else:
            recorder.transport = live
        return recorder

    return _ConfiguredSurface(indexes, factory)
