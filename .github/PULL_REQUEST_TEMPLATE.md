## What and why

<!-- What changed, and the reasoning. The diff already shows what; explain why. -->

## Checklist

- [ ] Tests pass for what I touched (`pytest` / `cargo test` / `npm test`)
- [ ] `python tools/claims_check.py` is clean

**If the controller's behaviour changed:**

- [ ] I regenerated the golden traces: `cd packages/python && python tools/gen_golden_traces.py`
- [ ] `cd packages/rust && cargo test` passes against the regenerated corpus
- [ ] The controller is still pure: no clock, no randomness, no I/O, no session state
- [ ] Nothing text-like crosses into the meta level

**If any number changed or was added:**

- [ ] It is a script output, not an estimate
- [ ] It travels with its qualifier in the same sentence or the one beside it
- [ ] It is not rounded up
- [ ] If it states 15/16, it also states 13/16 at p<.05 and shows the null

<!--
The claims gate enforces the mechanical parts of the last section on every push.
If it fails, it is telling you a published figure and your text disagree.
Rules: .github/claims.json
-->
