# 1.0.2 · prepared, not published

**Status: READY FOR THE HUMAN.** Four packages are at 1.0.2 on branch
`release/1.0.2-split`, stacked on `docs/launch-readiness-2026-08-24`. Nothing is pushed and
nothing is published: this repository's only remote is public, so both are yours (T4).

**What it is:** documentation and metadata only. The packages present the two products,
split by how they run: Gubernaut Tiller, the proxy, and Gubernaut Keel, the controller
in-process. See `CHANGELOG.md` for the detail.

| Package | Registry | Version | Product |
| --- | --- | --- | --- |
| `gubernaut-sdk` | PyPI | 1.0.1 → **1.0.2** | Tiller |
| `@gubernaut/plugin-gcc` | npm | 1.0.1 → **1.0.2** | Tiller client |
| `@gubernaut/core` | npm | 1.0.1 → **1.0.2** | Keel, JavaScript |
| `gubernaut-core` | crates.io | 1.0.1 → **1.0.2** | Keel, Rust |
| `gcc-core` | crates.io | stays **1.0.1** | deprecation shim, unchanged |

## Before anything is pushed or published

1. **The product pages must be live.** Every package's homepage, and a link in each README,
   now points at `gubernaut.com/tiller` or `gubernaut.com/keel`. Those pages are built in the
   site's v1 sandbox and go live at its cut-over. Published earlier, the links 404 on four
   registry pages and on GitHub. To publish before cut-over, set the four homepage fields back
   to `https://gubernaut.com` and drop the two README links first.
2. **The review is clean.** The Codex read-only review of this branch did not run: the
   Codex usage limit was spent when it was prepared. The command is in the site's
   `runs/2026-09-18_v1-u2-packaging.md`.
3. **CI is green on the pushed branch, the `rust + wasm target` job included.** Its drift
   check, a fresh wasm build compared with the bytes `@gubernaut/core` embeds, could not run
   on the machine that prepared this (no `wasm32` target). It is the one check that proves
   the version bump left the controller byte-identical, SHA-256 `834015d7…`.
4. **Merge order:** `docs/launch-readiness-2026-08-24` into `main`, then this branch.

## Measured on the machine that prepared it, 2026-09-18

| Check | Result |
| --- | --- |
| `pytest packages/python/tests` | 40 passed, the same as before the change |
| golden traces regenerated | unchanged |
| `cargo test`, `gubernaut-core` / `gcc-core` | 7 / 3 passed |
| `npm test` + `typecheck`, `@gubernaut/core` / `@gubernaut/plugin-gcc` | 10 / 15 passed, both clean |
| `tools/claims_check.py`, and `--self-test` | clean on 84 files; the self-test fires |
| `uv build` + `twine check` | `gubernaut_sdk-1.0.2` wheel and sdist, both PASSED |
| `npm pack --dry-run` | `@gubernaut/core` 1.0.2, 7 files, 34.7 kB · `@gubernaut/plugin-gcc` 1.0.2, 7 files, 11.1 kB |
| `cargo package` | `gubernaut-core` 1.0.2, 9 files, packaged and verified |

## Publishing, in this order

- [ ] Tag `v1.0.2`, push the tag, cut a GitHub Release.
- [ ] `cargo publish` in `packages/rust`. Nothing else depends on it being first, but crates
      cannot be unpublished, so it is the one to get right while attention is fresh.
- [ ] `npm publish --access public` in `packages/core-js`, then in `packages/node`.
- [ ] `python -m build`, `twine check dist/*`, then upload `gubernaut-sdk`.
- [ ] Every token is read in place from the master key home. Never paste one, never put it
      on a command line, never write it to disk.
- [ ] **Wait for the indexes.** A registry's JSON API reports a version a few minutes before
      an installer can resolve it.
- [ ] `python tools/verify_published.py`. It installs each package from its registry into a
      throwaway environment and runs it. It must print `ALL PUBLISHED PACKAGES VERIFIED`.
- [ ] Do not yank 1.0.1. Published versions are immutable by policy.

## Then the site

The site's register (`astro-site/src/data/facts.json` `packages.*`) moves to 1.0.2 through its
register stage: each package's own `version` and `install_pinned`, and `packages.version`.
`numbers_audit` fails the build if one moves without the others.

**`npm run contract:refresh` will not work.** The site's vendored contract names
`tools/build_contract.py` in this repository as its generator. That script is not in this
repository or its history: it lived only in a working tree before the 2026-08-30 migration.
The site holds this as an open question for the human, with options.
