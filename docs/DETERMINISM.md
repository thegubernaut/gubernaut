# Determinism

Gubernaut's central engineering property is that **the same history always produces the
same posture**, on any machine, in any language, at any time. Everything else in this
project rests on it: the receipts are reproducible because of it, the paper is
recomputable because of it, and you can audit a decision months later because of it.

## Why it holds

The controller is a pure function. `update(state, telemetry) -> decision`, no clock, no
randomness, no I/O, no network, no accumulated session.

The proxy holds no session either. On each request it replays the visible history from a
fresh zero state and re-derives the posture. There is nothing to drift, nothing to warm up,
and nothing to reset.

## Cross-language parity

`packages/rust` reproduces `packages/python` **bit-exactly**. Not approximately, not within
a tolerance. The same floating-point values.

That is enforced by a golden-trace corpus checked in CI:

- **73 value-exact golden steps.** Every field of every decision compared.
- **8 boundary rejections.** Inputs the controller must refuse.

```bash
cd packages/rust && cargo test
```

The traces live at `packages/rust/tests/golden/traces.jsonl` and are **generated, never
hand-edited**:

```bash
cd packages/python && python tools/gen_golden_traces.py
```

That writes into the Rust crate's test fixtures. If a change to the Python controller is
real, the traces change and the Rust side fails until it is updated to match. If the traces
change and you did not intend them to, you have found a regression.

## The wasm soak

The same Rust core compiles to `wasm32` and was soaked for **10,000 ticks bit-exact with
zero divergence and flat memory** in three runtimes: Cloudflare workerd, a Node worker, and
Node main.

Bit-exact across three runtimes is the claim that matters. Flat memory over 10,000 ticks
says there is no accumulator quietly growing inside the loop.

Edge timing, with its scope attached: roughly **125 ns per tick in workerd**, with **200 ns
p99** on the identical wasm in a Node worker. workerd's Spectre-hardened clock precludes an
internal per-tick distribution, so the workerd figure is derived from external throughput
and the distribution comes from the Node worker.

## What this buys you

**Audit.** A posture from six months ago can be re-derived from the transcript. There is no
"the model was in a different mood" and no hidden state to explain.

**Testing.** You can assert on postures in your own test suite without mocking, flaking or
recording. Same input, same output, every run.

**Reproduction.** The measured hard stop lands at turn 4 in every run and the first posture
change at turn 3, identical across runs, because there is nothing in the controller that
could make it otherwise. That is why [REPRODUCE.md](REPRODUCE.md) can promise you the same
numbers rather than similar ones.

## What is not deterministic

**The upstream model.** Gubernaut governs it and does not replace it. Given the same
posture and the same clamp, the model may still answer differently on two calls, and every
end-to-end dollar figure carries the sampling variance of the thing being governed.

**The sensor, across versions.** The v0 lexicon appraiser is deterministic for a fixed
version, and changing the lexicon changes the telemetry, which changes the postures. Pin
your version if you are comparing runs.

**Anything measured against a live upstream.** The real-upstream soak in `bench/soak_real.py`
talks to a real API over a real network. It carries the variance and it says so.
