# Changelog

Notable changes to Gubernaut. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Published versions are immutable. A defect in a released version is corrected by shipping
the next one, never by rewriting a published artifact.

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
