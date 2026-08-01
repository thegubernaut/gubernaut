"""In-process host for the GCC proxy: a uvicorn server on a daemon thread.

Wraps the exact same app the ``gcc-proxy`` CLI serves (`gcc_proxy.proxy
.create_app`), so programmatic and CLI adoption govern identically.
"""

from __future__ import annotations

import dataclasses
import threading
import time

import httpx
import uvicorn

from gcc_proxy.config import GCCConfig
from gcc_proxy.proxy import create_app

from gubernaut_sdk.errors import GubernautConnectionError


class GccProxy:
    """A governed local proxy you can start/stop from Python.

    ``port=0`` (default) binds an ephemeral free port; read ``base_url``
    after ``start()``. ``transport`` injects an ``httpx.MockTransport`` as
    the upstream (tests / offline demos).
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 0,
                 upstream: str | None = None,
                 hard_stop: bool = True,
                 config: GCCConfig | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        cfg = config or GCCConfig.from_env()
        overrides: dict = {"host": host, "port": port}
        if upstream is not None:
            overrides["upstream_base"] = upstream
        if not hard_stop:
            overrides["hard_stop_enabled"] = False
        self.config = dataclasses.replace(cfg, **overrides)
        self._server = uvicorn.Server(uvicorn.Config(
            create_app(self.config, transport=transport),
            host=self.config.host, port=self.config.port, log_level="warning"))
        self._thread: threading.Thread | None = None
        self._port: int | None = None

    def start(self, timeout: float = 15.0, preflight: bool = False) -> "GccProxy":
        if self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._server.run,
                                        name="gcc-proxy", daemon=True)
        self._thread.start()
        deadline = time.monotonic() + timeout
        while not self._server.started:
            if not self._thread.is_alive():
                raise RuntimeError("gcc proxy server thread exited during startup")
            if time.monotonic() > deadline:
                raise RuntimeError(f"gcc proxy did not start within {timeout}s")
            time.sleep(0.02)
        self._port = self._server.servers[0].sockets[0].getsockname()[1]
        if preflight:
            # Confirm the proxy we just started actually answers before handing
            # it back — a caller asking for fail-safe adoption wants a loud error
            # here, not a surprise mid-traffic.
            try:
                r = httpx.get(f"{self.root_url}/gcc/health", timeout=2.0)
                if r.status_code != 200:
                    raise GubernautConnectionError(
                        self.base_url, f"health returned HTTP {r.status_code}")
            except httpx.HTTPError as e:
                raise GubernautConnectionError(
                    self.base_url, f"{type(e).__name__}: {e}") from e
        return self

    @property
    def port(self) -> int:
        if self._port is None:
            raise RuntimeError("proxy not started — call start()")
        return self._port

    @property
    def base_url(self) -> str:
        """OpenAI-compatible base for clients, e.g. http://127.0.0.1:PORT/v1"""
        return f"http://{self.config.host}:{self.port}/v1"

    @property
    def root_url(self) -> str:
        """Server root (health/state endpoints live under /gcc/...)."""
        return f"http://{self.config.host}:{self.port}"

    def stop(self, timeout: float = 10.0) -> None:
        if self._thread is None:
            return
        self._server.should_exit = True
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise RuntimeError(f"gcc proxy did not shut down within {timeout}s")
        self._thread = None

    def __enter__(self) -> "GccProxy":
        return self.start()

    def __exit__(self, *exc_info) -> None:
        self.stop()


def launch_proxy(preflight: bool = False, **kwargs) -> GccProxy:
    """One call: construct AND start a governed proxy. Returns the running host.

    ``preflight=True`` verifies the proxy answers ``/gcc/health`` before
    returning, raising :class:`GubernautConnectionError` otherwise.
    """
    return GccProxy(**kwargs).start(preflight=preflight)
