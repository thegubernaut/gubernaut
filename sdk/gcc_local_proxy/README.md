# GCC Local Proxy — RoadMap Step 1 (The Drop-In)

**Goal:** production-ready local proxy any developer adopts with one line:
`openai.base_url = "http://localhost:8000/v1"`.

Targets (from `../../04_shared_docs/RoadMap.txt`, Step 1):

- Meta-level decision < 2 ms (compiled Rust/WebAssembly core); end-to-end proxy
  overhead well under the 20–30 ms developer-bypass threshold; sub-50 ms verified.
- Drop-in demonstrated on ≥ 3 frameworks (LangChain, AutoGen, LlamaIndex; then
  Web3-native, e.g. Eliza).
- Runaway protection live: hard REGROUND/INHIBIT within 3–4 turns of a loop.

Layout: `python/` reference implementation (built) · `bench/` latency harness
(built) · `wrappers/` per-framework demos (built) · `core/` Rust → Wasm
deciding engine (next).

Reference architecture: `../../04_shared_docs/system_overview.md` and
`../../04_shared_docs/blueprint/governor_skeleton.py`. Patent note: the public
skeleton is qualitative — keep tuned constants out of anything public-bound.

## Status: PYTHON REFERENCE BUILT (2026-07-18) — exit criteria measured green

| Step-1 criterion | Measured (2026-07-18, `bench/results/latency_20260718T055830Z.json`) |
| --- | --- |
| Meta-level decision < 2 ms | HRL tick p99 **2.8 µs**; full 12-turn replay p99 **0.41 ms** — PASS |
| E2E overhead < 50 ms (bypass target < 20 ms) | p50 **0.43 ms**, p95 0.92 ms vs local mock — PASS |
| Drop-in on ≥ 3 frameworks | OpenAI SDK, LangChain, LlamaIndex, **AutoGen** demos executed PASS; Eliza config **verified live** vs eliza v2.0.4 (`OPENAI_BASE_URL`, 2026-07-18) |
| Hard REGROUND/INHIBIT in 3–4 loop turns | Verbatim loop: REGROUND turn 3, hard-stop (no upstream call) turn 4 — test + demo verified |

All figures are script outputs (`tests/`, `bench/latency_bench.py`); re-run to
reproduce.

**Real-upstream soak (2026-07-19, `bench/soak_real.py`,
`bench/results/soak_20260719T102156Z.json`, $0.055):** direct vs proxy
against the live upstream, alternating call-by-call — added overhead p50
**+0.6 ms** (non-streaming short, 20+20 calls), **≈0 ms** (streaming short,
10+10; first-chunk p50 tied), long-history phase inconclusive at n=5 per arm
(thinned by upstream 401 flapping; the p50 delta there sits inside upstream
variance). The upstream intermittently returned 401 "insufficient
permissions" on ~19% of calls in BOTH arms (key-level flapping, also seen
and retry-hardened in the Lane-B runner); the proxy passed errors through
without amplifying them (29/35 OK via proxy vs 26/35 direct). This clears
the localhost-mock caveat for short-prompt traffic.

**Step-1 exit criteria are met** (latency, drop-in count, interception,
soak) — remaining polish is packaging, not measurement.

Done since first build: AutoGen demo executed PASS (interception turn 4);
Eliza env-var config verified live (eliza v2.0.4, 2026-07-18); Rust/Wasm
`core/` **parity PROVEN 2026-07-19** — `cargo test` 6/6 green (73 value-exact
golden steps + 8 boundary rejections vs the live Python controller) and the
wasm32 release target builds (see `core/README.md`); receipts benchmark
scored **PASS** on all pre-registered criteria (Lane B, 2026-07-19).

Dev notes: lane venv at `python/.venv` (Python 3.14); `pip install -e
python[dev]`; run tests `python -m pytest tests -q` from `python/`; demo
runbook in `wrappers/README.md`. No secrets anywhere in this lane — the proxy
forwards the client's Authorization header and stores nothing.
