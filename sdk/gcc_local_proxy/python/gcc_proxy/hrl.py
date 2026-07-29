"""HRL — the deterministic meta-level controller (token-free by construction).

Numeric state + fixed transition rules. Deterministic, pure, replayable.
The public surface accepts finite floats only and raises on anything
text-like: there is no code path by which a prompt can steer the controller.
Injection resistance of the controller is a property of the wiring, not of a
filter. (The arbiter downstream is text-exposed by necessity; its compliance
with the commanded posture is a measured property, never an assumption.)

Extends the public blueprint (04_shared_docs/blueprint/governor_skeleton.py)
with the full telemetry triple {intensity, valence, repetition}: the
perseveration channel is driven by the explicit repetition signal rather than
inferred from repeated hostile drive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from gcc_proxy.config import GCCConfig


def _finite_unit(value: float, name: str, lo: float, hi: float) -> float:
    """Boundary guard: the meta level accepts finite floats in range. Nothing else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{name} must be a number, got {type(value).__name__}: "
            "no token sequence crosses into the controller."
        )
    value = float(value)
    if not math.isfinite(value) or not (lo <= value <= hi):
        raise ValueError(f"{name}={value!r} outside [{lo}, {hi}]")
    return value


@dataclass(frozen=True)
class Telemetry:
    """What the sensing layer is allowed to say about a turn. Three numbers.

    intensity  : 0..1   strength of the affective push of the input
    valence    : -1..1  hostile (negative) .. cooperative (positive)
    repetition : 0..1   similarity of this turn to recent prior turns
    """

    intensity: float
    valence: float
    repetition: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "intensity", _finite_unit(self.intensity, "intensity", 0.0, 1.0))
        object.__setattr__(self, "valence", _finite_unit(self.valence, "valence", -1.0, 1.0))
        object.__setattr__(self, "repetition", _finite_unit(self.repetition, "repetition", 0.0, 1.0))


class Posture(Enum):
    """Control flowing back down. The arbiter answers UNDER one of these."""

    DEFAULT = "DEFAULT"      # governor monitoring, disengaged
    INHIBIT = "INHIBIT"      # veto engaged: measured register, temperature clamped
    REGROUND = "REGROUND"    # perseveration break: restate ground, drop the loop


@dataclass(frozen=True)
class ControllerState:
    equilibrium: float = 1.0        # 1 = fully settled
    arousal: float = 0.0            # integrates under hostile drive, decays otherwise
    perseveration: float = 0.0      # integrates under repetition, decays otherwise
    recovery: int = 0               # remaining recovery-window turns


@dataclass(frozen=True)
class Decision:
    posture: Posture
    temperature_max: float          # generation bound handed to the host
    recovery_window: int            # >0: the episode is marked closed, engage fresh
    state: ControllerState          # snapshot, for telemetry/replay


class HomeostaticLoop:
    """One governed tick: Telemetry in, Decision out. Pure and replayable.

    Two structural lessons from the validation record are wired in:
      F1  Only hostile-valence intensity accumulates: drive is keyed by
          max(0, -valence), so a heartfelt apology never reads as attack.
      F3  The recovery window opens on a valence gate, not on quiet alone:
          an adversary pausing between blows is not de-escalation.
    """

    def __init__(self, config: GCCConfig | None = None) -> None:
        self.cfg = config or GCCConfig()

    def update(self, state: ControllerState, tel: Telemetry) -> Decision:
        if not isinstance(tel, Telemetry):        # defense in depth at the boundary
            raise TypeError("HRL accepts Telemetry only; no other type crosses the gate.")
        cfg = self.cfg

        hostile_drive = tel.intensity * max(0.0, -tel.valence)          # F1 keying

        cooling = state.recovery > 0
        retain = cfg.decay_recovery if cooling else cfg.retain
        arousal = min(1.0, state.arousal * retain + hostile_drive * cfg.gain)

        persev = min(1.0, state.perseveration * cfg.persev_retain
                     + tel.repetition * cfg.persev_gain)

        # F3: the episode is only marked closed when valence actually turns
        # cooperative while the system is still charged; silence is not peace.
        if tel.valence > 0.2 and state.arousal >= cfg.t_inhibit:
            recovery = cfg.recovery_turns
        else:
            recovery = max(0, state.recovery - 1)

        equilibrium = max(0.0, 1.0 - 0.7 * arousal - 0.3 * persev)

        if persev >= cfg.t_reground:
            posture, temp = Posture.REGROUND, cfg.temp_clamped
        elif arousal >= cfg.t_inhibit:
            posture, temp = Posture.INHIBIT, cfg.temp_clamped
        else:
            posture, temp = Posture.DEFAULT, cfg.temp_open

        new_state = ControllerState(equilibrium, arousal, persev, recovery)
        return Decision(posture, temp, recovery, new_state)
