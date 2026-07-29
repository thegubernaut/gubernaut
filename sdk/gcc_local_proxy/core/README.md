# gcc-core — compiled deciding engine (Rust → Wasm)

Bit-exact port of the Python reference HRL
(`../python/gcc_proxy/hrl.py` + config defaults): same IEEE-754 f64
operations in the same order, proven by the golden-trace parity test.

## Status (2026-07-19): PARITY PROVEN — `cargo test` green, wasm32 builds

Measured 2026-07-19 on rustc 1.97.1, host `x86_64-pc-windows-gnu`
(toolchain at repo `.toolchains/rust/`, installed via rustup, minimal
profile; gnu host chosen because no VS Build Tools exist on this machine —
IEEE-754 f64 results are host-triple-independent, so the parity claim is
unaffected):

- `cargo test`: **6/6 green** — config-drift guard, value-exact replay of
  all 8 scenarios (73 stepwise expectations), all 8 boundary rejections,
  plus 3 inline unit tests.
- `cargo build --release --target wasm32-unknown-unknown`: builds clean
  (`target/wasm32-unknown-unknown/release/gcc_core.wasm`). Bindings/
  packaging (wasm-bindgen) remain a separate later step — no wasm size or
  latency claims yet.

Components:

- `src/lib.rs` — Config / Telemetry (constructor-guarded numeric boundary) /
  HomeostaticLoop / Posture / Decision. `#![deny(unsafe_code)]`, no runtime
  dependencies.
- `tests/golden/traces.jsonl` — 8 scenarios (73 stepwise expectations) + 8
  boundary-rejection cases + the config line, generated from the REAL Python
  controller by `../python/tools/gen_golden_traces.py`. Regenerate there;
  never edit by hand. (The fixtures are vendored into the packaged crate, so
  `cargo test` passes from an extracted `.crate` without the Python source
  tree present; the relative path above refers to the source repo.)
- `tests/golden_parity.rs` — value-exact replay of every step; config-drift
  guard; boundary rejections. The dev-dependency `serde_json` pins the
  `float_roundtrip` feature: its default float parse can land 1 ulp off,
  which a bit-exact contract cannot tolerate (found the hard way — the
  first run flagged `hostile_ramp` step 5 as a miss that was actually the
  test's parser, verified against live Python bit patterns).

Reproduce:

```text
cd core
cargo test                                              # parity + unit tests
cargo build --release --target wasm32-unknown-unknown   # wasm build check
```

Port exit condition (RoadMap Step 1 / P3) is met: parity green + wasm32
builds. Optional later: add the msvc host triple once VS Build Tools are
installed (not required for correctness or the wasm target).
## Citation & license

Licensed under **Apache-2.0** (see `LICENSE`). If you use Gubernaut, please cite
the concept (all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

Byline: Gubernaut Research.
