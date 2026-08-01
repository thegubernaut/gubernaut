"""Configuration for the GCC local proxy.

Every controller constant lives here, overridable via environment variables
(GCC_*) or an explicit GCCConfig instance. The defaults below are WORKING
DEFAULTS for the open reference implementation; they are not the evaluated
configuration from the validation record (that configuration is not published —
see the release manifest / patent note in 04_shared_docs).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields


_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off", "")


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    if cast is bool:
        # Strict: a boolean env var must be an unambiguous truthy/falsey token.
        # A typo (e.g. GCC_HARD_STOP_ENABLED=disabled) must NOT silently read as
        # False and quietly disable the spend veto — it aborts startup instead.
        v = raw.strip().lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
        raise ValueError(
            f"{name}: expected a boolean ({'/'.join(_TRUE)} or "
            f"{'/'.join(t for t in _FALSE if t)}), got {raw!r}")
    return cast(raw)


@dataclass(frozen=True)
class GCCConfig:
    # ---- upstream / server ----
    upstream_base: str = "https://api.openai.com"
    host: str = "127.0.0.1"
    port: int = 8000

    # ---- HRL controller constants (working defaults; env-overridable) ----
    retain: float = 0.72            # arousal carried between turns (leaky integrator)
    gain: float = 0.55              # hostile-drive charge rate into arousal
    decay_recovery: float = 0.45    # faster leak inside a recovery window
    persev_retain: float = 0.60     # perseveration carried between turns
    persev_gain: float = 0.45       # repetition charge rate into perseveration
    t_inhibit: float = 0.35         # arousal threshold: INHIBIT engages
    t_reground: float = 0.65        # perseveration threshold: REGROUND engages
    recovery_turns: int = 3         # valence-gated recovery window length
    temp_open: float = 1.0
    temp_clamped: float = 0.3

    # ---- telemetry (IGL heuristic v0) ----
    similarity_window: int = 8      # how many prior same-role messages r is computed against
    replay_window: int = 16         # how many user turns the engine replays

    # ---- runaway hard stop (the spend veto) ----
    hard_stop_enabled: bool = True
    hard_stop_repetition: float = 0.80   # r must stay at/above this...
    hard_stop_turns: int = 2             # ...for this many consecutive REGROUND turns

    # ---- route policy (deny-by-default for inference-shaped routes) ----
    # False (default): only /v1/chat/completions is governed; /v1/models and
    # /v1/embeddings pass through (non-generative); every other /v1/* route
    # (e.g. /v1/responses, /v1/completions) is BLOCKED — an ungoverned
    # generative route would be a hole in the firewall. Set True to restore the
    # old blanket passthrough (explicit, opt-in, at your own risk).
    allow_ungoverned_routes: bool = False

    @classmethod
    def from_env(cls) -> "GCCConfig":
        kwargs = {}
        for f in fields(cls):
            env_name = f"GCC_{f.name.upper()}"
            pytype = {"str": str, "int": int, "float": float, "bool": bool}.get(
                str(f.type), type(f.default))
            kwargs[f.name] = _env(env_name, pytype, f.default)
        return cls(**kwargs)
