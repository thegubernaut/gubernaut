//! **`gcc-core` is deprecated. It was renamed to
//! [`gubernaut-core`](https://crates.io/crates/gubernaut-core).**
//!
//! This crate is a re-export shim and contains no logic of its own. Everything below is
//! `gubernaut-core`, unchanged. Switch your dependency when convenient:
//!
//! ```toml
//! [dependencies]
//! gubernaut-core = "1.0.1"
//! ```
//!
//! ```rust
//! use gubernaut_core::{Config, HomeostaticLoop, Telemetry};
//! ```
//!
//! # Why
//!
//! "gcc" is unsearchable. It belongs to the GNU Compiler Collection and always will, so
//! nobody who did not already know this crate existed could find it.
//!
//! # What this shim cannot do
//!
//! The real crate is `crate-type = ["lib", "cdylib"]` and exports `gcc_tick` and the
//! `gcc_last_*` getters to wasm through `#[no_mangle]`. **Those cannot be forwarded.**
//! `pub use` re-exports Rust paths; `#[no_mangle]` exports are linker symbols compiled into
//! the defining crate's own binary. A `cdylib` here would produce an empty wasm module with
//! none of them, which is worse than offering nothing — so this crate is `lib`-only.
//!
//! **If you consume the wasm, depend on `gubernaut-core` directly.** The ABI symbol names
//! are unchanged there; only the crate name moved.
//!
//! `gcc-core` 1.0.0 remains published and is not yanked.

#![deny(unsafe_code)]

pub use gubernaut_core::*;
