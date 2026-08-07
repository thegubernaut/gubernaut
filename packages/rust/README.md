# gubernaut-core

**The Gubernaut controller, compiled.** A bit-exact Rust port of the Python reference
controller: the same IEEE-754 f64 operations in the same order, verified by a golden-trace
parity test. No runtime dependencies, `#![deny(unsafe_code)]`, and it compiles to wasm.

```bash
cargo add gubernaut-core
```

Use this when you want the **decision without the proxy**: no network, no HTTP hop, no
Python. Embedding in an edge worker, a gateway, or an agent runtime that already has its
own transport.

The full product, including the OpenAI-compatible proxy, is
[gubernaut](https://github.com/thegubernaut/gubernaut). For JavaScript and TypeScript,
this same wasm is packaged as [`@gubernaut/core`](https://www.npmjs.com/package/@gubernaut/core).

## Renamed from `gcc-core` at 1.0.1

`gcc-core` was unsearchable. Type "gcc" into any developer search and you get the GNU
Compiler Collection, forever; nobody who did not already know this crate existed could find
it. It is now `gubernaut-core`.

crates.io cannot rename a crate, so:

- **`gcc-core` 1.0.0** stays published and is **not yanked**. Anything already depending on
  it keeps building.
- **`gcc-core` 1.0.1** is a deprecation shim that re-exports this crate, so an existing
  dependency can be bumped without a code change.
- The shim is `lib`-only and **cannot forward the `cdylib`/wasm target**: `#[no_mangle]`
  symbols do not re-export. If you consume the wasm, depend on `gubernaut-core` directly.

**The controller did not change.** The compiled wasm is byte-identical across the rename,
SHA256 `834015d7…`, the same binary that passed the 10,000-tick edge soak. The rename moved
one string in `Cargo.toml`; the `#[no_mangle]` ABI symbols are still `gcc_tick` and
`gcc_last_*`, because renaming those would change the binary and break every existing
embedder.

## What it is

| | |
|---|---|
| Input | `Telemetry { intensity, valence, repetition }`, constructor-guarded to finite floats in range |
| Output | `Decision { posture, temperature_max, recovery_window, state }` |
| Postures | `DEFAULT`, `INHIBIT`, `REGROUND` |
| State | `equilibrium`, `arousal`, `perseveration`, `recovery` |

The controller is a pure function. No clock, no randomness, no I/O, no session. The same
history always produces the same posture.

**The numeric boundary is the point.** The constructor accepts finite floats in range and
rejects everything else, so no token sequence can reach the component that decides posture.

## Parity

`cargo test` replays a golden corpus generated from the live Python controller:

- **73 value-exact stepwise expectations** across 8 scenarios.
- **8 boundary-rejection cases.**
- A config-drift guard, so a changed constant fails loudly rather than quietly.

```bash
cargo test
cargo build --release --target wasm32-unknown-unknown
```

The fixtures are vendored into the packaged crate, so `cargo test` passes from an extracted
`.crate` with no Python source present.

**Never hand-edit `tests/golden/traces.jsonl`.** Regenerate it:

```bash
cd ../python && python tools/gen_golden_traces.py
```

One note worth keeping, because it cost a day. The `serde_json` dev-dependency pins the
`float_roundtrip` feature: its default float parse can land 1 ulp off, which a bit-exact
contract cannot tolerate. The first parity run flagged `hostile_ramp` step 5 as a miss that
turned out to be the test's own parser, confirmed against live Python bit patterns.

## On the edge

The identical wasm was soaked for **10,000 ticks bit-exact with zero divergence and flat
memory** in Cloudflare workerd, a Node worker, and Node main.

Timing, with its scope: roughly **125 ns per tick in workerd**, and **200 ns p99** on the
identical wasm in a Node worker. workerd's Spectre-hardened clock precludes an internal
per-tick distribution, so the workerd figure is external-throughput-derived and the
distribution comes from the Node worker.

## Configuration

`Config` defaults match the Python reference and are the values every published figure was
measured with. Change one and the published numbers no longer describe your deployment.

## Citation and license

Licensed under **Apache-2.0**. If you use Gubernaut, please cite the concept
(all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

No consciousness claims. This is a regulation layer, measured and falsifiable.
Byline: Gubernaut Research.
