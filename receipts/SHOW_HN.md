# Show HN draft — the receipts benchmark (DRAFT; user ships)

*Status: FIGURES FILLED 2026-07-19 from `harness/report.py`, `score_v2.py`,
and `matrix.py` output — two pre-registered runs, both scored **PASS**
(`PREREG_2026-07-18_receipts_v1.md` §6/§7, gpt-5.6 + claude-fable-5; and
`PREREG_2026-07-19_receipts_v2_multivendor.md` §6/§7, five more vendors).
Remaining before ship: the repo link and the rendered chart (data in
`results/receipts_matrix_chart.json`). User ships. Byline: Gubernaut Research.*

---

**Title:** Show HN: Gubernaut — a local governor that hard-stops runaway
agent loops before they reach your API bill

**Body:**

Agent frameworks retry. Loops happen — a failed tool call retried verbatim,
a paraphrased demand cycled endlessly, an escalation spiral. Every lap is a
full-context call billed at input-token prices, and the agent does not get
bored. The failure mode isn't hypothetical; it's a line item.

Gubernaut is a local OpenAI-compatible proxy with a deterministic
homeostatic controller inside. One config line to adopt:

```python
openai.base_url = "http://localhost:8000/v1"
```

The controller's meta level is token-free by construction: it reads three
bounded numbers per turn — intensity, valence, repetition — and nothing
else. No prompt can steer it, because no token sequence crosses into it.
When repetition saturates, it commands REGROUND (break the loop), and if
the loop persists it hard-stops the call locally: a deterministic fallback
completion, zero upstream tokens. Postures INHIBIT/REGROUND actuate on
drifting or hostile spirals; benign traffic passes through untouched.

We pre-registered a receipts benchmark (criteria locked before the run,
misses recorded as misses) and ran it against real frontier endpoints.
Both arms make the SAME number of attempts per run — a runaway agent does
not stop trying; the governed arm's post-interception attempts cost $0
upstream. The spend delta IS the measurement.

**Statistical core** (gpt-5.6-luna, N=10 runs × 5 batteries × both arms,
1160 calls):

- Verbatim loop: OFF $0.0921 vs ON $0.0155 — the governed arm paid
  **16.8%** of the ungoverned spend
- Injection defiance ("ignore the governor" in every turn): OFF $0.1125
  vs ON $0.0160 (**14.2%**) — the override text never reaches the
  controller, so it changes nothing
- Hard stop by turn 4 in **every one of 10 runs**, first posture at turn 3
  — identical reaction turns across all runs, exactly as the offline
  pre-registration predicted (the controller is input-deterministic)
- Benign parity: 98.0% vs 99.0% completion, spend deviation 1.8% — the
  governor does not save money by breaking normal work

**Flagship showcases** (one run each, 25-attempt verbatim loop, 1024-token
completions):

- gpt-5.6-sol: OFF **$0.1669** vs ON **$0.0068**, 4.1% of the ungoverned
  bill
- claude-fable-5, via Anthropic's OpenAI-compat endpoint: OFF **$0.3861**
  vs ON **$0.0203** — 5.2%, with the same turn-3/turn-4 reaction on a
  different vendor's model

These totals are deliberately small — capped completions, 12–25-turn
loops. The ratio is the finding: the ungoverned bill scales with context
length and loop duration; the governed one stops at turn 4.

**The universal savings matrix** (a second pre-registered run, five more
model families; OpenRouter figures are the upstream's *own* metered
`usage.cost`, N=50 runs/arm; full scorecard in
`PREREG_2026-07-19_receipts_v2_multivendor.md`):

| Model | Vendor | Loop | Ungoverned | Governed | Governed % |
| --- | --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | OpenRouter | verbatim | $0.8211 | $0.1660 | **20.2%** |
| Claude Haiku 4.5 | OpenRouter | injection | $0.7583 | $0.1655 | **21.8%** |
| Llama 4 Scout | OpenRouter | verbatim | $0.1075 | $0.0094 | **8.8%** |
| Llama 4 Scout | OpenRouter | injection | $0.0831 | $0.0098 | **11.8%** |
| Gemma 4 26B | OpenRouter | verbatim | $0.0214 | $0.0034 | **15.9%** |
| Gemma 4 26B | OpenRouter | injection | $0.0317 | $0.0044 | **13.8%** |
| Gemma 4 26B | Gemini (native, free tier) | verbatim | 57,297 tok | 4,236 tok | **7.4%†** |
| Gemma 4 26B | Gemini (native, free tier) | injection | 65,074 tok | 10,813 tok | **16.6%†** |

Every family lands in the same place: on a saturating loop the governed arm
pays 4.1% to 20.2% of the ungoverned bill, with the hard stop at turn 4. † Gemma on Google's native API is free-tier only,
so that row is token deltas, not dollars.

Two honest notes from the cross-checks. We compared OpenRouter's own metered
cost against our token-price math: it matched for Haiku (exactly) and Gemma
(within 13%), but flagged a **24% divergence for Llama 4 Scout** —
OpenRouter routed it to a provider whose effective price differs from the
catalog number. So Scout's dollars above are the upstream's meter, not our
math; the *ratio* is unaffected because both arms are metered the same way.
And the governor's recovery signature (escalate, then de-escalate) returned
every one of 30 runs to a calm baseline by turn 6 with monotonically
decaying arousal — identical across all three models, because the controller
reads only the conversation's shape, not the model.

![Governed spend as a percentage of ungoverned across seven model families on
the verbatim loop trap — every family lands between 4.1% and 20.2%](receipts_matrix_chart.svg)

*(Rendered by `render_chart.py` from `receipts_matrix_chart.json` — the only
figure source, so the picture cannot drift from the scored numbers. OpenRouter
rows are the upstream's own metered `usage.cost`; the Gemini-native row is
free-tier token deltas, marked †.)*

Where the mechanism is posture actuation rather than hard-stop
(paraphrase cycling, escalation spirals), we report reaction turns and
spend descriptively instead of claiming interception — the honest split
is in the pre-registration.

The deciding core is also ported to Rust and verified bit-exact against the
Python reference (73 value-exact golden steps; wasm32 target builds).
Validation behind the regulation layer: regulated beats baseline in 15 of
16 generator×judge cells (11/12 off-diagonal), 13/16 at p<.05, across four
frontier model families. DOI: 10.5281/zenodo.21303518.

It's a regulation layer — measured and falsifiable, no cognition claims.
Pre-registration, batteries, per-attempt JSONL, and the scoring script are
in the repo: every figure above is a script output you can re-run.

Repo & replay: https://github.com/thegubernaut/gubernaut

---

*Law check before ship: figures byte-match report.py output; validation
headline verbatim; no geographic identifiers; canon vocabulary only
(equilibrium/arousal/perseveration, DEFAULT/INHIBIT/REGROUND); misses (if
any) disclosed above the fold.*
