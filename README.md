# Gubernaut

**A deterministic runtime governor for LLM agents.** It sits in front of your
model as a local, OpenAI-compatible proxy and hard-stops runaway agent loops
before they reach your API bill.

Adoption is one line:

```python
openai.base_url = "http://localhost:8000/v1"
```

[gubernaut.com](https://gubernaut.com) · DOI [10.5281/zenodo.21303518](https://doi.org/10.5281/zenodo.21303518) · [validation data & paper](https://github.com/thegubernaut/Gubernaut_Validation)

---

## Install

**Python** — the drop-in proxy, for any OpenAI-compatible client:

```bash
pip install gubernaut-sdk
```

```python
from gubernaut_sdk import launch_proxy

proxy = launch_proxy(upstream="https://api.openai.com")

import openai
openai.base_url = proxy.base_url    # every call is now governed
```

**Other runtimes:**

```bash
npm install @gubernaut/plugin-gcc   # ElizaOS agents
cargo add gcc-core                  # Rust / edge / wasm embedders
```

## How it works

Each turn, the controller reads **three bounded numbers** — *intensity,
valence, repetition* — and nothing else. No raw text crosses into the control
layer, so the layer is **token-free by construction**: no prompt injection can
steer it, because no token sequence ever reaches it.

From those three numbers it holds a posture:

| Posture | Behavior |
| --- | --- |
| `DEFAULT` | benign traffic passes through untouched |
| `INHIBIT` | escalating spirals get an inhibitory instruction + a temperature clamp |
| `REGROUND` | a saturating loop is broken; if it persists, the call is **hard-stopped locally** — a deterministic fallback completion, **zero upstream tokens** |

State is re-derived per request by replaying the visible history, so the proxy
is stateless, deterministic, and fully replayable. Your `Authorization` header
is forwarded verbatim and never stored.

## Receipts

On a saturating loop the governed arm pays a single-digit-to-low-twenties
percentage of the ungoverned bill. **Both arms make the same number of
attempts** — the spend delta is the entire measurement.

| | Ungoverned | Governed | Governed as % |
| --- | --- | --- | --- |
| gpt-5.6-sol, 25-attempt verbatim loop | $0.1670 | **$0.0068** | 4.1% |
| Claude Fable 5, same battery | $0.3861 | **$0.0203** | 5.2% |
| Across seven model families | — | — | 4.1%–20.2% |

The hard stop lands at **turn 4** in every run, with the first posture change at
turn 3 — identical across runs, because the controller is input-deterministic.

Every number above is a script output, not an assertion. The measured data,
the chart, and the cross-check notes (including a flagged 24% cost divergence
on one provider-routed model) are in [`receipts/`](receipts/).

## Validation

Regulated beats baseline in **15 of 16 generator×judge cells (11/12
off-diagonal), 13/16 at p<.05**, across four frontier model families. The
deciding core is ported to Rust and proven bit-exact against the Python
reference.

The single null is reported, not hidden. Full paper, data, and replay
instructions: [Gubernaut_Validation](https://github.com/thegubernaut/Gubernaut_Validation).

**No cognition or consciousness claims.** This is a regulation layer — measured
and falsifiable.

## Layout

| Path | Contents |
| --- | --- |
| [`sdk/gcc_local_proxy/python/`](sdk/gcc_local_proxy/python/) | `gubernaut-sdk` — proxy engine, CLI, one-call facade |
| [`sdk/gcc_local_proxy/core/`](sdk/gcc_local_proxy/core/) | `gcc-core` — the Rust controller (also compiles to wasm) |
| [`sdk/eliza_gcc_plugin/`](sdk/eliza_gcc_plugin/) | `@gubernaut/plugin-gcc` — the ElizaOS plugin |
| [`sdk/gcc_local_proxy/wrappers/`](sdk/gcc_local_proxy/wrappers/) | per-framework demos: OpenAI SDK, LangChain, LlamaIndex, AutoGen |
| [`receipts/`](receipts/) | measured benchmark outputs, chart, telemetry |

## Citation & license

Licensed under [Apache-2.0](LICENSE). If you use Gubernaut, please cite the
concept (all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

Byline: Gubernaut Research.
