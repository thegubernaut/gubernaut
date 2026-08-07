# Install commands in prose are unpinned

**Decision, 2026-08-07. From the website lane, for the product lane.**

> "Whenever we update, it automatically updates at the user end. The same command stays
> true forever." (the user, setting this policy)

## The rule

| Where | Form | Example |
|---|---|---|
| Prose, READMEs, quickstarts, the site, any marketing surface | **unpinned** | `pip install gubernaut-sdk` |
| A version matrix whose job is to record what "current" means | **pinned** | `pip install gubernaut-sdk==1.0.1` |

One pinned table per surface, and only where the pin is the point. Everywhere else the
command carries no version.

## Why

A pinned command in prose is correct on the day it is written and wrong on the day of the
next release, on every surface that repeats it. That is a recurring defect, not a one-time
one, and this project has already paid for it once: **the README advertised
`gubernaut-sdk==1.0.0` for four days after 1.0.1 shipped, through a green CI gate.** The
release checklist gained a step, the surfaces got re-edited, and the same failure was
queued up again for 1.0.2.

An unpinned command has nothing to go stale. It resolves to the newest published version at
the moment the reader runs it, which is what a quickstart is for. Someone who needs
reproducibility pins deliberately, from the version matrix, which is where a pin means
something.

There is a second reason as of the 1.0.1-sync release. **`gubernaut-core` exists only at
1.0.1.** There is no 1.0.0 under that name, so a command copied forward from the old
crate's documentation and pinned to that version would not merely be stale, it would fail
outright: there is nothing for cargo to resolve.

That example is not written out here, because `claims_check.py` correctly rejects it. Three
findings came back on the first draft of this file, one of them the pinned command above,
and all three were real. A policy document about install commands that cannot itself pass
the install-command gate would not be worth much.

## Compatibility with `tools/claims_check.py`

**This policy does not require a change to that gate, and does not weaken it.**

`install_pins_in()` finds version pins that appear in an *install form* and fails when the
pin disagrees with the manifest. It validates pins where they appear; it does not require
one. An unpinned command carries no pin, so the rule finds nothing to check and passes.
Bare version mentions in changelogs and "1.0.0 is not yanked" notes were already exempt by
design, and stay exempt.

So adopting this policy makes the failure class **impossible in prose** rather than merely
detected there, and leaves the gate guarding the one place a pin still lives.

**Worth considering, not done here:** a companion rule that fails a *pinned* install
command outside an allow-listed version-matrix file. That is what would make the policy
enforced rather than agreed. It is the product lane's call, on the product lane's gate.

## What the site does

`gubernaut.com` shipped this on 2026-08-07. Each of the five packages carries both forms in
the sealed register (`astro-site/src/data/facts.json`):

```json
"crates": {
  "name": "gubernaut-core",
  "version": "1.0.1",
  "install": "cargo add gubernaut-core",
  "install_pinned": "cargo add gubernaut-core@1.0.1"
}
```

`numbers_audit` enforces both directions and fails the build on any of:

- an `install` string that contains a version pin (a pin creeping back into copy),
- an `install_pinned` string that does not carry its own package's declared version,
- the two forms naming different packages (a half-landed rename),
- a package missing either form,
- `packages.version`, the release train, not equalling the highest of the five.

All five branches were shown to fail before they were kept. `/releases` is the only route
that renders a pinned command.

## Surfaces to bring across

Not done by this lane. Listed so the product lane can decide and sequence.

- `README.md` and `packages/*/README.md` quickstarts.
- `receipts/SHOW_HN.md` and any launch copy holding an install line.
- `docs/REPRODUCE.md` **stays pinned** where a level's purpose is reproducing a specific
  published artifact. That is a version matrix in prose form, and the pin is the point.

## One correction, sent back up

`04_shared_docs/V1_ENGINEERING_RECORD.md` §4.5 reads *"12 rows across 7 model families and
2 batteries"*. Counted from `receipts/telemetry/savings_matrix.md`, the verbatim-loop
battery is **seven rows spanning four lineages**: OpenAI (GPT-5.6 Luna, GPT-5.6 Sol),
Anthropic (Claude Fable 5, Claude Haiku 4.5), Meta (Llama 4 Scout) and Google (Gemma 4 26B
on two routes).

The record uses "families" for what its own table shows as configurations. It matters
publicly because the site uses "family" in the strict lineage sense elsewhere, most visibly
"four frontier families" for the validation record, so "seven families" let any reader
count to four and find a contradiction. **The site now publishes "seven measured
configurations across four model families."** §7.3 already warns that the range depends on
which battery is meant; the unit needs the same care.
