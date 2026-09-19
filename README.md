# Gubernaut 1.0

**Your agent stopped making progress. The bill did not.**

An agent retries a failed tool call word for word. Each retry sends the whole conversation
back, and you pay for all of it, every time. Nothing inside the loop knows it is a loop.
You find out from the bill.

Gubernaut is a deterministic runtime governor for LLM agents. It reads three bounded
numbers per turn and none of your text, and decides when a saturating loop must stop.
**Gubernaut Tiller** runs it as a local, OpenAI-compatible proxy in front of your model and
hard-stops the turn itself, before the request is sent: a stopped turn calls no upstream, so
it costs nothing. **Gubernaut Keel** runs it inside your own program, and your code acts on
the decision.

Start Tiller, then change one line in your code:

```bash
gubernaut-proxy --upstream https://api.openai.com     # binds 127.0.0.1:8000
```
```python
client = OpenAI(base_url="http://localhost:8000/v1")   # the one line of adoption
```

[![PyPI](https://img.shields.io/pypi/v/gubernaut-sdk?label=gubernaut-sdk&color=0072B2)](https://pypi.org/project/gubernaut-sdk/)
[![crates.io](https://img.shields.io/crates/v/gubernaut-core?label=gubernaut-core&color=0072B2)](https://crates.io/crates/gubernaut-core)
[![npm](https://img.shields.io/npm/v/%40gubernaut%2Fcore?label=%40gubernaut%2Fcore&color=0072B2)](https://www.npmjs.com/package/@gubernaut/core)
[![npm](https://img.shields.io/npm/v/%40gubernaut%2Fplugin-gcc?label=%40gubernaut%2Fplugin-gcc&color=0072B2)](https://www.npmjs.com/package/@gubernaut/plugin-gcc)
[![License](https://img.shields.io/badge/license-Apache--2.0-555555)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21303518-0072B2)](https://doi.org/10.5281/zenodo.21303518)
[![arXiv](https://img.shields.io/badge/arXiv-2607.24339-b31b1b)](https://arxiv.org/abs/2607.24339)

[gubernaut.com](https://gubernaut.com) · [the paper](https://arxiv.org/abs/2607.24339) · [validation data](https://github.com/thegubernaut/Gubernaut_Validation) · [docs](docs/)

---

## Start here

One controller, two products, split by how they run.

- **Gubernaut Tiller** is the proxy: a separate process your agent's model calls pass
  through. It stops a looping call itself, on the wire.
- **Gubernaut Keel** is the controller inside your program. It decides, and your own code
  acts on the decision. No proxy, no network hop.

One question picks between them: should it stop the call itself, or should the decision sit
inside your code?

| Product | How it runs | Install | Use it for |
| --- | --- | --- | --- |
| **Gubernaut Tiller** · start here | a proxy, its own process | `pip install gubernaut-sdk` | The reference implementation: the proxy, the controller, the CLI. Language-neutral: any OpenAI-compatible client can point at it. |
| Tiller client · ElizaOS | talks to the proxy | `npm install @gubernaut/plugin-gcc` | ElizaOS agents and on-chain runtimes, routed through the proxy. It does nothing without the proxy running. |
| **Gubernaut Keel** · JS/TS | in-process | `npm install @gubernaut/core` | The same wasm controller inside your program. Node, Deno, Bun, workerd, the browser. |
| **Gubernaut Keel** · Rust | in-process | `cargo add gubernaut-core` | The controller as a Rust library, no network. Keel's wasm is compiled from it. |

The product names change nothing you install: every command above is the one that has always
worked. Each product has its own page: [gubernaut.com/tiller](https://gubernaut.com/tiller)
and [gubernaut.com/keel](https://gubernaut.com/keel).

> **Renamed at 1.0.1:** the Rust crate was `gcc-core`. "gcc" is unsearchable next to the GNU
> Compiler Collection. `gcc-core` 1.0.0 is **not yanked**, and `gcc-core` 1.0.1 is a shim
> that re-exports `gubernaut-core`, so nothing existing breaks. The controller is unchanged:
> the compiled wasm is byte-identical across the rename.

Everything is Apache-2.0 and free. There is no hosted tier, no key, and no account.

### Python, end to end

```python
from openai import OpenAI
from gubernaut_sdk import launch_proxy

# 1. start the governor in front of your upstream
launch_proxy(upstream="https://api.openai.com", port=8000)

# 2. one line of adoption
client = OpenAI(base_url="http://localhost:8000/v1")

# 3. nothing else changes. every turn now passes the controller.
resp = client.chat.completions.with_raw_response.create(
    model="gpt-5.6-sol",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.http_response.headers.get("x-gcc-posture"))  # DEFAULT | INHIBIT | REGROUND
```

**Set `base_url` on the client.** Three things bite here, all of them silent:

- The pre-v1 `openai.api_base` attribute is ignored by current OpenAI SDKs, so a client
  configured that way goes straight to the upstream ungoverned and nothing errors to tell
  you.
- The **module-level** `openai.base_url` attribute needs a **trailing slash**. Without one
  the SDK builds `/v1chat/completions` and returns 404. Setting `base_url` on the client
  object works either way, which is why every example here uses that form.
- `launch_proxy()` binds an **ephemeral** port unless you pass `port=`, so either pass it
  as above or read `proxy.base_url` back.

Reading the posture needs `with_raw_response`: a plain `create()` returns a parsed
`ChatCompletion`, which carries no headers.

Worked integrations for OpenAI SDK, LangChain, LlamaIndex, AutoGen and ElizaOS are in
[`examples/`](examples/). All five adopt in one line, hard-stop a loop, and fail closed on
a dead proxy, installed from the published artifacts only.

---

## How it works

Each turn, the controller reads **three bounded numbers**, *intensity*, *valence* and
*repetition*, and nothing else. No raw text crosses into the control layer, so the layer is
**token-free by construction**: no token sequence ever reaches it, and the meta level
rejects every non-numeric input at the type boundary. Across **324 of 324** constructed
telemetry-matched payload pairs, plain against injection, the controller committed
byte-identical postures.

> **Scope.** That is claimed for the **controller** only. The arbiter that composes the
> reply reads raw text by necessity. Gubernaut is not injection-proof, and the full
> boundary is in [What it does not do](#what-it-does-not-do) below.

From those three numbers it holds a posture:

| Posture | Behavior |
| --- | --- |
| `DEFAULT` | benign traffic passes through untouched |
| `INHIBIT` | an escalating spiral gets an inhibitory instruction and a temperature clamp |
| `REGROUND` | a saturating loop is broken. If it persists, the call is **hard-stopped locally**, returning a deterministic fallback completion with **zero upstream tokens** |

State is re-derived per request by replaying the visible history, so the proxy is
stateless, deterministic and fully replayable. Your `Authorization` header is forwarded
verbatim and never stored.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/POSTURES.md](docs/POSTURES.md)

---

## The receipts

On a saturating loop the governed arm pays a fraction of the ungoverned bill. **Both arms
make the same number of attempts**, so the spend delta is the entire measurement. They
were measured through the proxy, **Gubernaut Tiller**.

| | Ungoverned | Governed | Governed as % |
| --- | --- | --- | --- |
| GPT-5.6 Sol, 25-attempt verbatim loop | $0.1669 | **$0.0068** | 4.1% |
| Claude Fable 5, same battery | $0.3861 | **$0.0203** | 5.2% |
| Across seven measured configurations, four model families | | | **4.1% to 20.2%** |

Stated as savings, that range is **79.8% at worst and up to 95.9% at best**. The ceiling is
the GPT-5.6 Sol row exactly, unrounded, and it never travels without the floor beside it.

The hard stop lands at **turn 4** in every run, with the first posture change at turn 3,
identical across runs, because the controller is input-deterministic.

Every number above is a script output. The measured data, the chart, and the cross-check
notes, including a flagged 24% cost divergence on one provider-routed model, are in
[`receipts/`](receipts/).

### On a chain

The same mechanism was run against a contract that reverts on every call, on a local
ephemeral EVM devnet (ganache, chain id 31337, not a public testnet). The governed agent
submitted **3 reverting transactions and was severed at turn 4**. The ungoverned agent
submitted **8**, and stopped only because the harness capped it. The governed balance ended
strictly greater, and every transaction has a real hash and gas receipt.

Scaled up: 24 agents per arm produced **72 governed transactions against 960 ungoverned**,
with all 24 governed agents severing at turn 4. Under 210 concurrent agents across three
revert patterns, **210 severed, 0 drops**.

Full record with tx hashes: [`receipts/onchain/`](receipts/onchain/).

### "Could I not just put this in the system prompt?"

Measured, pre-registered, same model, N=3:

| | Spend, as % of ungoverned baseline |
| --- | --- |
| **Governed** | **23% to 63%** |
| Static system prompt only | 117% to 192% |

A static instruction not to loop costs more than doing nothing, because it lengthens every
turn and the model still loops.

---

## Validation

Regulated beats baseline in **15 of 16 generator by judge cells (11/12 off-diagonal),
13/16 at p<.05**, across four frontier model families, with the recovery signature
replicating 4/4.

The single null cell is GPT by Gemini at **-0.04**. It sits on the calmest host, the one
with the least reactivity left to regulate, and it is reported rather than patched.

Full paper, data, and replay instructions:
[arXiv:2607.24339](https://arxiv.org/abs/2607.24339) ·
[Gubernaut_Validation](https://github.com/thegubernaut/Gubernaut_Validation) ·
[gubernaut.com/research](https://gubernaut.com/research)

**No cognition or consciousness claims.** This is a regulation layer, measured and
falsifiable.

---

## What it does not do

Read this before you deploy it. The full list is [docs/LIMITS.md](docs/LIMITS.md).

- **Injection resistance is claimed for the controller only.** The controller is token-free
  and cannot be steered by text. The arbiter reads raw text by necessity, and its posture
  compliance is a measured property. Gubernaut is not injection-proof, and there is no
  jailbreak success-rate figure here because none was measured.
- **The v0 lexicon sensor under-reads calmly worded hostility**, 5/5 missed on that corpus.
  That is a sensor-recall limit. The repetition veto caught 10/10 calm loops and false
  severs on benign traffic were 0/30.
- **Latency has three separate figures and they are not interchangeable.** One controller
  tick is p99 2.8 microseconds as an in-process microbenchmark, n=100,000. End-to-end
  governed proxy overhead is p50 1.2 ms and p99 2.4 ms. The wasm core on a real edge
  runtime is roughly 125 ns per tick in workerd, with 200 ns p99 on the identical wasm in a
  Node worker.
- **No motor control, no real-time embodied loop.** Out of scope for 1.0.

---

## Reproduce it

The controller is input-deterministic, the data is CC-BY, and the paper is public. You can
re-run the record and get the same numbers.

```bash
git clone https://github.com/thegubernaut/gubernaut.git
cd gubernaut/packages/python && pip install -e ".[dev]"
python -m pytest tests -q          # the controller, including the golden traces
cd ../rust && cargo test           # bit-exact parity against the Python reference
```

Then run the receipts battery yourself: [docs/REPRODUCE.md](docs/REPRODUCE.md).

**Post what you get**, matching or not, in
[Discussions](https://github.com/thegubernaut/gubernaut/discussions) or as a
[reproduction report](https://github.com/thegubernaut/gubernaut/issues/new?template=reproduction.yml).
A result that disagrees with ours is more useful to us than one that agrees.

---

## Layout

| Path | Contents |
| --- | --- |
| [`packages/python/`](packages/python/) | `gubernaut-sdk`, **Gubernaut Tiller**. Proxy engine, controller, CLI, one-call facade |
| [`packages/rust/`](packages/rust/) | `gubernaut-core`, **Gubernaut Keel** for Rust. The controller as a library; Keel's wasm compiles from it |
| [`packages/rust-shim/`](packages/rust-shim/) | `gcc-core` 1.0.1. Deprecation shim re-exporting `gubernaut-core` |
| [`packages/core-js/`](packages/core-js/) | `@gubernaut/core`, **Gubernaut Keel**. The same wasm controller for JS/TS |
| [`packages/node/`](packages/node/) | `@gubernaut/plugin-gcc`. The ElizaOS plugin, a client of Tiller |
| [`examples/`](examples/) | Per-framework demos: OpenAI SDK, LangChain, LlamaIndex, AutoGen, ElizaOS |
| [`bench/`](bench/) | Latency harness and the real-upstream soak |
| [`receipts/`](receipts/) | **The evidence.** Spend receipts, the on-chain devnet run, and the engineering corpus: soaks, latency, concurrency, hardening, ablation |
| [`docs/`](docs/) | Architecture, postures, determinism, limits, reproduction |

---

## Citation and license

Licensed under [Apache-2.0](LICENSE). If you use Gubernaut, please cite the concept
(all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

Machine-readable metadata is in [CITATION.cff](CITATION.cff). Byline: Gubernaut Research.

**Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) ·
**Security:** [SECURITY.md](SECURITY.md) ·
**Changes:** [CHANGELOG.md](CHANGELOG.md)
