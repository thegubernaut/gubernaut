"""GovernorEngine — stateless deterministic replay over a chat history.

The proxy holds no session store. Each /v1/chat/completions request carries the
full visible history, so the engine re-derives the controller state by
replaying every user-role turn through the HRL from a fresh state. Same
history in, same Decision out — across restarts, across machines. This is what
makes every governed decision replayable and auditable.

The engine also implements the runaway hard stop (the spend veto): when the
controller has commanded REGROUND and the loop signal stays saturated anyway,
the proxy is entitled to short-circuit the upstream call entirely.
"""

from __future__ import annotations

from dataclasses import dataclass

from gcc_proxy.config import GCCConfig
from gcc_proxy.hrl import ControllerState, Decision, HomeostaticLoop, Posture, Telemetry
from gcc_proxy.telemetry import appraise


@dataclass(frozen=True)
class EngineResult:
    decision: Decision
    telemetry: Telemetry          # telemetry of the latest user turn
    hard_stop: bool               # True: do not call upstream; return fallback
    replayed_turns: int


class GovernorEngine:
    def __init__(self, config: GCCConfig | None = None) -> None:
        self.cfg = config or GCCConfig()
        self.hrl = HomeostaticLoop(self.cfg)

    def evaluate_messages(self, messages: list[dict]) -> EngineResult:
        """Replay user-role turns of an OpenAI-style messages array; decide for
        the latest turn. Non-string content (multimodal parts) is flattened to
        its text parts; system/assistant/tool turns are not appraised."""
        user_texts = [_content_text(m) for m in messages
                      if m.get("role") == "user"]
        user_texts = [t for t in user_texts if t is not None]
        return self.evaluate_turns(user_texts)

    def evaluate_turns(self, user_texts: list[str]) -> EngineResult:
        cfg = self.cfg
        turns = user_texts[-cfg.replay_window:]
        state = ControllerState()
        decision = self.hrl.update(state, Telemetry(0.0, 0.0, 0.0))
        tel = Telemetry(0.0, 0.0, 0.0)

        saturated_regrounds = 0
        for i, text in enumerate(turns):
            tel = appraise(text, turns[:i], similarity_window=cfg.similarity_window)
            decision = self.hrl.update(state, tel)
            state = decision.state
            if (decision.posture is Posture.REGROUND
                    and tel.repetition >= cfg.hard_stop_repetition):
                saturated_regrounds += 1
            else:
                saturated_regrounds = 0

        hard_stop = (cfg.hard_stop_enabled
                     and saturated_regrounds >= cfg.hard_stop_turns)
        return EngineResult(decision=decision, telemetry=tel,
                            hard_stop=hard_stop, replayed_turns=len(turns))


def _content_text(message: dict) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # multimodal: concatenate text parts
        parts = [p.get("text", "") for p in content
                 if isinstance(p, dict) and p.get("type") == "text"]
        return " ".join(parts) if parts else None
    return None
