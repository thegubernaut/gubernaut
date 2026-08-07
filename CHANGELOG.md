# Changelog

Notable changes to Gubernaut. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Published versions are immutable. A defect in a released version is corrected by shipping
the next one, never by rewriting a published artifact.

## [1.0.1-sync] - 2026-08-07

The three registries had drifted apart. PyPI was at 1.0.1; crates.io and npm were still at
1.0.0, because 1.0.1 was a Python-only documentation fix and the other two are versioned
independently. This release brings every registry to 1.0.1, renames the Rust crate to
something a person can find, and adds a fourth package.

**The controller did not change.** The compiled wasm is byte-identical, SHA-256
`834015d7…`, unchanged since 0.1.1 and unchanged across the rename. Every published figure
still describes the binary that ships.

`gubernaut-sdk` stays at **1.0.1** and was not republished. It was already correct, and
PyPI versions are immutable, so touching it would have meant 1.0.2 and an immediate
re-desync of the versions this release exists to align.

### Changed

- **The Rust crate is now `gubernaut-core`.** `gcc-core` was a discoverability dead end
  from the day it was published: type "gcc" into any developer search and you get the GNU
  Compiler Collection, forever. Nobody who did not already know the crate existed could
  find it.

  crates.io has no rename, so this is a new crate and the old name is handled deliberately
  rather than abandoned. See *Deprecated* below.

  The `#[no_mangle]` ABI symbols are **not** renamed. They are still `gcc_tick` and
  `gcc_last_*`, because renaming them would change the compiled bytes and break every
  existing wasm embedder to fix a string nobody types.

  Method note, since "byte-identical" is easy to assert and easy to get wrong: the wasm was
  built **before** the rename first, to establish that this toolchain reproduces the shipped
  1.0.0 artifact at all. It does, exactly. Only then was the crate renamed and rebuilt, and
  the digest compared against that control rather than against a claim. Without the control
  build, a match would not have distinguished "the rename is neutral" from "the toolchain
  happens to produce this".

- **`@gubernaut/plugin-gcc` is 1.0.1**, with `gubernautPlugin` and `callGubernaut` exported
  alongside the existing `gccPlugin` and `callGcc`. Aliases, not replacements: the 1.0.0
  names keep working indefinitely. The tests assert *identity* rather than equivalence, so
  the aliases cannot quietly become a second implementation that drifts, and CI now checks
  both name sets against the built `dist/` for ESM and CJS, because an alias that exists in
  source and not in the build passes every test and still ships broken.

- The documented CLI is now `gubernaut-proxy`. This is not new: `pyproject.toml` has
  installed both `gubernaut-proxy` and `gcc-proxy` entry points since 1.0.0, so this is a
  documentation change with no packaging change behind it. `gcc-proxy` still works.

### Added

- **`@gubernaut/core`**, the controller in-process for JavaScript. The same wasm the
  `gubernaut-core` crate produces, base64 inlined, with a typed API over the scalar ABI.
  No dependencies, no network, no filesystem, no bundler plugin and no loader config, so it
  runs unchanged in Node, Deno, Bun, Cloudflare workerd and the browser.

  It reuses the **existing** golden corpus rather than shipping its own:
  `packages/rust/tests/golden/traces.jsonl`, generated from the live Python controller, now
  gates three languages. **73 value-exact steps across 8 scenarios and 8 boundary
  rejections**, compared with `assert.equal` on doubles rather than a tolerance, because
  bit-exactness is the claim and a tolerance would dissolve it. Copying the corpus into the
  package would have let the copies drift, and a drifted parity fixture is worse than none:
  it passes while the thing it pins has moved.

  The 10,000-tick soak is a test in the package too, and `tools/embed_wasm.mjs` refuses to
  inline any wasm whose digest is not the verified one, so a changed controller cannot
  arrive silently through the embed step.

  Scope worth stating plainly: **this package decides, it does not intercept.** Acting on
  `REGROUND` is the caller's job. Hard-stopping the upstream call before the tokens are
  spent is what the proxy in `gubernaut-sdk` does.

### Deprecated

