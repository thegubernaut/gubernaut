# Limits

What Gubernaut does not do, what has not been measured, and where the numbers stop
applying. Read this before you deploy it.

Nothing here is a roadmap item in disguise. These are the current boundaries of the
measured record.

---

## Injection resistance is scoped to the controller

**What is true.** The controller is token-free by construction. It accepts three finite
floats and raises on everything else at a type boundary, so no token sequence can reach the
thing that decides posture. Measured: 324/324 telemetry-matched payload pairs, plain
against injection, committed byte-identical postures. The meta level rejected every
non-numeric input, 5/5.

**What is not true.** Gubernaut is **not injection-proof**. The arbiter reads raw text
because generating an answer requires reading the question, and it is exactly as
susceptible as the model behind it. Its compliance with a commanded posture is a measured
property rather than a structural guarantee.

**There is no jailbreak success-rate figure in this project, because none was measured.**
Anyone quoting one is quoting something that does not exist.

The two mechanisms that hold regardless of what the model does are the temperature clamp,
applied before the request leaves, and the hard stop, which never sends the request.

---

## The v0 sensor under-reads calm hostility

The shipped appraiser is a deliberately basic local heuristic: lexicon affect plus
token-set repetition. It has a known recall gap.

| Measured | Result |
|---|---|
| Calmly worded, non-lexicon hostility | **5/5 missed** on that corpus |
| False sever on benign traffic | 0/30 |
| Calm loops caught by the repetition veto | 10/10 |

**This is a sensor-recall limit, not a control-boundary breach.** The controller did the
right thing with the telemetry it received, and the telemetry was wrong. Politely phrased
hostility with no lexicon hits reads as calm.

The repetition channel is unaffected, which is why loops are still caught when nothing
hostile ever happens. A higher-fidelity classifier is the intended fix and it is not in
1.0.

---

## Latency has three figures and they are not interchangeable

Quoting any of these without its scope is a false claim, not a shortened one.

| Figure | Scope |
|---|---|
| **p99 2.8 microseconds** per controller tick | In-process Python microbenchmark, n=100,000, Windows 11 AMD64, Python 3.14.5. Not end-to-end, not the wasm, no network. |
| **p50 1.2 ms, p99 2.4 ms** | End-to-end governed proxy overhead. |
| **~125 ns per tick**, 200 ns p99 | The wasm core on an edge runtime. The workerd figure is external-throughput-derived; the distribution is the identical wasm in a Node worker. |

Against a local mock upstream the proxy added p50 0.43 ms and p95 0.92 ms over n=300 per
arm. Against a **live** upstream the added overhead was p50 +0.6 ms non-streaming and
approximately 0 ms streaming.

**The long-history phase of that soak is inconclusive at n=5 per arm** and is reported that
way rather than rounded into the headline.

---

## Where the dollar figures stop applying

The receipts measure a **saturating loop**, which is the failure mode Gubernaut exists to
stop. On that battery the governed arm pays 4.1% to 20.2% of the ungoverned bill across
seven model families.

That is a ceiling on a specific pathology. It is not a general claim about your bill.

Benign traffic passes through untouched, and the measured benign parity is 98.0% against
99.0% completion with 1.8% spend deviation. **The governor does not save money by breaking
normal work**, and on an agent that never loops it saves nothing, which is the correct
outcome.

Two figures that are deliberately not published as dollars:

- **Llama 4 Scout absolute dollars from token math.** The catalog price sits 24% off the
  metered cost on provider routing, so that row uses the upstream's meter. The ratio is
  unaffected.
- **Gemma on Google's native API.** Free tier only, so that row is token deltas.

---

## Not measured, therefore not claimed

- **Veto-stage latency as a product number.** The v1 gatekeeper is a remote model call.
- **Long-history real-upstream overhead.** Inconclusive at n=5.
- **Any adoption figure.** No customer reviews, testimonials, logos, user counts, download
  counts or star ratings exist for this project. None will be fabricated.

---

## Out of scope for 1.0

**Real-time motor control and embodied loops.** Not attempted, not measured, not claimed.

**PEV and SMM.** The predictive error veto and the self-model memory are sequestered in v1
and are not part of the 1.0 packages.

**Behavioral tone as a headline.** In the ablation, the governed against prompt-only
warmth-recovery contrast on RLHF-aligned frontier models was weak and mixed. No tone
headline is claimed from it. The spend result from the same ablation is solid and is the
one quoted.

---

## The null cell

The validation matrix is 15 of 16 cells calmer by sign, 11/12 off-diagonal, 13/16 at p<.05.

The one null is GPT by Gemini at **-0.04**. It sits on the calmest host, the one with the
least reactivity left to regulate, and the three sub-threshold cells all sit on that same
near-saturated host.

It is reported everywhere the headline is reported, and it was not patched.

---

## Changing the configuration

Every published number was measured with the default `GCCConfig`. Change a threshold, a
gain or a decay constant and the published figures no longer describe your deployment. Say
so when you report results.
