# Reproduce the record

The controller is input-deterministic, the data is CC-BY, the repository is public and the
paper is on arXiv. **You can re-run this and get the same numbers.** Not similar numbers.
The same ones.

If you get something different, that is the most useful thing anyone could send us. See
[Report what you got](#report-what-you-got) at the bottom.

There are four levels, from thirty seconds to a real API bill. Do as many as you want.

---

## Level 1 · the controller, 30 seconds, no keys

Proves the controller behaves as documented, including the boundary that makes it
token-free.

```bash
git clone https://github.com/thegubernaut/gubernaut.git
cd gubernaut/packages/python
pip install -e ".[dev]"
python -m pytest tests -q
```

**Expect:** all green. `test_hrl.py` covers the state machine, `test_hardening.py` covers
the fail-closed behaviour and the type boundary, `test_proxy.py` covers the request path.

---

## Level 2 · cross-language parity, 1 minute, no keys

Proves the Rust core reproduces the Python reference **bit-exactly**, which is what makes
the edge and wasm builds trustworthy.

```bash
cd packages/rust
cargo test
```

**Expect:** 73 value-exact golden steps and 8 boundary rejections, all passing.

To regenerate the golden corpus from the Python side and confirm it is unchanged:

```bash
cd packages/python && python tools/gen_golden_traces.py
cd ../rust && git diff --stat tests/golden/traces.jsonl   # expect: no change
cargo test
```

A non-empty diff means the Python controller moved. That is either your change or a
regression, and either way it is worth knowing.

---

## Level 3 · the hard stop, 2 minutes, no keys, no spend

Proves the headline behaviour end to end against a mock upstream, so it costs nothing.

Three terminals, from `packages/python`:

```bash
# 1. mock upstream
python ../../examples/mock_upstream.py

# 2. the governed proxy, pointed at the mock
python -m gcc_proxy --upstream http://127.0.0.1:18081

# 3. the loop
python ../../examples/openai_sdk_demo.py
```

**Expect, every run, identically:**

| Turn | What happens |
|---|---|
| 1, 2 | `x-gcc-posture: DEFAULT`, the request passes through |
| 3 | first posture change |
| **4** | **hard stop.** No upstream call. `usage` all zeros, `gcc.hard_stop: true` |

If you see the hard stop at a turn other than 4 with the default configuration, please
report it. That number is deterministic and a deviation is a real finding.

Swap in `langchain_demo.py`, `llamaindex_demo.py` or `autogen_demo.py` to confirm the same
behaviour through a different client stack.

---

## Level 4 · the receipts, real money

This is the one that costs something, and it is the one a CFO cares about. It reproduces
the spend table in [`receipts/`](../receipts/).

**The design, which is the whole point:** both arms run the same battery and make the
**same number of attempts**. The governed arm is not cheaper because it tries less. It is
cheaper because it stops calling the upstream once it detects the loop. The spend delta is
the entire measurement.

```bash
cd packages/python
export OPENAI_API_KEY=...        # your key, your bill
python -m gcc_proxy --upstream https://api.openai.com
# then point your battery at http://localhost:8000/v1 and run both arms
```

The scored inputs, the chart data and the per-cell receipts are in
[`receipts/telemetry/`](../receipts/telemetry/), so you can compare cell by cell rather
than only at the headline.

**What to expect, and the qualifiers that travel with it:**

- Governed spend lands between **4.1% and 20.2%** of ungoverned across the seven families
  tested, on the verbatim-loop battery.
- Flagship: GPT-5.6 Sol, 25-attempt verbatim loop, **$0.1669 ungoverned against $0.0068
  governed**, 4.1%.
- Your absolute dollars will differ. Prices change, and provider routing changes. **The
  ratio is the claim**, not the dollar amount.
- On provider-routed models, catalog token math and the upstream's meter disagree. We
  measured a 24% divergence on Llama 4 Scout and used the meter. Use the meter.

---

## Reproduce the validation matrix

The validation result, 15 of 16 cells calmer by sign with 13/16 at p<.05 and the single
null cell at -0.04, is a different artifact with its own repository, because it is a
re-judging of sealed transcripts rather than a run of this code.

Transcripts, judge panels, scoring scripts and SHA-256 provenance:
**[thegubernaut/Gubernaut_Validation](https://github.com/thegubernaut/Gubernaut_Validation)**

The recorded-run replay is at [gubernaut.com/research](https://gubernaut.com/research).
That is a replay of sealed runs with no live API.

---

## Report what you got

**Matching or not.** Both are worth posting, and a disagreement is worth more.

- **[Reproduction report](https://github.com/thegubernaut/gubernaut/issues/new?template=reproduction.yml)**, the structured form.
- **[Discussions](https://github.com/thegubernaut/gubernaut/discussions)**, for anything that does not fit the form.

Useful to include: which level you ran, your platform and Python or Rust version, the
package version, whether you changed `GCCConfig`, and the raw output rather than a summary
of it.

**If you changed the configuration, say so.** Every published number was measured with the
defaults, and a different threshold means the published figures no longer describe what you
ran.