- **`gcc-core`.** Version 1.0.0 stays published and is **not yanked**, so anything already
  depending on it keeps building. Version 1.0.1 is a re-export shim
  (`packages/rust-shim/`) that forwards to `gubernaut-core`, so an existing dependency can
  be bumped without a code change.

  The shim is `lib`-only, and this is a real limitation rather than an oversight: the wasm
  exports are `#[no_mangle]` linker symbols compiled into the defining crate's own binary,
  and `pub use` forwards Rust paths, not symbols. A `cdylib` in the shim would build an
  empty wasm module carrying none of `gcc_tick` or the getters, which is worse than
  offering nothing. **wasm consumers must depend on `gubernaut-core` directly.**

  Its test imports through the *old* path and asserts an actual decision plus the numeric
  boundary, rather than asserting that the crate compiles. A shim that builds but re-exports
  nothing useful looks green in CI and breaks on the first real dependent.

### Fixed

- **The front page advertised a version we no longer shipped.** `README.md` told every
  reader `pip install gubernaut-sdk==1.0.0` while PyPI, gubernaut.com and this file all read
  1.0.1. It had been wrong since the 1.0.1 release four days earlier. Every gate was green,
  CI was green, and the claims gate scanned the file and found nothing, because it had no
  concept of a version.

  A pinned install command is a promise a reader executes verbatim, which makes it a claim
  like any number in this repository. `claims_check.py` now reads each package's own
  manifest and fails any install form that disagrees with it. It matches install **forms**
  only, never bare mentions, so "gcc-core 1.0.0 stays published and is not yanked" remains
  sayable while `cargo add gcc-core@1.0.0` does not. The self-test cases read the live
  manifests, so they will not need editing on the next bump, and they cover both the
  must-fire and the must-stay-silent direction.

  The same defect existed in the Rust and Node install rows and in the issue template.

## [1.0.1] - 2026-08-03

**Documentation only. No behaviour changed, and no controller constant moved.** The
published quickstart did not run, in three separate ways, each of which fails silently or
with an error that does not name its cause. All three were found by executing the snippet
against the released 1.0.0 wheel in a clean virtual environment rather than by reading it.

Every worked integration under `examples/` was already correct. Only the copy-paste path
in the READMEs was broken, which is the path a new reader takes first.

### Fixed

- **`launch_proxy(upstream=...)` binds an ephemeral port.** `GccProxy.__init__` defaults
  to `port=0`; the observed bind was 65252, while the following line in the quickstart told
  the reader to point a client at `:8000`. The result is a connection refused on the most
  copied string in the documentation. Pass `port=8000` explicitly, or read `proxy.base_url`
  back. Both forms are now shown and the behaviour is stated rather than implied.
- **The module-level `openai.base_url` attribute needs a trailing slash.** Without one,
  openai 2.52.1 builds a request to `/v1chat/completions` and the proxy correctly returns
  404. Setting `base_url` on the client object works with or without the slash, so that is
  now the form every document shows.
- **`resp.headers.get("x-gcc-posture")` raises `AttributeError`.** A plain `create()`
  returns a parsed `ChatCompletion`, which carries no headers; reading the posture requires
  `with_raw_response`. This was the "verify it works" line, so the one step whose entire
  purpose is proving the governor sits in the request path was the step most certain to
  crash.

### Changed

- Model identifiers in copied samples moved from `gpt-4o-mini` to a model from the measured
  record. The `GCC_MODEL_*` runtime defaults in the node package are untouched, because
  those are configuration rather than documentation.
- `gcc_proxy`'s module docstring no longer presents a bare `openai.base_url` assignment as
  the whole of adoption. A proxy has to be listening first, and the docstring now says so.

### Note

Version 1.0.0 remains on PyPI and is not withdrawn. Published versions are immutable, and
the defects above are in its documentation rather than its behaviour: a reader who wires
the proxy correctly gets the same governed request path from either release.

## [Unreleased]

### Changed
- **Repository restructured.** `sdk/gcc_local_proxy/{python,core}` and
  `sdk/eliza_gcc_plugin` became `packages/{python,rust,node}`, `wrappers/` became
  `examples/`, and `bench/` moved to the root. The previous layout mirrored the internal
  development sandboxes rather than the way anyone installs the software. History was moved
  with `git mv` and is intact.
