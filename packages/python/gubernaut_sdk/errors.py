"""Typed errors for the Gubernaut SDK.

Before 0.1.1 the SDK had no exception hierarchy: a down proxy surfaced only as
whatever the client library raised (``httpx.ConnectError`` /
``openai.APIConnectionError``), and a bad config as a bare ``RuntimeError``.
These give integrators a stable, catchable surface — and make the fail-**safe**
contract explicit: when the governed proxy is unreachable, you get a
``GubernautConnectionError``, never a silent fall-through to an ungoverned
upstream.
"""

from __future__ import annotations


class GubernautError(Exception):
    """Base class for all Gubernaut SDK errors."""


class GubernautConnectionError(GubernautError):
    """The governed proxy could not be reached (or did not answer /gcc/health).

    Raised by :func:`gubernaut_sdk.preflight` and the opt-in preflight in
    :meth:`GccProxy.start`. It exists so a caller can *fail closed on purpose*:
    if the governor is not in front of your traffic, stop — do not send
    ungoverned requests to the upstream API.
    """

    def __init__(self, base_url: str, detail: str = "") -> None:
        self.base_url = base_url
        msg = f"GCC proxy unreachable at {base_url}"
        if detail:
            msg += f" ({detail})"
        msg += " — refusing to proceed ungoverned. Is `gcc-proxy` running?"
        super().__init__(msg)


class GubernautConfigError(GubernautError):
    """A configuration value was missing or malformed."""


__all__ = ["GubernautError", "GubernautConnectionError", "GubernautConfigError"]
