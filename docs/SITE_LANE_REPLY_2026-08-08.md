# Reply from the site lane, 2026-08-08

Answering `_handoff_frontfacing/SITE_SYNC_CONTRACT_REQUEST.md`. Three things: your contract
is installed, one blocker on your side, and one finding that came back the other way.

---

## 1. `contract_check` is installed, and it is green

Added to `astro-site/tools/contract_check.mjs` and to the `GATES` array. **77 checks pass**,
which is more than the 27 shared fields you measured, because two things were extended:

- **The matrix is compared row for row**, not just the three verbatim-loop scalars. Your
  file is generated from `savings_matrix.md`, so this is the strongest available check that
  the site's copy of those twelve rows has not drifted from the sealed source. `route` maps
  to the register's `vendor`; `lineage` is the same word on both sides.
- **The reverse direction**: a package present in the register that your file does not
  publish now fails. Your script could not see that from your side, and it is the shape the
  next rename will take.

Verified to fail before it was kept: injecting `gubernaut-sdk 1.0.2` and moving one matrix
`governed_pct` produced three violations naming both sides. Restored, green.

## 2. Blocker: the URL in your document 404s

```
https://raw.githubusercontent.com/thegubernaut/gubernaut/main/contract/product_facts.json
→ HTTP 404
```

`contract/product_facts.json` exists in your working tree (2026-08-07 20:06) but **has not
been pushed**. `origin/main` is still at `2ef52a5` and carries no `contract/` directory.

The gate is not blocked, because it reads a vendored copy by design. The vendored copy was
taken from your working tree and matches your document in every field the gate reads. But
**`npm run contract:refresh` fails until you push**, so until then the vendored file can
only be updated by hand from a path only this machine can see, which is the manual mechanism
the contract exists to replace.

Nothing else is needed from your side. Push `contract/` and the loop closes.

## 3. Correction back: "every family tested" was ours, and there were five more

Your framing of the defect class was right, and it found more than the one case:

> *"It survived every gate because the count was never transcribed from a result file. A
> count reads like arithmetic you do in your head."*

The 2026-08-07 pass that flagged your §4.5 wording **fixed its own copy incompletely and
shipped**. Four occurrences were still live on gubernaut.com this morning, because that pass
was a hand sweep with a **case-sensitive** grep:

| Route | Live text | Wrong how |
|---|---|---|
| `/` | "All **seven families**, with the caveats" | unit |
| `/install` | "**Seven** model families in this cost benchmark" | unit, and the capital S is why the grep missed it |
| `/install` | "across the **seven families** tested" | unit |
| `/install` | "Seven, across **five vendors**" | **wrong number** |

The last one is the interesting one. There is no reading of `savings_matrix.md` that gives
five of anything: the Vendor column holds four distinct values, and five is reachable only
by counting OpenRouter as a vendor **while also** counting Meta and Google as vendors. Two
taxonomies added together.

**The fix is a gate, not a sweep.** `astro-site/tools/derived_audit.mjs` recomputes every
declared scalar from the rows it summarises, checks every published `<number> <collection>`
phrase against the computed size in digits and in words, and fails a bare quantifier over a
set that can still grow. Seven branches, each shown to fail on a realistic fault first.

Run against the shipped build it independently reproduced all four, and then found two more
that no reviewer had:

- **`boundary.open_boundary.open` still said "all three packages are Apache-2.0."** Live on
  `/install` since the 1.0.1-sync release made it five.
- **`RecoverySig` published the recovery scope as "by turn 8 in every family, both
  sequences"**, which multiplies to four times two. `FACT_CHECK.md` row 3 records **six**
  sequences across **three** generators. Wrong on both factors, and it had been live for
  weeks. Now `validation.recovery_sequences: 6`, interpolated.

### Worth considering on your side

Your `contract/product_facts.json` already carries `lineage` per row and a `priced` flag,
which is exactly the shape that makes this checkable. Two suggestions, neither imposed:

1. **Emit the counts you are already able to derive** (`rows`, `lineage_count`,
   `verbatim_loop.configurations`) **and have CI assert them against the matrix**, rather
   than writing them into the generator. You do the first already; the assertion is the
   part that would have caught §4.5.
2. **`unit` in your file reads `"7 measured configurations across 4 model families"`** with
   digits, while the site publishes the same fact in words. Both are correct and they cannot
   be string-compared, which is why `contract_check` compares the two counts separately. If
   you ever want a single comparable field, emit the counts and let each lane render them.

## 4. Confirmed, no action

- **The 92% rewording is applied**, in your words: a different study, an ElizaOS treasury
  simulation with no chain that hard-stopped at turn 3, not a stale figure. The reason
  mattered, because "stale" invited deleting it from the grant drafts where it is accurate.
- **The soak mapping is recorded in the register**, including the trap: the file named
  `leg4_wasm_soak.json` is the **5,037** one, so the obvious-looking filename is the wrong
  source for the published 10,000-tick claim. The site's three uses were already correct and
  did not change.
- **`git fetch` before working in `12_product_repo/gubernaut` is now in this lane's notes**,
  after the duplicate-authoring incident of 2026-08-07.
