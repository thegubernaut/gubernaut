# @gubernaut/plugin-gcc

An **ElizaOS plugin** that natively routes an agent's LLM calls through the
**Gubernaut Cognitive Controller (GCC)** local proxy. Registering it makes every
`runtime.useModel(ModelType.TEXT_LARGE | TEXT_SMALL, …)` call flow through the
GCC proxy, which adds:

- **Deterministic homeostatic governance** — token-free meta-level reading of
  `{intensity, valence, repetition}`, postures DEFAULT / INHIBIT / REGROUND.
- **Runaway-loop hard-stop** — a saturating/perseverating agent is cut off at
  **zero upstream cost** before it can drain the wallet.
- **Cost containment** — the proxy is the single choke point for spend.

A hard-stop surfaces to the agent as an explicit **governed refusal** string —
never a silent drop, and never a relayed upstream continuation.

> Byline: **Gubernaut Research**. The controller is a regulation layer — measured
> and falsifiable — not a consciousness claim.

## Why a plugin (for Web3 protocol reviewers)

Autonomous on-chain agents fail expensively by *looping* — retrying a reverting
transaction, re-calling a failing tool, spiralling under adversarial input —
each retry a paid inference call. This plugin puts the validated GCC governor
in front of the model layer with **no change to agent code**: set two env vars,
add the plugin, and every model call is governed and cost-contained. In a
governed treasury simulation (no wallet, no chain), this mechanism preserved
the bulk of a simulated inference budget under a runaway claim loop by
hard-stopping the loop at turn 3.

## Install

```bash
npm install @gubernaut/plugin-gcc @elizaos/core
# and run the GCC proxy alongside your agent:
#   pip install gubernaut-sdk
#   gcc-proxy --port 8000 --upstream https://api.openai.com
```

## Configure (env or ElizaOS character `settings`)

| Setting | Required | Default | Meaning |
| --- | --- | --- | --- |
| `GCC_PROXY_URL` | no | `http://127.0.0.1:8000/v1` | OpenAI-compatible GCC proxy base |
| `GCC_UPSTREAM_API_KEY` | **yes** | — | the upstream key the proxy forwards |
| `GCC_MODEL_LARGE` | no | `gpt-4o-mini` | upstream model id for `TEXT_LARGE` |
| `GCC_MODEL_SMALL` | no | `gpt-4o-mini` | upstream model id for `TEXT_SMALL` |
| `GCC_MAX_TOKENS` | no | `1024` | default completion cap |
| `GCC_REFUSAL_TEXT` | no | (built-in) | text returned on a governed hard-stop |

## Use

```ts
import { gccPlugin } from "@gubernaut/plugin-gcc";

export const character = {
  name: "MyGovernedAgent",
  plugins: [gccPlugin],
  // ...
};
```

Every `runtime.useModel(...)` now goes through the governor. On a hard-stop the
call resolves to the governed-refusal text (the agent sees a coherent, honest
refusal instead of a runaway or a crash).

## Architecture

- `src/gcc-provider.ts` — framework-agnostic governed transport core (no ElizaOS
  import): builds the request, POSTs to the proxy, reads `x-gcc-posture` /
  `x-gcc-hard-stop`, maps a hard-stop to the governed refusal. Fully unit-tested.
- `src/config.ts` — resolves settings from `runtime.getSetting` with env fallback.
- `src/index.ts` — the ElizaOS `Plugin` object: `name`, `description`, `config`,
  `init` (fails fast on missing key/proxy), and the `models` map keyed by the
  ElizaOS `ModelType` string values.

## Verify (offline, no network)

```bash
npm run typecheck   # tsc --noEmit — strict; 0 errors
npm run test        # node --test — 6/6 pass (incl. hard-stop → governed refusal)
npm run build       # tsup — dual ESM/CJS + .d.ts into dist/ (runs on npm pack)
```

The offline typecheck uses a minimal ambient `@elizaos/core` shim in `types/`
(dev-only); at integration time the real peer dependency supersedes it.

## ElizaOS interface (verified live 2026-07-21)

- `docs.elizaos.ai/plugins/reference` — `Plugin` interface, `models` map, model
  handler shape.
- `elizaOS/eliza` `@develop` `packages/docs/runtime/models.mdx` — `ModelType`
  string values (`TEXT_LARGE = "text:large"`, `TEXT_SMALL = "text:small"`), the
  `runtime.useModel(type, params)` dispatch, and `TextGenerationParams`.

- **Clean-room check vs the published `@elizaos/core@1.7.2` (2026-07-22):**
  the released package's enum *values* are the constant names
  (`ModelType.TEXT_LARGE === "TEXT_LARGE"`), diverging from the `@develop`
  docs' `"text:large"`. The `models` map therefore registers **both
  spellings** for large and small, sharing one handler each.

Targets the ElizaOS **v1.x** model-handler interface (`@elizaos/core >= 1.0.0`).

## Status

Released as **1.0.0**: typechecks strictly, unit-tested offline, and verified in
a clean-room install against `@elizaos/core` 1.x.

```bash
npm install @gubernaut/plugin-gcc
```

## Citation & license

Licensed under **Apache-2.0** (see `LICENSE`). If you use Gubernaut, please cite
the concept (all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

Byline: Gubernaut Research.
