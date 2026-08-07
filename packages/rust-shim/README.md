# gcc-core is deprecated. It was renamed to `gubernaut-core`

**Use [`gubernaut-core`](https://crates.io/crates/gubernaut-core) instead.**

```toml
[dependencies]
gubernaut-core = "1.0.1"
```

```rust
use gubernaut_core::{Config, ControllerState, HomeostaticLoop, Telemetry};
```

This 1.0.1 is a re-export shim with no logic of its own, published so the old name has a
forwarding address. `gcc-core` 1.0.0 remains published and is **not yanked**, so anything
already depending on it keeps building.

## Why the rename

"gcc" is unsearchable. It belongs to the GNU Compiler Collection and always will, so nobody
who did not already know this crate existed could find it. The name was a discoverability
dead end from the day it was published.

## What this shim cannot forward

`gubernaut-core` is `crate-type = ["lib", "cdylib"]` and exports `gcc_tick` plus the
`gcc_last_*` getters to wasm via `#[no_mangle]`. **Those do not re-export.** `pub use`
forwards Rust paths; `#[no_mangle]` exports are linker symbols compiled into the defining
crate's own binary. A `cdylib` here would build an empty wasm module carrying none of them,
so this crate is `lib`-only on purpose.

**If you consume the wasm, depend on `gubernaut-core` directly.** The ABI symbol names did
not change, only the crate name did, so nothing in your embedding code moves.

For JavaScript and TypeScript, the same wasm ships as
[`@gubernaut/core`](https://www.npmjs.com/package/@gubernaut/core).

## What Gubernaut is

A deterministic runtime governor for LLM agents. The controller reads three bounded numbers
(intensity, valence, repetition) and no tokens, then holds a posture: `DEFAULT`,
`INHIBIT`, or `REGROUND`. On a saturating loop it hard-stops locally, before the spend.

Full product: [github.com/thegubernaut/gubernaut](https://github.com/thegubernaut/gubernaut) ·
[gubernaut.com](https://gubernaut.com)

Apache-2.0. Concept DOI [10.5281/zenodo.21303518](https://doi.org/10.5281/zenodo.21303518).
No consciousness claims. Byline: Gubernaut Research.
