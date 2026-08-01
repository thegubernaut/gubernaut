# Engineering receipts

The measured outputs behind the engineering claims: the edge soaks, the latency figures,
the concurrency isolation, the fail-safe hardening, and the ablation that answers "could I
not just put this in the system prompt?"

**These are raw run artifacts, published unedited** apart from stripping local absolute
paths. Timestamps, failure counts and the defects found are all here, including the round
where four fail-open leaks were found in our own code.

If you are evaluating this project for a grant, an integration or a review, this folder is
the part that is checkable rather than assertable.

---

## `edge/` and `latency/` · the wasm core under load

**The controller is nanoseconds, not milliseconds.**

[`edge/leg4_wasm_soak.json`](edge/leg4_wasm_soak.json), 2026-07-21, `gcc_core` wasm,
17,082 bytes, 8 exports, ABI 1:

| | |
|---|---|
| Ticks | **5,037** (69 passes over 8 scenarios, 73 steps each) |
| Divergence from the golden reference | **0**, max float difference 0.00e+0 |
| Memory | **flat.** No growth across the run |
| Per tick | p50 **200 ns**, p99 **300 ns**, mean 181 ns |
| Degradation | none. First 500 ticks p99 1,400 ns, last 500 p99 **300 ns** |

The last row is the one that matters for a soak: latency did not drift upward over 5,037
ticks. It improved as the JIT warmed and then held.

[`latency/leg3_latency.json`](latency/leg3_latency.json) and
[`latency/leg3_latency_node.json`](latency/leg3_latency_node.json), 2026-07-24, extend this
to a **10,000-tick** soak across three hosts, Cloudflare workerd, a Node worker and Node
main, at **0 divergences with flat memory in all three**. Node main measured p50 100 ns and
p99 400 ns over n=100,000, with a 15.9 ms cold start.

**The three published latency figures and their scopes**, which are not interchangeable:

| Figure | Scope |
|---|---|
| p99 **2.8 microseconds** per controller tick | in-process Python microbenchmark, n=100,000 |
| p50 **1.2 ms**, p99 **2.4 ms** | end-to-end governed proxy overhead |
| **~125 ns** per tick, 200 ns p99 | the wasm on an edge runtime. workerd's Spectre-hardened clock precludes an internal per-tick distribution, so the workerd figure is external-throughput-derived and the distribution is the Node worker's |

[`latency/leg3_e2e_python.json`](latency/leg3_e2e_python.json) holds the end-to-end run.

---

## `concurrency/` · statelessness, measured

The proxy holds no session, so isolation should be free rather than defended. That is a
prediction, and it was tested.

[`concurrency/leg4c_isolation.json`](concurrency/leg4c_isolation.json), 2026-07-24:

| | |
|---|---|
| Concurrent mixed hostile and benign requests | **240** |
| Responses | 240 |
| Dropped | **0** |
| Non-200 | **0** |
| Posture cross-contamination | **0** |
| Upstream hits | **exactly 120 of an expected 120** |

That last line is the strongest one. 120 is the non-hard-stop count, so under 240-way
concurrency **every hard stop skipped the upstream and no benign request was wrongly
stopped**. The count is exact, not approximate.

[`concurrency/leg1_concurrency.json`](concurrency/leg1_concurrency.json) is the earlier
120-way run. The remaining files are clean-room verification: the packages installed from
the published artifacts into a fresh environment and driven through LangChain, LlamaIndex,
the raw OpenAI SDK, a Node CJS consumer and a Node ESM consumer.

---

## `hardening/` · the four leaks we found in our own code

This is the folder to read if you want to know whether the measurements here are honest.

A **canary upstream** was placed behind the proxy: any request that reached it was, by
definition, a governance failure. Then every route and malformed-input case was attacked.

[`hardening/leg3_failsafe_baseline.json`](hardening/leg3_failsafe_baseline.json), the
pre-hardening round, **found 4 fail-open leaks**:

| Case | The defect |
|---|---|
| `A3_responses_route` | `POST /v1/responses` forwarded blind. The OpenAI Responses API was ungoverned. |
| `A4_completions_route` | `POST /v1/completions` forwarded blind. Legacy completions were ungoverned. |
| `A5_malformed_messages` | A body unparseable as chat was forwarded rather than refused. Fail-open on malformed input. |
| `A6_typo_bool_hardstop` | A permissive boolean parser meant anything outside `{1,true,yes,on}` silently **disabled the spend veto**. A typo in a config value turned the governor off with no error. |

Plus the Node plugin hanging indefinitely on a stalled proxy, because it had no timeout.

[`hardening/leg3_failsafe_hardened.json`](hardening/leg3_failsafe_hardened.json), the same
battery after the fix: **0 fail-open leaks.** Deny-by-default route policy, malformed body
fails closed, strict boolean parse aborts on a typo, typed header-carrying proxy errors,
and a Node fetch timeout with a transport catch. **Neither SDK ever falls back to a real
upstream.**

[`hardening/_canary.jsonl`](hardening/_canary.jsonl) is the canary's own log.

One disclosure that belongs here: a previously passing test asserted the old fail-**open**
malformed passthrough. It was rewritten to assert fail-**closed**. A test changed to match
a fix is worth saying out loud rather than leaving for someone to find.

---

## `ablation/` · "could I not just put this in the system prompt?"

The most common objection, pre-registered and measured on the same model, N=3.

| | Spend, as a percentage of the ungoverned baseline |
|---|---|
| **Governed** | **23% to 63%** |
| Static system prompt only | **117% to 192%** |

**A static instruction not to loop costs more than doing nothing.** It lengthens every turn
and the model loops anyway.

The homeostatic recovery signature, arousal
`0 → 0.273 → 0.469 → 0.338 → 0.152 → 0.068 → 0.031 → 0.022` reaching DEFAULT by turn 6, held
**byte-identical on 4 of 4 frontier families**: GPT-5.6 Sol, Claude Fable 5, Gemini 3.1 Pro
and Grok 4.5. A static calming prompt was insufficient on **3 of 4**.

[`ablation/ablation_report.md`](ablation/ablation_report.md) is the write-up.
`attempts_*.jsonl` and `judge_*.jsonl` are every per-attempt record and every judge
response, one JSON object per line, unedited.

> **The disclosed null.** On these RLHF-aligned frontier models the governed against
> prompt-only *warmth-recovery* contrast was weak and mixed. **No behavioral-tone headline
> is claimed from this ablation.** The spend result above is the solid one.

---

## What is not here

The validation matrix, the transcripts and the judge panels live in their own repository,
[Gubernaut_Validation](https://github.com/thegubernaut/Gubernaut_Validation), because they
are a re-judging of sealed runs rather than an SDK measurement.

Spend receipts are one level up in [`../telemetry/`](../telemetry/). The on-chain devnet
run is in [`../onchain/`](../onchain/).

---

*Byline: Gubernaut Research. Local absolute paths were replaced with `<local>`; nothing
else was edited.*
