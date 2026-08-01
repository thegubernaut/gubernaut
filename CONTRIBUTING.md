# Contributing

Gubernaut is Apache-2.0 and contributions are welcome. This file covers the parts that are
specific to this project, which are mostly about **numbers** and **determinism**.

## The most useful thing you can contribute

**A reproduction.** Especially one that disagrees with us.

The controller is input-deterministic, the data is CC-BY and the paper is public, which
means anyone can re-run the record. A result that contradicts a published figure is worth
more to this project than a feature, and it is the whole reason
[docs/REPRODUCE.md](docs/REPRODUCE.md) exists.

Post it as a [reproduction report](https://github.com/thegubernaut/gubernaut/issues/new?template=reproduction.yml)
or in [Discussions](https://github.com/thegubernaut/gubernaut/discussions). Matching
results are welcome too.

## Ways in, roughly by effort

| | |
|---|---|
| Run a level from [REPRODUCE.md](docs/REPRODUCE.md) and post what you got | 30 seconds to an afternoon |
| Report a bug with a minimal reproduction | |
| Add a framework integration in `examples/` | one file, high value |
| Improve the sensor's recall on calmly worded hostility | the known open problem, see [LIMITS.md](docs/LIMITS.md) |
| Anything touching the controller's update rule | read the determinism rules below first |

## Setup

```bash
git clone https://github.com/thegubernaut/gubernaut.git
cd gubernaut

cd packages/python && pip install -e ".[dev]" && python -m pytest tests -q
cd ../rust && cargo test
cd ../node && npm install && npm test
```

Python 3.10 or newer. A recent stable Rust. Node 20 or newer.

## The rules that are particular to this project

### 1. The controller stays deterministic

`HomeostaticLoop.update` is a pure function. No clock, no randomness, no I/O, no network,
no accumulated session state. A patch that introduces any of those changes what this
project is, and it will be declined regardless of what it improves.

The proxy stays stateless. State is re-derived per request by replaying the visible
history. That is what makes concurrency safe and decisions auditable.

### 2. Nothing text-like crosses into the controller

The meta level accepts three finite floats in range and raises on everything else. That
boundary is the central security property, and it is not a filter to be relaxed for
convenience. If you need more signal, widen the **sensor**, and keep the interface numeric.

### 3. If the controller changes, the golden traces change with it

```bash
cd packages/python && python tools/gen_golden_traces.py
cd ../rust && cargo test
```

Both languages must agree bit-exactly. A pull request that changes controller behaviour and
leaves `packages/rust/tests/golden/traces.jsonl` untouched will fail CI, and that is
working as intended.

**Never hand-edit the traces file.** Regenerate it.

### 4. Every number is a measured output

This is the one that gets enforced hardest, and it applies to the README, the docs, the
issue you file and the release note.

- **A figure that is not a script output does not go in.** Not an estimate, not a
  reasonable-sounding round number.
- **A number travels with its qualifier**, in the same sentence or the one beside it.
  "4.1% to 20.2%" needs "on the verbatim-loop battery, across seven model families".
  Latency needs its scope, and the three latency figures are not interchangeable.
- **Never round up.** The flagship is `$0.1669`, not `$0.1670`.
- **Never "all".** The validation result is 15 of 16 cells, and any statement of it carries
  13/16 at p<.05 and the null cell.
- **No fabricated social proof.** No reviews, testimonials, logos, user counts, download
  counts or star ratings. None exist for this project, and none will be invented, including
  as placeholder text.

CI enforces the mechanical parts of this on every push. If the claims check fails your pull
request, it is telling you a published figure and your text disagree.

### 5. Limits are stated flatly, not hidden and not performed

Known limits belong in [docs/LIMITS.md](docs/LIMITS.md), written plainly. The null cell,
the sensor's recall gap and the inconclusive soak phase all sit there. State them as facts.

## Pull requests

- Branch from `main`.
- One concern per pull request.
- Tests for behaviour changes. If the controller moved, regenerate the golden traces.
- Run the suites for whatever you touched before pushing.
- Explain **why**, not only what. The diff shows what.

Commit messages: a short imperative subject, a body if the reasoning is not obvious.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licensing

Contributions are licensed under [Apache-2.0](LICENSE), matching the project. There is no
CLA.
