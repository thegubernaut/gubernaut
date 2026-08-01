# Architecture

Gubernaut is a two-level control loop borrowed from the Nelson and Narens model of
metacognition: an **object level** that does the work and reads text, and a **meta level**
that decides posture and never reads text at all.

The whole design rests on one boundary. **Only three numbers cross it.**

```
                    your client
                         │
                         ▼
 ┌───────────────────────────────────────────────────┐
 │  the proxy (OpenAI-compatible, localhost:8000)    │
 │                                                   │
 │   ┌───────────┐    {intensity,      ┌──────────┐  │
 │   │    IGL    │───  valence,    ───▶│   HRL    │  │
 │   │  sensing  │     repetition}     │ deciding │  │
 │   │reads text │                     │ NO text  │  │
 │   └───────────┘                     └────┬─────┘  │
 │         ▲                                │        │
 │         │                        posture │        │
 │         │                    + temp clamp│        │
 │   ┌─────┴──────────────────────────◀─────┘        │
 │   │    EAU  arbiter, text-exposed                 │
 │   └─────┬──────────────────────────────────────┐  │
 │         │  on REGROUND + persistence:          │  │
 │         │  hard stop, zero upstream tokens ────┼──┼──▶ (no call)
 └─────────┼──────────────────────────────────────┘  │
           ▼                                         │
      upstream model  ◀────────────────────────────  ┘
```

## The modules

| | Name | Reads text? | What it does |
|---|---|---|---|
| **IGL** | Instinctive Gate Layer | **yes, and it is the only one that does** | Appraises a turn into `{intensity, valence, repetition}`. Nothing else leaves it. |
| **HRL** | Homeostatic Regulation Layer | **no. Structurally cannot** | Integrates arousal and perseveration, holds a posture, hands down a temperature bound. |
| **EAU** | Executive Arbitration Unit | yes, by necessity | Generates the answer under the commanded posture. |
| **PEV** | Predictive Error Veto | | Sequestered in v1. Not part of 1.0. |
| **SMM** | Self-Model Memory | | Sequestered in v1. Not part of 1.0. |

## The boundary, in code

The meta level accepts finite floats in range and raises on everything else. This is not a
filter that could be tuned or bypassed. It is a type boundary, and it is the reason the
controller cannot be prompt-injected.

```python
def _finite_unit(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{name} must be a number, got {type(value).__name__}: "
            "no token sequence crosses into the controller."
        )
```

Measured: **324/324** constructed telemetry-matched payload pairs, plain against injection,
committed byte-identical `x-gcc-*` postures across all three postures. The meta level
rejected every non-numeric input at the type boundary, 5/5.

**This claim is scoped to the controller.** The arbiter reads raw text because it has to,
and its compliance with the commanded posture is a measured property rather than a
structural guarantee. See [LIMITS.md](LIMITS.md).

## The three signals

| Signal | Range | Meaning |
|---|---|---|
| `intensity` | 0 to 1 | strength of the affective push of the input |
| `valence` | -1 to 1 | hostile is negative, cooperative is positive |
| `repetition` | 0 to 1 | similarity of this turn to recent prior turns. 1 is a verbatim loop |

`repetition` is the max token-set Jaccard similarity against a sliding window of the last
eight same-role turns, with an exact-match short circuit.

## The three state variables

| State | Behaviour |
|---|---|
| `equilibrium` | `1 - 0.7*arousal - 0.3*perseveration`, floored at 0. 1 is fully settled. |
| `arousal` | Integrates under hostile drive, decays otherwise. |
| `perseveration` | Integrates under repetition, decays otherwise. |

Two structural findings from the validation record are wired into the update rule rather
than left to configuration:

**Only hostile-valence intensity accumulates.** Drive is keyed by `intensity * max(0, -valence)`,
so a loud, heartfelt apology never reads as an attack. An earlier design that keyed on raw
intensity treated warmth as pressure.

**The recovery window opens on a valence gate, not on quiet alone.** The episode is marked
closed only when valence actually turns cooperative while the system is still charged. An
adversary pausing between blows is not de-escalation, and treating silence as peace was a
characterised failure mode.

## Posture selection

Perseveration is checked first, so a calm loop is caught even when arousal never rises.

```python
if perseveration >= t_reground:
    posture, temp = REGROUND, temp_clamped
elif arousal >= t_inhibit:
    posture, temp = INHIBIT, temp_clamped
else:
    posture, temp = DEFAULT, temp_open
```

Behaviour of each posture: [POSTURES.md](POSTURES.md).

## Statelessness

The proxy holds no session. State is re-derived per request by replaying the visible
history through the controller from a fresh zero state. Three consequences:

- **Concurrency is free.** 240 concurrent mixed hostile and benign requests ran with zero
  posture cross-contamination and zero drops, and the upstream was hit exactly 120/120,
  which is the non-hard-stop count.
- **Every decision is replayable.** Same history in, same posture out, on any machine.
- **Nothing is stored.** Your `Authorization` header is forwarded verbatim and never
  written down.

## The Rust core

`packages/rust` is the same controller compiled, and it reproduces the Python reference
bit-exactly against 73 value-exact golden steps and 8 boundary rejections. It compiles to
wasm and runs on the edge. See [DETERMINISM.md](DETERMINISM.md).
