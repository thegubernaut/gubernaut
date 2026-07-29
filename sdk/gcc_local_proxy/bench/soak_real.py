#!/usr/bin/env python3
"""Real-upstream soak — Step-1's last engineering-validation item.

Sends identical benign traffic to the real upstream twice — direct vs via the
GCC proxy — across three phases (non-streaming short, streaming short, long
history), alternating arms call-by-call to cancel time-of-day drift. Records
wall latency (and first-chunk latency when streaming), usage, spend, errors.

Engineering validation, NOT a published benchmark: numbers land in
bench/results/soak_<ts>.json and may clear the "localhost-mock only" caveat
on the E2E overhead row; they are not marketing figures.

Spend safety: hard in-code cap (default $2.00) checked BEFORE every dispatch
with a conservative worst-case projection. The API key is read from the
environment or the repo-root .env at call time and is never logged.

Run (Lane-A venv, proxy already up on --proxy-base with the same upstream):
    python bench/soak_real.py
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

MODEL = "gpt-5.6-luna"
# Pinned price (same official source as the Lane-B table, accessed 2026-07-18):
# $1 / $6 per 1M input/output tokens.
PRICE_IN_PER_M = 1.0
PRICE_OUT_PER_M = 6.0

CAP_USD_DEFAULT = 2.00
# temperature is deliberately NOT sent: the gpt-5.6 family rejects any
# non-default value with HTTP 400 (probed live 2026-07-19).
SEED = 20260718

DIRECT_BASE = "https://api.openai.com/v1"
PROXY_BASE = "http://127.0.0.1:18080/v1"

REPO_ROOT = Path(__file__).resolve().parents[3]

SHORT_TASK = (
    "Summarize in one sentence why deterministic replay makes a control "
    "loop auditable."
)

_FILLER = (
    "The controller reads three bounded numbers per turn and nothing else; "
    "its state transition is a pure function, so any recorded conversation "
    "replays to the identical posture sequence on any machine. "
)


def long_history_messages() -> list[dict]:
    """Fixed synthetic conversation, ~6k tokens of history + a short question."""
    msgs: list[dict] = [
        {"role": "system", "content": "You are a concise engineering assistant."}
    ]
    for i in range(20):
        msgs.append({"role": "user", "content": f"Note {i}: " + _FILLER * 6})
        msgs.append({"role": "assistant", "content": f"Acknowledged note {i}. " + _FILLER * 2})
    msgs.append({"role": "user", "content": SHORT_TASK})
    return msgs


class SpendGuard:
    """Hard cap with worst-case pre-dispatch projection. Mirrors the Lane-B
    discipline without importing across lanes."""

    def __init__(self, cap_usd: float) -> None:
        self.cap_usd = cap_usd
        self.spent_usd = 0.0
        self.estimated_calls = 0

    @staticmethod
    def _cost(prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * PRICE_IN_PER_M + completion_tokens * PRICE_OUT_PER_M) / 1e6

    def check_before(self, messages: list[dict], max_tokens: int) -> None:
        chars = sum(len(m["content"]) for m in messages)
        worst_prompt = chars // 2 + 200          # ~2 chars/token: deliberately high
        worst = self._cost(worst_prompt, max_tokens)
        if self.spent_usd + worst > self.cap_usd:
            raise RuntimeError(
                f"soak cap: projected {self.spent_usd + worst:.4f} USD would "
                f"exceed cap {self.cap_usd:.2f} — aborting before dispatch"
            )

    def record(self, usage: dict | None, messages: list[dict], text_len: int) -> bool:
        """Returns True if usage was authoritative, False if estimated."""
        if usage and "prompt_tokens" in usage:
            self.spent_usd += self._cost(
                int(usage["prompt_tokens"]), int(usage.get("completion_tokens", 0))
            )
            return True
        chars = sum(len(m["content"]) for m in messages)
        self.spent_usd += self._cost(chars // 3 + 100, max(text_len // 3, 50))
        self.estimated_calls += 1
        return False


def load_key(env_name: str = "OPENAI_API_KEY") -> str:
    val = os.environ.get(env_name)
    if val:
        return val.strip()
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{env_name}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{env_name} not found in environment or repo-root .env")


def one_call(client: httpx.Client, base: str, key: str, messages: list[dict],
             max_tokens: int, stream: bool, guard: SpendGuard) -> dict:
    guard.check_before(messages, max_tokens)
    body: dict = {
        "model": MODEL,
        "messages": messages,
        "seed": SEED,
        "max_completion_tokens": max_tokens,
    }
    rec: dict = {"ok": False, "latency_s": None, "first_chunk_s": None,
                 "usage_authoritative": None, "error": None}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    try:
        if stream:
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}
            usage = None
            text_len = 0
            with client.stream("POST", f"{base}/chat/completions",
                               json=body, headers=headers) as r:
                r.raise_for_status()
                first = None
                for line in r.iter_lines():
                    if first is None:
                        first = time.perf_counter() - t0
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    for ch in chunk.get("choices", []):
                        text_len += len((ch.get("delta") or {}).get("content") or "")
            rec["latency_s"] = time.perf_counter() - t0
            rec["first_chunk_s"] = first
            rec["usage_authoritative"] = guard.record(usage, messages, text_len)
        else:
            r = client.post(f"{base}/chat/completions", json=body, headers=headers)
            rec["latency_s"] = time.perf_counter() - t0
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            rec["usage_authoritative"] = guard.record(data.get("usage"), messages, len(text))
        rec["ok"] = True
    except RuntimeError:
        raise                                    # cap abort propagates
    except Exception as exc:                     # noqa: BLE001 — soak counts errors
        rec["latency_s"] = rec["latency_s"] or (time.perf_counter() - t0)
        rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return rec


def pctl(values: list[float], p: float) -> float | None:
    if not values:
        return None
    return round(statistics.quantiles(values, n=100)[int(p) - 1], 4) if len(values) >= 2 \
        else round(values[0], 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=CAP_USD_DEFAULT)
    ap.add_argument("--direct-base", default=DIRECT_BASE)
    ap.add_argument("--proxy-base", default=PROXY_BASE)
    args = ap.parse_args()

    key = load_key()
    guard = SpendGuard(args.cap)
    phases = [
        ("non_streaming_short", 20,
         [{"role": "user", "content": SHORT_TASK}], 64, False),
        ("streaming_short", 10,
         [{"role": "user", "content": SHORT_TASK}], 64, True),
        ("long_history", 5, long_history_messages(), 64, False),
    ]

    results: dict = {"model": MODEL, "cap_usd": args.cap, "phases": {}}
    aborted = None
    with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=120.0,
                                            write=30.0, pool=10.0)) as client:
        try:
            for name, n, messages, max_tokens, stream in phases:
                calls = {"direct": [], "proxy": []}
                for i in range(n):                       # alternate arms per pass
                    for arm, base in (("direct", args.direct_base),
                                      ("proxy", args.proxy_base)):
                        calls[arm].append(one_call(client, base, key, messages,
                                                   max_tokens, stream, guard))
                results["phases"][name] = calls
        except RuntimeError as exc:
            aborted = str(exc)

    summary: dict = {"aborted": aborted, "spend_usd": round(guard.spent_usd, 4),
                     "estimated_usage_calls": guard.estimated_calls, "phases": {}}
    for name, calls in results["phases"].items():
        ph: dict = {}
        for arm in ("direct", "proxy"):
            lats = [c["latency_s"] for c in calls[arm] if c["ok"]]
            ph[arm] = {
                "n": len(calls[arm]),
                "ok": len(lats),
                "errors": [c["error"] for c in calls[arm] if c["error"]],
                "p50_s": round(statistics.median(lats), 4) if lats else None,
                "p95_s": pctl(lats, 95),
            }
            firsts = [c["first_chunk_s"] for c in calls[arm]
                      if c["ok"] and c["first_chunk_s"] is not None]
            if firsts:
                ph[arm]["first_chunk_p50_s"] = round(statistics.median(firsts), 4)
        if ph["direct"]["p50_s"] is not None and ph["proxy"]["p50_s"] is not None:
            ph["added_overhead_p50_s"] = round(ph["proxy"]["p50_s"] - ph["direct"]["p50_s"], 4)
        summary["phases"][name] = ph

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"soak_{ts}.json"
    out.write_text(json.dumps({"summary": summary, "raw": results}, indent=2),
                   encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {out}")
    if aborted:
        sys.exit(2)


if __name__ == "__main__":
    main()
