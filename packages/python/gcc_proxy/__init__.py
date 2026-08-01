"""gcc_proxy — Gubernaut Cognitive Controller, drop-in local proxy (Python reference).

Adoption is one line:

    openai.base_url = "http://localhost:8000/v1"

Architecture (see 04_shared_docs/system_overview.md):
  telemetry.appraise()   IGL   text -> Telemetry {intensity, valence, repetition}
  hrl.HomeostaticLoop    HRL   numbers -> Posture (DEFAULT / INHIBIT / REGROUND)
  actuation              EAU-side  posture -> request constraints (directive + temp clamp)
  engine                 stateless deterministic replay over the request's own history

The deciding meta level (HRL) accepts finite floats only — no code path exists
by which text reaches it. No consciousness, sentience, or experience is claimed
or implied; this is a regulation layer: monitored state, regulated output.
"""

from gcc_proxy.hrl import ControllerState, Decision, HomeostaticLoop, Posture, Telemetry
from gcc_proxy.engine import GovernorEngine, EngineResult
from gcc_proxy.config import GCCConfig

__version__ = "1.0.0"

__all__ = [
    "ControllerState",
    "Decision",
    "HomeostaticLoop",
    "Posture",
    "Telemetry",
    "GovernorEngine",
    "EngineResult",
    "GCCConfig",
    "__version__",
]
