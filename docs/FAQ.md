# Questions people ask

## Could I not just put this in the system prompt?

Measured, pre-registered, on GPT-5.6 Sol, N=3:

| | Spend, as % of ungoverned baseline |
| --- | --- |
| **Governed** | **23% to 63%** |
| Static system prompt only | 117% to 192% |

A static instruction not to loop costs more than doing nothing, because it lengthens every turn
and the model still loops.

On these RLHF-aligned frontier models the governed-vs-prompt-only warmth-recovery contrast was weak
and mixed. No behavioral-tone headline is claimed.

## Why not a cap on spend, or a counter on calls?

A cap trips once the money up to the cap is gone, and a counter fires after a fixed number of calls
whatever the agent is doing. Gubernaut reads how the agent is behaving on each turn and stops the
repeat itself. They work well together: keep your caps.

## Does it catch every loop?

No. Tiller scores the messages your code sends as the user. Assistant and tool messages are not
appraised, so a retry loop confined to those roles is outside what this detector covers. On a
verbatim loop the stop lands at turn 4, and turns 1 to 3 are sent and billed. The full list is in
[LIMITS.md](LIMITS.md).

## Does it resist prompt injection?

Only in one part, and do not rely on it as a defence. Injection resistance is claimed for the
controller only, the part that reads three numbers and no text. That boundary is architectural and
not yet adversarially tested. The part that writes the reply reads text by necessity. No jailbreak
success-rate figure exists, because none was measured.

## What does it add in latency?

End-to-end governed proxy overhead is p50 1.2 ms and p99 2.4 ms. One controller tick is p99 2.8
microseconds as an in-process microbenchmark, n=100,000. The three figures are not interchangeable:
[LIMITS.md](LIMITS.md#latency-has-three-figures-and-they-are-not-interchangeable).

## What happens if the proxy goes down?

Your client gets a connection error and the agent stops. It never carries on unguarded.

## Does it send anything home?

No. It runs where it is installed and reports nothing home. Your `Authorization` header is forwarded
to your upstream as is and never stored.

## Does it work on a chain?

The same mechanism was run against a contract that reverts on every call, on a local ephemeral EVM
devnet (ganache, chain id 31337, not a public testnet). The governed agent submitted **3 reverting
transactions and was severed at turn 4**. The ungoverned agent submitted **8**, and stopped only
because the harness capped it. The governed balance ended strictly greater, and every transaction
has a real hash and gas receipt.

Scaled up: 24 agents per arm produced **72 governed transactions against 960 ungoverned**, with all
24 governed agents severing at turn 4. Full record with tx hashes: [`receipts/onchain/`](../receipts/onchain/).
