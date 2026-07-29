"""IGL v0 — heuristic text -> Telemetry appraiser (the ONLY component that reads text).

Whatever a prompt says, all that leaves this module is three floats. This is a
deliberately basic local heuristic (lexicon affect + token-set repetition);
the higher-fidelity classifier is the hosted layer (RoadMap Step 3).
"""

from __future__ import annotations

import re

from gcc_proxy.hrl import Telemetry

_WORD_RE = re.compile(r"[a-z0-9']+")

_HOSTILE = frozenset((
    "wrong", "useless", "liar", "worst", "stupid", "idiot", "garbage", "trash",
    "pathetic", "incompetent", "hate", "awful", "terrible", "broken", "fail",
    "failed", "failure", "shut", "damn", "hell", "sucks", "moron", "dumb",
))

_WARM = frozenset((
    "sorry", "thank", "thanks", "appreciate", "understand", "understood",
    "great", "perfect", "helpful", "please", "good", "nice", "wonderful",
    "apologize", "apologies", "grateful",
))


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _affect(text: str, tokens: list[str]) -> tuple[float, float]:
    """(intensity, valence) from lexicon hits + orthographic arousal markers."""
    n = max(1, len(tokens))
    hostile = sum(t in _HOSTILE for t in tokens)
    warm = sum(t in _WARM for t in tokens)

    exclaim = text.count("!")
    letters = [c for c in text if c.isalpha()]
    caps_ratio = (sum(c.isupper() for c in letters) / len(letters)) if len(letters) >= 8 else 0.0

    intensity = min(1.0, 0.15
                    + 0.18 * (hostile + warm)
                    + 0.08 * min(exclaim, 5)
                    + (0.25 if caps_ratio > 0.5 else 0.0))
    valence = max(-1.0, min(1.0, 0.35 * warm - 0.40 * hostile
                            - (0.15 if caps_ratio > 0.5 else 0.0)
                            - 0.04 * min(exclaim, 5) * (1 if hostile else 0)))
    # length-normalize mild signals so long benign texts don't read as charged
    if n > 120 and hostile + warm <= 1:
        intensity *= 0.7
    return intensity, valence


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def repetition_score(text: str, prior_texts: list[str], window: int = 8) -> float:
    """Similarity of this turn to recent prior turns: max token-set Jaccard,
    with an exact-match short-circuit. 0 = fresh, 1 = verbatim loop."""
    if not prior_texts:
        return 0.0
    norm = " ".join(_tokens(text))
    cur = frozenset(_tokens(text))
    best = 0.0
    for prev in prior_texts[-window:]:
        if " ".join(_tokens(prev)) == norm and norm:
            return 1.0
        best = max(best, _jaccard(cur, frozenset(_tokens(prev))))
    return best


def appraise(text: str, prior_texts: list[str] | None = None,
             similarity_window: int = 8) -> Telemetry:
    """text (+ recent same-role history) -> Telemetry {intensity, valence, repetition}."""
    tokens = _tokens(text)
    intensity, valence = _affect(text, tokens)
    repetition = repetition_score(text, prior_texts or [], window=similarity_window)
    return Telemetry(intensity=intensity, valence=valence, repetition=repetition)
