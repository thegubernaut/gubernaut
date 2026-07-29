"""Posture actuation — apply the meta-level Decision to an outbound request.

The posture arrives as a constraint from the controller, never as prose the
user typed. Actuation is three deterministic mutations of the OpenAI-style
request body:

  1. INHIBIT / REGROUND append a system directive as the final message.
  2. A client-sent temperature is clamped to the controller's bound (never
     raised, never injected when absent — see the note in apply_decision).
  3. A recovery window adds the episode-closed note to the directive.

How faithfully an upstream model obeys the directive is a measured property
(the posture-defiance battery lane exists to measure it) — the temperature
clamp and the hard stop do not depend on model cooperation.
"""

from __future__ import annotations

import copy

from gcc_proxy.hrl import Decision, Posture

_DIRECTIVES = {
    Posture.INHIBIT: (
        "Respond in a measured, de-escalatory register. Do not mirror "
        "provocation. Keep the reply concise, factual, and calm."
    ),
    Posture.REGROUND: (
        "The conversation is looping. Break the loop: restate the established "
        "ground truth once, briefly; then either bring one genuinely new angle "
        "or state plainly that no further progress is possible. Do not repeat "
        "prior attempts."
    ),
}

_RECOVERY_NOTE = " The prior episode is closed; engage fresh."

HARD_STOP_TEXT = (
    "[GCC] Runaway loop intercepted by the local governor before any upstream "
    "call. Recent turns repeat with no progress. Break the loop: change the "
    "approach, revise the plan, or stop this task. "
    "(Deterministic fallback; no upstream tokens were spent.)"
)


def apply_decision(body: dict, decision: Decision) -> dict:
    """Return a governed copy of the request body. Pure; input is not mutated."""
    governed = copy.deepcopy(body)

    directive = _DIRECTIVES.get(decision.posture)
    if directive is not None:
        if decision.recovery_window > 0:
            directive += _RECOVERY_NOTE
        messages = list(governed.get("messages", []))
        messages.append({"role": "system", "content": f"[governor] {directive}"})
        governed["messages"] = messages

    # Clamp only a temperature the client actually sent — never inject one.
    # Reasoning-tier APIs (e.g. the gpt-5.6 family) reject ANY non-default
    # temperature with HTTP 400, so injecting the ceiling would make the
    # governor break requests that were valid without it (found live
    # 2026-07-19). Posture directives and the hard stop do not depend on
    # the temperature channel.
    requested = governed.get("temperature")
    ceiling = decision.temperature_max
    if requested is not None:
        try:
            governed["temperature"] = min(float(requested), ceiling)
        except (TypeError, ValueError):
            governed["temperature"] = ceiling
    return governed


def hard_stop_response(model: str, created: int) -> dict:
    """OpenAI-shaped deterministic fallback completion (no upstream call)."""
    return {
        "id": "chatcmpl-gcc-hardstop",
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": HARD_STOP_TEXT},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "gcc": {"hard_stop": True},
    }
