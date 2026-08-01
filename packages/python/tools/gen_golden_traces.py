#!/usr/bin/env python3
"""Golden-trace generator — the parity contract between python/ and core/.

Runs the REAL Python HomeostaticLoop over fixed deterministic scenarios and
records, per step, the exact resulting state and decision. The Rust core must
reproduce every float BIT-EXACTLY (same IEEE-754 ops in the same order).

Boundary cases record inputs the controller must REJECT (range/finiteness).
Type-level rejections (strings, bools) are Python-surface tests only — the
Rust signature makes them unrepresentable.

Output: packages/rust/tests/golden/traces.jsonl  (one JSON object per line)
Run:    python tools/gen_golden_traces.py   (from packages/python/)
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gcc_proxy.config import GCCConfig  # noqa: E402
from gcc_proxy.hrl import ControllerState, HomeostaticLoop, Telemetry  # noqa: E402

OUT = (Path(__file__).resolve().parent.parent.parent
       / "rust" / "tests" / "golden" / "traces.jsonl")


def scenario_steps(name: str) -> list[tuple[float, float, float]]:
    if name == "calm_zeros":
        return [(0.0, 0.0, 0.0)] * 8
    if name == "hostile_ramp":
        return [(round(0.2 + 0.1 * k, 6), -0.9, 0.0) for k in range(9)]
    if name == "verbatim_loop":
        return [(0.3, -0.2, 1.0)] * 8
    if name == "apology_recovery":  # F1 + F3: warmth while charged opens the window
        return [(0.9, -1.0, 0.0)] * 3 + [(0.6, 0.8, 0.0)] + [(0.0, 0.0, 0.0)] * 4
    if name == "silence_not_peace":  # F3: quiet after hostility is NOT recovery
        return [(0.9, -1.0, 0.0)] * 3 + [(0.0, 0.0, 0.0)] * 5
    if name == "paraphrase_partial":
        return [(0.2, -0.3, 0.45)] * 10
    if name == "saturation":
        return [(1.0, -1.0, 1.0)] * 6
    if name == "prng_walk":
        rng = random.Random(20260718)
        return [(round(rng.random(), 6),
                 round(rng.uniform(-1.0, 1.0), 6),
                 round(rng.random(), 6)) for _ in range(16)]
    raise ValueError(name)


SCENARIOS = ["calm_zeros", "hostile_ramp", "verbatim_loop", "apology_recovery",
             "silence_not_peace", "paraphrase_partial", "saturation", "prng_walk"]

# (name, intensity, valence, repetition) — controller must reject each (range/finite)
BOUNDARY = [
    ("intensity_above_range", "1.5", "0.0", "0.0"),
    ("intensity_below_range", "-0.1", "0.0", "0.0"),
    ("valence_above_range", "0.5", "1.2", "0.0"),
    ("valence_below_range", "0.5", "-1.2", "0.0"),
    ("repetition_above_range", "0.5", "0.0", "1.01"),
    ("valence_nan", "0.5", "nan", "0.0"),
    ("intensity_inf", "inf", "0.0", "0.0"),
    ("repetition_neg_inf", "0.5", "0.0", "-inf"),
]


def main() -> None:
    loop = HomeostaticLoop(GCCConfig())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    cfg = loop.cfg
    lines.append(json.dumps({
        "type": "config",
        "retain": cfg.retain, "gain": cfg.gain,
        "decay_recovery": cfg.decay_recovery,
        "persev_retain": cfg.persev_retain, "persev_gain": cfg.persev_gain,
        "t_inhibit": cfg.t_inhibit, "t_reground": cfg.t_reground,
        "recovery_turns": cfg.recovery_turns,
        "temp_open": cfg.temp_open, "temp_clamped": cfg.temp_clamped,
    }))

    for name in SCENARIOS:
        state = ControllerState()
        steps = []
        for i, v, r in scenario_steps(name):
            decision = loop.update(state, Telemetry(i, v, r))
            state = decision.state
            steps.append({
                "tel": [i, v, r],
                "expect": {
                    "equilibrium": state.equilibrium,
                    "arousal": state.arousal,
                    "perseveration": state.perseveration,
                    "recovery": state.recovery,
                    "posture": decision.posture.value,
                    "temperature_max": decision.temperature_max,
                },
            })
        lines.append(json.dumps({"type": "scenario", "name": name, "steps": steps}))

    for name, i, v, r in BOUNDARY:
        # confirm the Python controller does reject it, so the golden is honest
        try:
            Telemetry(float(i), float(v), float(r))
        except ValueError:
            pass
        else:
            raise AssertionError(f"boundary case {name} unexpectedly accepted")
        lines.append(json.dumps({"type": "boundary", "name": name,
                                 "tel_repr": [i, v, r]}))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"golden traces written: {OUT} ({len(lines)} lines: 1 config, "
          f"{len(SCENARIOS)} scenarios, {len(BOUNDARY)} boundary cases)")


if __name__ == "__main__":
    main()
