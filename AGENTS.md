# AGENTS.md

Instructions for AI coding agents working in this repository. Humans: [CONTRIBUTING.md](CONTRIBUTING.md)
says the same at more length.

## What this is

Gubernaut stops an LLM agent stuck in a loop before the next call is billed. One deterministic
controller reads three numbers per turn (intensity, valence, repetition) and returns a posture
(`DEFAULT`, `INHIBIT`, `REGROUND`). It ships as two products:

- **Tiller** (`packages/python`, PyPI `gubernaut-sdk`): an OpenAI-compatible proxy that hard-stops a
  looping call. The reference implementation.
- **Keel** (`packages/rust` → `gubernaut-core`, compiled to wasm for `packages/core-js` →
  `@gubernaut/core`): the same controller in-process.

`packages/node` is the ElizaOS plugin (`@gubernaut/plugin-gcc`), a client of Tiller.
`packages/rust-shim` is the `gcc-core` deprecation shim. `receipts/` and `bench/` are evidence.

## Commands

```bash
# Python (3.10+)
cd packages/python && pip install -e ".[dev]" && python -m pytest tests -q && ruff check .
# Rust
cd packages/rust && cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check
# JavaScript (tests need Node 22.6+; the published package supports Node 18+)
cd packages/core-js && npm ci && npm run build && npm test && npm run typecheck
cd packages/node && npm ci && npm run build && npm test && npm run typecheck
# The claims gate, on any change to prose
python tools/claims_check.py
# See the stop, no key
python examples/hard_stop_demo.py
```

## Rules that fail review

1. **The controller is a pure function.** No clock, randomness, I/O, network or session state in
   `HomeostaticLoop.update`. The proxy stays stateless and rebuilds state from the visible history.
2. **Only three finite floats cross into the controller.** Never pass text, never loosen the type
   boundary. Need more signal? Widen the sensor, keep the interface numeric.
3. **Controller change ⇒ regenerate the golden traces** (`cd packages/python && python
   tools/gen_golden_traces.py`, then `cargo test`). Python and Rust must agree bit-exactly. Never
   hand-edit `packages/rust/tests/golden/traces.jsonl`.
4. **Keel's wasm is pinned.** CI rebuilds it with rustc 1.97.1 and compares the bytes `@gubernaut/core`
   embeds. A different compiler builds different bytes, which `embed_wasm.mjs` refuses.
5. **Every number is a script output** and travels with its qualifier. Never round up, never say
   "all", never invent a user count, review, logo or star count. `tools/claims_check.py` enforces the
   mechanical part from `.github/claims.json`; run it before committing prose.
6. **Do not edit `receipts/`.** It is the measured record. Add a new run; never rewrite an old one.
7. **Fail closed.** The proxy never forwards a call it could not govern. Keep it that way.
8. **Install commands in prose are unpinned** (`pip install gubernaut-sdk`, not `==1.0.1`).

## Where things are

| Path | What |
| --- | --- |
| `packages/python/gcc_proxy/` | proxy, engine, controller (`hrl.py`), sensor (`telemetry.py`), config |
| `packages/python/gubernaut_sdk/` | the public Python facade: `launch_proxy`, framework helpers, header names |
| `docs/` | configuration reference, architecture, postures, determinism, limits, reproduction, FAQ |
| `examples/` | one demo per framework, plus `hard_stop_demo.py` |
| `skills/gubernaut/` | the skill that teaches agents to add Gubernaut to a user's project |
| `.claude-plugin/` | makes this repository a Claude Code plugin marketplace that installs that skill |
| `.github/claims.json` | the claims register the gate enforces |

## Pull requests

One concern each. Tests for behaviour changes. Say why, not only what. Releases and publishing are
done by the maintainer, never by an agent.
