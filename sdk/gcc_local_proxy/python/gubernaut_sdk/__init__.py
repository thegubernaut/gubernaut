"""gubernaut_sdk — one-call SDK facade over the GCC local proxy.

Quickstart (one import, one call):

    from gubernaut_sdk import launch_proxy

    proxy = launch_proxy(upstream="https://api.openai.com")
    # point any OpenAI-compatible client at proxy.base_url; stop with proxy.stop()

Framework helpers return plain kwargs dicts (no framework is imported here):

    ChatOpenAI(**langchain_kwargs("gpt-4o-mini"))          # LangChain
    OpenAI(**llamaindex_kwargs("gpt-4o-mini"))             # LlamaIndex
    openai.OpenAI(**openai_kwargs())                       # OpenAI SDK

The governed state of every response is exposed in `x-gcc-*` headers; the
HEADER_* constants below name them. A saturated recursive loop is answered by
the deterministic hard-stop completion (content starts with ``[GCC]``, zero
upstream tokens) instead of an upstream call.

No consciousness claims: a measured, falsifiable regulation layer.
Byline: Gubernaut Research.
"""

from __future__ import annotations

import os

import httpx

from gcc_proxy import __version__
from gcc_proxy.actuation import HARD_STOP_TEXT
from gcc_proxy.config import GCCConfig

from gubernaut_sdk.errors import (
    GubernautError, GubernautConnectionError, GubernautConfigError)
from gubernaut_sdk.host import GccProxy, launch_proxy

# Response-header names set by the proxy on every governed completion.
# These mirror gcc_proxy.proxy._gcc_headers exactly (asserted in tests).
HEADER_POSTURE = "x-gcc-posture"
HEADER_TEMPERATURE_MAX = "x-gcc-temperature-max"
HEADER_EQUILIBRIUM = "x-gcc-equilibrium"
HEADER_AROUSAL = "x-gcc-arousal"
HEADER_PERSEVERATION = "x-gcc-perseveration"
HEADER_REPETITION = "x-gcc-repetition"
HEADER_RECOVERY = "x-gcc-recovery"
HEADER_HARD_STOP = "x-gcc-hard-stop"

ALL_HEADERS = (
    HEADER_POSTURE,
    HEADER_TEMPERATURE_MAX,
    HEADER_EQUILIBRIUM,
    HEADER_AROUSAL,
    HEADER_PERSEVERATION,
    HEADER_REPETITION,
    HEADER_RECOVERY,
    HEADER_HARD_STOP,
)


def default_base_url() -> str:
    """The proxy base clients should target (env GCC_PROXY_BASE overrides)."""
    return os.environ.get("GCC_PROXY_BASE", "http://127.0.0.1:8000/v1")


def preflight(base_url: str | None = None, timeout: float = 2.0) -> dict:
    """Confirm a governed proxy is actually in front of your traffic.

    GETs ``/gcc/health`` at the root of ``base_url`` (default: the SDK's target
    base). Returns the health dict on success; raises
    :class:`GubernautConnectionError` if the proxy is unreachable or unhealthy.
    Call this before sending real traffic when you want to *fail closed on
    purpose* — better a loud error than ungoverned requests to the upstream.
    """
    base = base_url or default_base_url()
    root = base[:-3] if base.rstrip("/").endswith("/v1") else base
    root = root.rstrip("/")
    url = f"{root}/gcc/health"
    try:
        resp = httpx.get(url, timeout=timeout)
    except httpx.HTTPError as e:
        raise GubernautConnectionError(base, f"{type(e).__name__}: {e}") from e
    if resp.status_code != 200:
        raise GubernautConnectionError(base, f"health returned HTTP {resp.status_code}")
    return resp.json()


def openai_kwargs(base_url: str | None = None,
                  api_key: str | None = None) -> dict:
    """Kwargs for ``openai.OpenAI(...)`` pointing at the governed proxy.

    ``api_key`` is included only when given; otherwise the client's own
    environment resolution applies (the proxy forwards the client's
    Authorization header verbatim and stores nothing).
    """
    kwargs: dict = {"base_url": base_url or default_base_url()}
    if api_key is not None:
        kwargs["api_key"] = api_key
    return kwargs


def langchain_kwargs(model: str,
                     base_url: str | None = None,
                     api_key: str | None = None) -> dict:
    """Kwargs for LangChain ``ChatOpenAI(...)`` pointing at the governed proxy."""
    kwargs: dict = {"model": model, "base_url": base_url or default_base_url()}
    if api_key is not None:
        kwargs["api_key"] = api_key
    return kwargs


def llamaindex_kwargs(model: str,
                      api_base: str | None = None,
                      api_key: str | None = None) -> dict:
    """Kwargs for LlamaIndex ``OpenAI(...)`` pointing at the governed proxy."""
    kwargs: dict = {"model": model, "api_base": api_base or default_base_url()}
    if api_key is not None:
        kwargs["api_key"] = api_key
    return kwargs


__all__ = [
    "GccProxy",
    "launch_proxy",
    "GCCConfig",
    "HARD_STOP_TEXT",
    "GubernautError",
    "GubernautConnectionError",
    "GubernautConfigError",
    "default_base_url",
    "preflight",
    "openai_kwargs",
    "langchain_kwargs",
    "llamaindex_kwargs",
    "HEADER_POSTURE",
    "HEADER_TEMPERATURE_MAX",
    "HEADER_EQUILIBRIUM",
    "HEADER_AROUSAL",
    "HEADER_PERSEVERATION",
    "HEADER_REPETITION",
    "HEADER_RECOVERY",
    "HEADER_HARD_STOP",
    "ALL_HEADERS",
    "__version__",
]
