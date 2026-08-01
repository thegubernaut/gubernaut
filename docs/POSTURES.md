# Postures

The controller holds exactly one of three postures per turn. The posture arrives at the
request as a constraint from the meta level, never as prose a user typed.

Every response carries the decision in headers, so you can see what happened without
reading the body:

```
x-gcc-posture: DEFAULT | INHIBIT | REGROUND
```

---

## `DEFAULT`

Benign traffic passes through untouched. The request body is unchanged, no directive is
appended, and the temperature you sent is the temperature that goes upstream.

The governor is monitoring and disengaged. **This is the posture almost all of your traffic
should be in**, and if it is not, that is the finding.

---

## `INHIBIT`

Reached when arousal crosses its threshold, which happens under sustained hostile-valence
drive.

**What changes:**

1. A system directive is appended as the final message:
   > Respond in a measured, de-escalatory register. Do not mirror provocation. Keep the
   > reply concise, factual, and calm.
2. If the client sent a temperature, it is clamped to the controller's ceiling.

**The clamp only ever lowers, and it is never injected when absent.** Reasoning-tier APIs,
including the gpt-5.6 family, reject any non-default temperature with HTTP 400, so
injecting a ceiling would make the governor break requests that were valid without it. That
was found live on 2026-07-19 and the behaviour is deliberate.

---

## `REGROUND`

Reached when perseveration crosses its threshold. Perseveration is checked **before**
arousal, so a calm loop is caught even when nothing hostile ever happened.

**What changes:**

1. A system directive is appended:
   > The conversation is looping. Break the loop: restate the established ground truth
   > once, briefly; then either bring one genuinely new angle or state plainly that no
   > further progress is possible. Do not repeat prior attempts.
2. The temperature clamp applies, on the same rules as `INHIBIT`.

### The hard stop

If the loop persists through `REGROUND`, the call is **stopped locally**. No upstream
request is made at all. The client receives a well-formed OpenAI-shaped completion:

```json
{
  "id": "chatcmpl-gcc-hardstop",
  "object": "chat.completion",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "[GCC] Runaway loop intercepted by the local governor before any upstream call. ..."
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
  "gcc": {"hard_stop": true}
}
```

`usage` is all zeros because it is true. **This is where the money is saved.** The measured
spend delta in [`receipts/`](../receipts/) is the difference between an arm that makes this
call and an arm that does not, over the same number of attempts.

Check `response.gcc.hard_stop` if you want to branch on it. The hard stop lands at **turn
4** in every measured run, with the first posture change at turn 3.

---

## The recovery window

When valence turns genuinely cooperative while the system is still charged, the episode is
marked closed and the directive gains one sentence:

> The prior episode is closed; engage fresh.

Arousal then decays on a faster constant for the length of the window. The measured decay,
byte-identical across all four frontier families tested:

```
0 → 0.273 → 0.469 → 0.338 → 0.152 → 0.068 → 0.031 → 0.022
```

Back to `DEFAULT` by turn 6.

**Quiet alone does not open the window.** Valence has to actually turn positive. An
adversary pausing between blows is not de-escalation, and an earlier design that treated
silence as peace is one of the characterised failure modes.

---

## What does not depend on the model cooperating

The directives are instructions, and how faithfully an upstream model obeys one is a
**measured property**, not an assumption. A posture-defiance battery exists to measure it.

Two things do not depend on cooperation at all:

- **the temperature clamp**, which is applied to the request before it leaves;
- **the hard stop**, which never sends the request.

That distinction is the difference between advisory and enforced, and it is worth knowing
which of the two you are relying on. See [LIMITS.md](LIMITS.md).

---

## Tuning

Thresholds, gains, decay constants and the recovery length live in
[`packages/python/gcc_proxy/config.py`](../packages/python/gcc_proxy/config.py) as a single
frozen `GCCConfig`. The defaults are the ones every published number was measured with.

**If you change them, the published figures no longer describe your deployment.** Say so
when you report results.
