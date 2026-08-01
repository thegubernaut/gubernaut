# On-chain receipts

**Gubernaut intercepted a runaway on-chain retry loop at turn 4.** Two runs, real
transactions, real gas, real hashes.

> **The substrate, stated up front and never omitted.** A **local ephemeral EVM devnet**:
> ganache, chain id **31337**. **This is not a public testnet and not a mainnet.** Blocks,
> gas and balances are real within that devnet and the chain was disposed of afterwards.
> Every figure below is scoped to it.

The agent is ElizaOS running [`@gubernaut/plugin-gcc`](../../packages/node/) against a
contract engineered to fail on every call. A failing on-chain call is the purest form of
the loop this governor exists to stop: the agent retries, every retry burns gas, and
nothing about the failure teaches it to stop.

---

## Run 1 · the intercept

[`devnet_intercept.json`](devnet_intercept.json) · 2026-07-21 · contract loops to
out-of-gas on every call, 400,000 gas per attempt

| | Ungoverned | Governed |
|---|---|---|
| Transactions submitted | **8** | **3** |
| All reverted | yes | yes |
| Severed at | never | **turn 4** |
| Remaining balance | lower | **strictly greater** |

Every transaction has a hash, a block number, a `gasUsed` and a `status: reverted` receipt
in the JSON. The sever bracket records the exact boundary:

- last on-chain transaction the governed agent sent: `0xf0abd66a...` in block 12
- the first transaction the governed agent **never sent**: `0xb24597af...`, which the
  ungoverned agent did send

That pair is the whole claim, and it is checkable. One agent's turn-4 transaction exists on
the chain; the other's does not.

The host survived and the chain stayed alive. A benign request after the sever was answered
normally, so the governor stopped the loop rather than the agent.

**The ungoverned arm stopped at 8 because the harness capped it, not because the agent
stopped.** Nothing in a reverting retry loop terminates on its own. The gap is a floor.

---

## Run 2 · treasury under stress, and concurrency

[`devnet_treasury.json`](devnet_treasury.json) · 2026-07-24 · 3 revert patterns
(out-of-gas, explicit `REVERT`, `INVALID` opcode), 40-attempt cap per agent

**Phase A, 24 agents per arm:**

| | Ungoverned | Governed |
|---|---|---|
| Transactions | **960** (40 each, the cap) | **72** (3 each) |
| Severed | none | **all 24, every one at turn 4** |
| Treasury remaining | 20% | 94% |

Every governed agent severed at turn 4. Not a mean of 4, not around 4. **The same turn,
every agent**, because the controller is input-deterministic and every agent saw the same
shape of failure.

> **The percentages are a per-run artifact and are not a portable headline.** Gas
> preserved on a devnet depends on the gas limit, the gas price and EIP-1559 base-fee
> decay, all of which were fixed by this harness. The transaction counts and the fact that
> the governed balance ends strictly greater are the durable results. Quote those.

**Phase B, 210 concurrent agents:** 210 completed, **210 severed, 0 drops**, across all
three revert patterns, in 41 seconds. The chain was alive at block 1665 afterwards and the
host exited 0.

That matters because the governor is stateless by construction. There is no shared session
to contend on, so 210 concurrent agents is 210 independent replays, and the result is what
statelessness predicts.

---

## What this does and does not show

**Does:** the governor severs an on-chain retry loop before the wallet drains; the sever
turn is deterministic across agents and across revert patterns; it holds under concurrency;
and the mechanism works through the ElizaOS plugin with no change to agent code.

**Does not:** say anything about mainnet gas economics, MEV, a public testnet's mempool
behaviour, or any contract other than the deliberately failing ones used here. It is not a
security audit of the contracts, which exist only to fail.

---

## Reproduce it

`scripts/` holds the harness verbatim. It needs ganache on 31337, the proxy from
[`packages/python`](../../packages/python/), and the plugin from
[`packages/node`](../../packages/node/).

```bash
npx ganache --chain.chainId 31337 --wallet.deterministic
python -m gcc_proxy --upstream http://127.0.0.1:18081   # or a real upstream
node scripts/leg2_devnet.mjs
node scripts/leg4b_treasury.mjs
```

`probe_chain.mjs` checks the chain is reachable and the contracts are deployed before
either run. `proxy_stack.py` brings up the mock upstream and the proxy together.

Post what you get, matching or not:
[reproduction report](https://github.com/thegubernaut/gubernaut/issues/new?template=reproduction.yml).

---

*No API spend. Mock upstream, local devnet. Byline: Gubernaut Research.*