- `packages/node/package.json` `repository.directory` corrected to `packages/node`.
  **npm metadata for a published version cannot be rewritten**, so the Repository link on
  `@gubernaut/plugin-gcc@1.0.0` still points at the old path and will resolve correctly
  from the next publish onward.
- `gen_golden_traces.py` output path follows the crate to `packages/rust`.

### Fixed
- **The README stated the flagship ungoverned spend as `$0.1670`. The scored value is
  `$0.1669`** and the rule is never to round up. Corrected in `README.md` and
  `receipts/SHOW_HN.md`.
- The receipts range was described as "a single-digit-to-low-twenties percentage", which
  overshoots the measured ceiling. It reads **4.1% to 20.2%**, verbatim.

### Added
- **`receipts/onchain/`.** The local-devnet run published for the first time: a runaway
  on-chain retry loop severed at turn 4, with real transaction hashes, gas receipts and the
  sever bracket. 3 governed transactions against 8 ungoverned in the intercept run, 72
  against 960 across 24 agents in the treasury run, and 210 concurrent agents all severed
  with 0 drops. Reproduction scripts included, with the hardcoded local interpreter path
  replaced by `GCC_PYTHON` so they run outside the machine that produced them.
- **`receipts/engineering/`.** The SDK evidence corpus, previously unpublished: the 5,037
  and 10,000 tick wasm soaks (bit-exact, flat memory), the three scoped latency figures,
  the 240-way concurrency isolation with upstream hits exact at 120/120, the fail-safe
  hardening round that found **4 fail-open leaks in our own code** and the round that
  closed them, and the "just a prompt" ablation with its disclosed tone null.
- `docs/`: architecture, postures, determinism, limits and a reproduction guide.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, this file.
- **A claims gate in CI.** Every push and pull request is checked against the sealed
  numbers register: banned figure variants, required qualifier pairings, and the
  no-fabricated-social-proof rule. The `$0.1670` defect above is exactly what it exists to
  catch, and it would have caught it.
- Issue templates, including a structured reproduction report.

### Removed
- `receipts/landing/`, a two-file static landing preview. [gubernaut.com](https://gubernaut.com)
  serves that purpose and a stray preview page inside a code repository is confusing.
- An internal development-lane README whose links pointed at directories that never existed
  publicly.

## [1.0.0] - 2026-07-29

First public release. Published to all three registries and verified by clean-environment
installs from the live registries.

| Package | Registry |
|---|---|
| `gubernaut-sdk` | [PyPI](https://pypi.org/project/gubernaut-sdk/) |
| `@gubernaut/plugin-gcc` | [npm](https://www.npmjs.com/package/@gubernaut/plugin-gcc) |
| `gcc-core` | [crates.io](https://crates.io/crates/gcc-core) |

### Added
- Local OpenAI-compatible proxy with the deterministic homeostatic controller. One-line
  adoption through `base_url`.
- Three postures: `DEFAULT`, `INHIBIT`, `REGROUND`, plus the local hard stop that returns a
  deterministic fallback completion with zero upstream tokens.
- Token-free controller boundary. The meta level accepts three finite floats and raises on
  anything else, so no token sequence can reach the component that decides posture.
- Rust core, bit-exact against the Python reference across 73 value-exact golden steps and
  8 boundary rejections. Compiles to wasm.
- ElizaOS plugin.
- Worked integrations for OpenAI SDK, LangChain, LlamaIndex, AutoGen and ElizaOS. All five
  adopt in one line, hard-stop a loop, and fail closed on a dead proxy.
- Receipts bundle: the measured spend battery, the chart and the telemetry.

### Security
- Deny-by-default route policy. Malformed bodies fail closed, booleans parse strictly,
  proxy errors are typed and carry headers, and the Node client has a fetch timeout.
- Zero fail-open leaks. Neither SDK falls back to a real upstream when the proxy is
  unavailable.
- The client's `Authorization` header is forwarded verbatim and never stored.
- Stateless by construction. 240 concurrent mixed hostile and benign requests ran with zero
  posture cross-contamination and zero drops.

[Unreleased]: https://github.com/thegubernaut/gubernaut/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/thegubernaut/gubernaut/releases/tag/v1.0.0
