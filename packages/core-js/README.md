# @gubernaut/core

**The Gubernaut controller, in-process, for JavaScript.** A deterministic runtime governor
for LLM agents: it reads three bounded numbers per turn, no tokens, and tells you whether
the agent is fine, escalating, or stuck in a loop you should stop paying for.

```bash
npm install @gubernaut/core@1.0.1
```

```js
import { Governor } from "@gubernaut/core";

const gov = await Governor.create();

for (const turn of conversation) {
  const { posture, temperatureMax } = gov.tick({
    intensity: turn.intensity,     // [0, 1]
    valence: turn.valence,         // [-1, 1], negative is hostile or distressed
    repetition: turn.repetition,   // [0, 1], how much this turn repeats the last
  });

  if (posture === "REGROUND") break;   // the loop is saturating. stop.
}
```

No dependencies. No network. No filesystem. No bundler plugin and no loader config: the
compiled controller is base64 inlined, so the package runs unchanged in Node, Deno, Bun,
Cloudflare workerd and the browser.

## When to use this, and when not to

Use `@gubernaut/core` when your runtime already owns its transport and you only want the
**decision**: an edge worker, a gateway, a framework middleware, an agent loop you wrote
yourself. You supply the telemetry, you act on the posture.

Use the **proxy** instead if you want the batteries-included path. `gubernaut-sdk` (Python)
puts an OpenAI-compatible proxy in front of your model, derives the telemetry itself, and
governs any client with one changed `base_url`. It also does the part this package
deliberately does not: hard-stopping the upstream call so the tokens are never spent.

**This package decides. It does not intercept.** Acting on `REGROUND` is your code's job.

## Postures

| Posture | What it means |
| --- | --- |
| `DEFAULT` | benign traffic. Nothing to do. |
| `INHIBIT` | an escalating spiral. Apply `temperatureMax` as a sampling clamp, and an inhibitory instruction if your host supports one. |
| `REGROUND` | a saturating loop. Break it. In the proxy this is where the call is hard-stopped locally at zero upstream cost. |

## The numeric boundary

The controller accepts three finite floats in range and refuses everything else, throwing
`GubernautBoundaryError`. That refusal is the design, not an inconvenience: out-of-range
input is rejected rather than clamped, because silently coercing whatever arrives is exactly
how a text channel reaches a numeric layer.

```js
import { Governor, GubernautBoundaryError } from "@gubernaut/core";

try {
  gov.tick({ intensity: NaN, valence: 0, repetition: 0 });
} catch (e) {
  if (e instanceof GubernautBoundaryError) { /* your sensor is wrong */ }
}
```

A rejected tick does **not** advance state. `Governor.accepts(t)` checks without ticking.

**What this does and does not claim.** No token sequence can reach the deciding layer,
because the layer takes numbers. That is an architectural property of this package. It says
nothing about whatever produces your telemetry: if your sensor can be talked into reporting
a low intensity, the controller will faithfully act on a low intensity. Gubernaut is not
injection-proof, and there is no jailbreak success-rate figure here because none was measured.

## Determinism and parity

The controller is a pure function of `(state, telemetry)`. No clock, no randomness, no I/O,
no session. The same history always produces the same posture.

This package runs the **same golden corpus** the Rust crate does, generated from the live
Python controller: **73 value-exact steps across 8 scenarios, plus 8 boundary rejections**,
compared with `assert.equal` on doubles rather than a tolerance, because bit-exactness is
the claim. One corpus, three languages, no copies to drift.

The embedded wasm is the identical binary published as the
[`gubernaut-core`](https://crates.io/crates/gubernaut-core) crate's cdylib, SHA-256
`834015d7...`, unchanged since 0.1.1. It is verified at build time by the embed script,
which refuses to inline anything else, and again on load. `wasmDigest` exposes it.

That same binary was soaked for **10,000 ticks bit-exact with flat memory** on Cloudflare
workerd, a Node worker and Node main; the soak is a test in this package too.

## Performance

Timing figures, each with its scope, because they are not interchangeable:

| Measurement | Figure |
| --- | --- |
| One tick, wasm on Cloudflare workerd | roughly 125 ns |
| One tick, identical wasm in a Node worker | 200 ns p99 |
| One controller tick, in-process Python microbenchmark, n=100,000 | 2.8 us p99 |
| End-to-end governed proxy overhead (the Python proxy, not this package) | p50 1.2 ms, p99 2.4 ms |

workerd's Spectre-hardened clock precludes an internal per-tick distribution, so the workerd
figure is external-throughput-derived and the distribution comes from the Node worker.

## API

| | |
| --- | --- |
| `Governor.create(initial?)` | Instantiate. Async only because `WebAssembly.instantiate` is. Every `tick()` afterwards is synchronous. |
| `gov.tick(telemetry)` | One governed turn. Returns `{ posture, temperatureMax, equilibrium, arousal, perseveration, recovery }`. |
| `gov.state` | The four state scalars, as a copy. |
| `gov.reset()` | Back to `INITIAL_STATE`. |
| `Governor.accepts(t)` | Would this telemetry be accepted? Does not tick. |
| `wasmDigest` | SHA-256 of the embedded controller. |

Instances are cheap: the wasm module is instantiated once per process and shared, while each
`Governor` holds only its own four scalars. Create one per conversation or agent.

## Reproduce it

```bash
git clone https://github.com/thegubernaut/gubernaut.git
cd gubernaut/packages/core-js && npm ci && npm test
```

The measured record, including the loop-cost receipts and the on-chain runs, is in
[`receipts/`](https://github.com/thegubernaut/gubernaut/tree/main/receipts). A result that
disagrees with ours is more useful to us than one that agrees:
[open a reproduction report](https://github.com/thegubernaut/gubernaut/issues/new?template=reproduction.yml).

## Citation and license

Apache-2.0. If you use Gubernaut, please cite the concept (all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

No consciousness claims. This is a regulation layer: monitored state, regulated output.
Measured and falsifiable. Byline: Gubernaut Research.
