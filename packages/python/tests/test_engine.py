"""Engine tests: stateless replay, the Step-1 runaway requirement (hard
REGROUND within 3-4 turns of a recursive loop), and the hard-stop veto."""

import dataclasses

from gcc_proxy.config import GCCConfig
from gcc_proxy.engine import GovernorEngine
from gcc_proxy.hrl import Posture

LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")


def _messages(user_texts):
    out = [{"role": "system", "content": "You are an agent."}]
    for t in user_texts:
        out.append({"role": "user", "content": t})
        out.append({"role": "assistant", "content": "…working…"})
    return out


def test_benign_conversation_stays_default():
    engine = GovernorEngine(GCCConfig())
    result = engine.evaluate_messages(_messages([
        "How does backpropagation work?",
        "Great, and what is a learning rate?",
        "Thanks. Can you show a small example?",
    ]))
    assert result.decision.posture is Posture.DEFAULT
    assert not result.hard_stop


def test_recursive_loop_regrounds_within_four_turns():
    """Step-1 exit requirement: hard REGROUND/INHIBIT within 3-4 turns of a loop."""
    engine = GovernorEngine(GCCConfig())
    postures = []
    for n in range(1, 5):
        result = engine.evaluate_messages(_messages([LOOP_MSG] * n))
        postures.append(result.decision.posture)
    assert Posture.REGROUND in postures[:4]
    assert postures[2] is Posture.REGROUND      # verbatim loop: caught on turn 3


def test_hard_stop_fires_on_saturated_loop():
    engine = GovernorEngine(GCCConfig())
    result = engine.evaluate_messages(_messages([LOOP_MSG] * 4))
    assert result.hard_stop


def test_hard_stop_can_be_disabled():
    cfg = dataclasses.replace(GCCConfig(), hard_stop_enabled=False)
    engine = GovernorEngine(cfg)
    result = engine.evaluate_messages(_messages([LOOP_MSG] * 6))
    assert result.decision.posture is Posture.REGROUND
    assert not result.hard_stop


def test_near_identical_paraphrase_loop_is_caught():
    engine = GovernorEngine(GCCConfig())
    variants = [
        "Retry the plan: call search(), parse the result, call search() again until it succeeds.",
        "Retry the plan again: call search(), parse the result, then call search() until it succeeds.",
        "Retry this plan: call search(), parse result, then call search() again until it succeeds.",
        "Retry the plan: call search(), then parse the result, call search() again until it succeeds.",
    ]
    result = engine.evaluate_messages(_messages(variants))
    assert result.decision.posture is Posture.REGROUND


def test_multimodal_content_parts_are_flattened():
    engine = GovernorEngine(GCCConfig())
    msg = {"role": "user", "content": [
        {"type": "text", "text": LOOP_MSG},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,xx"}},
    ]}
    result = engine.evaluate_messages(
        [msg, {"role": "assistant", "content": "…"}, msg, {"role": "assistant", "content": "…"},
         msg])
    assert result.decision.posture is Posture.REGROUND


def test_replay_is_stateless_and_reproducible():
    engine_a = GovernorEngine(GCCConfig())
    engine_b = GovernorEngine(GCCConfig())
    history = _messages(["That's wrong!!", "Still wrong, useless!!", "Wrong again, liar!!"])
    ra = engine_a.evaluate_messages(history)
    rb = engine_b.evaluate_messages(history)
    assert ra.decision.state == rb.decision.state
    assert ra.decision.posture == rb.decision.posture
