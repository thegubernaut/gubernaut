# Gubernaut — receipts for a local governor that hard-stops runaway agent loops

*Gubernaut Research. This repository is the **public receipts bundle**: the
measured benchmark outputs, the render-ready chart, and the launch copy. Every
number here is a script output you can re-run from the source harness.*

> The controller source that produced these numbers lives alongside them, in
> [`../sdk/`](../sdk/). Every figure below is reproducible from it.

---

## The one-line adoption

```python
openai.base_url = "http://localhost:8000/v1"   # the GCC local proxy
```

A deterministic homeostatic controller reads three bounded numbers per turn —
intensity, valence, repetition — and nothing else. No prompt can steer it,
because no token sequence crosses into the meta level. When repetition
saturates it commands a re-grounding posture, and if the loop persists it
hard-stops the call locally: a deterministic fallback completion, **zero
upstream tokens.** Benign traffic passes through untouched.

## The finding

On a saturating loop the governed arm pays a **single-digit-to-low-twenties
percentage** of the ungoverned bill, across every model family we tested —
with the hard stop landing at turn 4 every run.

![Governed spend as % of ungoverned across seven model families](receipts_matrix_chart.svg)

| Where the numbers come from | File |
| --- | --- |
| Chart data (7 series, verbatim-loop battery) | [`telemetry/receipts_matrix_chart.json`](telemetry/receipts_matrix_chart.json) |
| Per-cell receipts (native `usage.cost` where available) | [`telemetry/openrouter_gemini_receipts.json`](telemetry/openrouter_gemini_receipts.json) |
| Cross-vendor savings matrix (markdown) | [`telemetry/savings_matrix.md`](telemetry/savings_matrix.md) |
| Homeostatic recovery telemetry | [`telemetry/framework_stress_test.csv`](telemetry/framework_stress_test.csv) |
| Proxy added-latency sample | [`telemetry/latency_sample.json`](telemetry/latency_sample.json) |
| Live LangChain + Eliza-pattern intercept | [`telemetry/framework_clients.json`](telemetry/framework_clients.json) |
| Lane-E coercive-veto results | [`telemetry/lane_e_veto_results.md`](telemetry/lane_e_veto_results.md) |

Two honest cross-check notes travel with the data: OpenRouter's own metered
cost matched our token-price math for Haiku (exactly) and Gemma (within 13%),
but flagged a **24% divergence for Llama 4 Scout** (provider routing) — so
Scout's dollars are the upstream's meter, not our math; the *ratio* is
unaffected. And Gemma on Google's native API is free-tier only, so that row is
token deltas, not dollars.

## Validation behind the regulation layer

Regulated beats baseline in **15 of 16** generator×judge cells (**11/12
off-diagonal**), **13/16 at p<.05**, across four frontier model families. The
deciding core is also ported to Rust and proven bit-exact against the Python
reference. DOI: **10.5281/zenodo.21303518**.

It's a regulation layer — measured and falsifiable, no cognition claims.

## What's in this bundle

- [`SHOW_HN.md`](SHOW_HN.md) — the launch write-up (draft; repo link is a
  placeholder pending the user's public URL).
- [`receipts_matrix_chart.svg`](receipts_matrix_chart.svg) — the rendered chart.
- [`telemetry/`](telemetry/) — the measured outputs above.
- [`landing/`](landing/) — a self-contained landing preview page.

The drop-in proxy source that produced these numbers is in
[`../sdk/`](../sdk/), and ships as `gubernaut-sdk` (PyPI),
`@gubernaut/plugin-gcc` (npm), and `gcc-core` (crates.io).

---

*Repo link: https://github.com/thegubernaut/gubernaut Byline: Gubernaut
Research. No geographic identifiers; canon vocabulary only.*
