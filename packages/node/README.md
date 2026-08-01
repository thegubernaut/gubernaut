# @gubernaut/plugin-gcc

An **ElizaOS plugin** that routes an agent's LLM calls through the **Gubernaut Cognitive
Controller** local proxy. Registering it makes every
`runtime.useModel(ModelType.TEXT_LARGE | TEXT_SMALL, ...)` call flow through the governor,
which adds:

- **Deterministic homeostatic governance.** A token-free meta level reading
  `{intensity, valence, repetition}`, holding postures DEFAULT, INHIBIT and REGROUND.
- **Runaway-loop hard stop.** A saturating agent is cut off at **zero upstream cost**
  before it can drain the wallet.
- **Cost containment.** The proxy is the single choke point for spend.

A hard stop surfaces to the agent as an explicit **governed refusal** string. Never a
silent drop, and never a relayed upstream continuation.

```bash
npm install @gubernaut/plugin-gcc
```

Full project and receipts:
[github.com/thegubernaut/gubernaut](https://github.com/thegubernaut/gubernaut)

## Why a plugin, for Web3 protocol reviewers

Autonomous on-chain agents fail expensively by **looping**: retrying a reverting
transaction, re-calling a failing tool, spiralling under adversarial input, each retry a
paid inference call. This plugin puts the validated governor in front of the model layer
with **no change to agent code**. Set two environment variables, add the plugin, and every
model call is governed.

**It has been run against a chain.** On a local ephemeral EVM devnet (ganache, chain id
31337, not a public testnet) against a contract that reverts out-of-gas on every call, the
governed agent submitted **3 reverting transactions and was severed at turn 4**, while the
ungoverned agent submitted **8**. The governed account's remaining balance was strictly
greater, the Node host survived and exited 0, and every transaction has a real hash and
gas receipt.

The full record, including tx hashes and the sever bracket, is in
[`receipts/onchain/`](https://github.com/thegubernaut/gubernaut/tree/main/receipts/onchain).
**The percentage saved is a per-run artifact** of EIP-1559 base-fee decay on a local
devnet, so the transaction counts and the balance comparison are the claim, not a savings
percentage.

## Install

```bash
npm install @gubernaut/plugin-gcc @elizaos/core

# and run the governor alongside your agent:
pip install gubernaut-sdk
gcc-proxy --port 8000 --upstream https://api.openai.com
```

## Configure

Through environment variables or the ElizaOS character `settings`.

| Setting | Required | Default | Meaning |
| --- | --- | --- | --- |
| `GCC_PROXY_URL` | no | `http://127.0.0.1:8000/v1` | OpenAI-compatible proxy base |
| `GCC_UPSTREAM_API_KEY` | **yes** | | the upstream key the proxy forwards |
| `GCC_MODEL_LARGE` | no | `gpt-4o-mini` | upstream model id for `TEXT_LARGE` |
| `GCC_MODEL_SMALL` | no | `gpt-4o-mini` | upstream model id for `TEXT_SMALL` |
| `GCC_MAX_TOKENS` | no | `1024` | default completion cap |
| `GCC_REFUSAL_TEXT` | no | built-in | text returned on a governed hard stop |

## Use

```ts
import { gccPlugin } from "@gubernaut/plugin-gcc";

export const character = {
  name: "MyGovernedAgent",
  plugins: [gccPlugin],
  // ...
};
```

Every `runtime.useModel(...)` now goes through the governor. On a hard stop the call
resolves to the governed-refusal text, so the agent sees a coherent refusal rather than a
runaway or a crash.

## Architecture

- `src/gcc-provider.ts`, the framework-agnostic governed transport core with no ElizaOS
  import. Builds the request, posts to the proxy, reads `x-gcc-posture` and
  `x-gcc-hard-stop`, and maps a hard stop to the governed refusal. Fully unit-tested.
- `src/config.ts`, resolves settings from `runtime.getSetting` with environment fallback.
- `src/index.ts`, the ElizaOS `Plugin` object: `name`, `description`, `config`, `init`
  which fails fast on a missing key or proxy, and the `models` map keyed by the ElizaOS
  `ModelType` string values.

## Verify, offline and with no network

```bash
npm run typecheck   # tsc --noEmit, strict, 0 errors
npm run test        # node --test, includes hard-stop to governed refusal
npm run build       # tsup, dual ESM/CJS plus .d.ts into dist/
```

The offline typecheck uses a minimal ambient `@elizaos/core` shim in `types/`, which is
dev-only. At integration time the real peer dependency supersedes it.

## ElizaOS interface, verified live 2026-07-21

- `docs.elizaos.ai/plugins/reference` for the `Plugin` interface, the `models` map and the
  model handler shape.
- `elizaOS/eliza` `@develop`, `packages/docs/runtime/models.mdx`, for the `ModelType`
  string values (`TEXT_LARGE = "text:large"`, `TEXT_SMALL = "text:small"`), the
  `runtime.useModel(type, params)` dispatch, and `TextGenerationParams`.

**Clean-room check against the published `@elizaos/core@1.7.2`, 2026-07-22.** The released
package's enum *values* are the constant names (`ModelType.TEXT_LARGE === "TEXT_LARGE"`),
diverging from the `@develop` docs' `"text:large"`. The `models` map therefore registers
**both spellings** for large and small, sharing one handler each.

Targets the ElizaOS **v1.x** model-handler interface, `@elizaos/core >= 1.0.0`.

## Citation and license

Licensed under **Apache-2.0**. If you use Gubernaut, please cite the concept
(all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

No consciousness claims. This is a regulation layer, measured and falsifiable.
Byline: Gubernaut Research.
