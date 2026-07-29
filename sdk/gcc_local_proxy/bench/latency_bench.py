#!/usr/bin/env python3
"""Latency bench for the GCC local proxy (RoadMap Step-1 exit criteria).

Measures, and prints as script output (numbers discipline — figures exist only
as outputs of this script):

  1. META-DECISION latency — one HRL tick (budget: < 2 ms), and the full
     stateless replay a real request pays (12-turn history).
  2. END-TO-END proxy overhead — request via proxy minus request direct to the
     same mock upstream, on localhost (budget: < 50 ms; target well under the
     20-30 ms developer-bypass threshold).

Run from the lane venv:
    .venv\\Scripts\\python.exe ..\\bench\\latency_bench.py

Writes machine-readable results to bench/results/latency_YYYYMMDDTHHMMSSZ.json.
"""

from __future__ import annotations

import json
import platform
import statistics
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from gcc_proxy.config import GCCConfig
from gcc_proxy.engine import GovernorEngine
from gcc_proxy.hrl import ControllerState, HomeostaticLoop, Telemetry
from gcc_proxy.proxy import create_app

MOCK_PORT = 18081
PROXY_PORT = 18080

HISTORY = []
for i in range(6):
    HISTORY.append({"role": "user",
                    "content": f"Step {i}: analyse the dataset, then summarise fold {i} "
                               "and report anomalies with confidence intervals."})
    HISTORY.append({"role": "assistant", "content": "Working on it — partial results attached."})

COMPLETION = {
    "id": "chatcmpl-bench", "object": "chat.completion", "created": 1,
    "model": "bench-model",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}
_COMPLETION_BYTES = json.dumps(COMPLETION).encode()


async def mock_upstream(scope, receive, send):
    """Minimal ASGI upstream: drain the request, answer a canned completion."""
    if scope["type"] != "http":
        return
    while True:
        event = await receive()
        if event["type"] != "http.request" or not event.get("more_body"):
            break
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": _COMPLETION_BYTES})


def start_server(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError(f"server on :{port} failed to start")
        time.sleep(0.02)
    return server


def quantiles_us(samples_ns: list[int]) -> dict:
    s = sorted(samples_ns)
    n = len(s)
    pick = lambda q: s[min(n - 1, int(q * n))] / 1000.0
    return {"n": n, "mean_us": statistics.fmean(s) / 1000.0,
            "p50_us": pick(0.50), "p95_us": pick(0.95), "p99_us": pick(0.99),
            "max_us": s[-1] / 1000.0}


def bench_meta_decision() -> dict:
    cfg = GCCConfig()
    hrl = HomeostaticLoop(cfg)
    state = ControllerState()
    tel = Telemetry(0.7, -0.6, 0.3)

    tick = []
    for _ in range(100_000):
        t0 = time.perf_counter_ns()
        d = hrl.update(state, tel)
        tick.append(time.perf_counter_ns() - t0)
        state = ControllerState()  # keep the input state constant
        _ = d

    engine = GovernorEngine(cfg)
    replay = []
    for _ in range(5_000):
        t0 = time.perf_counter_ns()
        engine.evaluate_messages(HISTORY)
        replay.append(time.perf_counter_ns() - t0)

    return {"hrl_tick": quantiles_us(tick), "full_replay_12_turns": quantiles_us(replay)}


def bench_e2e_overhead(n: int = 300) -> dict:
    mock = start_server(mock_upstream, MOCK_PORT)
    cfg = GCCConfig(upstream_base=f"http://127.0.0.1:{MOCK_PORT}",
                    port=PROXY_PORT)
    proxy = start_server(create_app(cfg), PROXY_PORT)
    body = {"model": "bench-model", "messages": HISTORY}
    try:
        with httpx.Client(timeout=10.0) as client:
            def measure(url: str) -> list[int]:
                for _ in range(30):                                   # warmup
                    client.post(url, json=body)
                out = []
                for _ in range(n):
                    t0 = time.perf_counter_ns()
                    r = client.post(url, json=body)
                    out.append(time.perf_counter_ns() - t0)
                    assert r.status_code == 200
                return out

            direct = measure(f"http://127.0.0.1:{MOCK_PORT}/v1/chat/completions")
            proxied = measure(f"http://127.0.0.1:{PROXY_PORT}/v1/chat/completions")
    finally:
        proxy.should_exit = True
        mock.should_exit = True
        time.sleep(0.3)

    dq, pq = quantiles_us(direct), quantiles_us(proxied)
    return {"direct": dq, "proxied": pq,
            "overhead_ms": {"p50": (pq["p50_us"] - dq["p50_us"]) / 1000.0,
                            "p95": (pq["p95_us"] - dq["p95_us"]) / 1000.0,
                            "mean": (pq["mean_us"] - dq["mean_us"]) / 1000.0}}


def main() -> int:
    print("GCC local proxy — latency bench")
    print(f"python {platform.python_version()} on {platform.system()} "
          f"{platform.release()} ({platform.machine()})\n")

    meta = bench_meta_decision()
    tick, replay = meta["hrl_tick"], meta["full_replay_12_turns"]
    print(f"[1] META-DECISION (one HRL tick, n={tick['n']}):")
    print(f"    mean {tick['mean_us']:.1f} us   p50 {tick['p50_us']:.1f} us   "
          f"p99 {tick['p99_us']:.1f} us")
    print(f"    full stateless replay, 12-turn history (n={replay['n']}): "
          f"mean {replay['mean_us']:.1f} us   p99 {replay['p99_us']:.1f} us")
    tick_ok = tick["p99_us"] < 2000.0
    replay_ok = replay["p99_us"] < 2000.0
    print(f"    budget < 2 ms: HRL tick {'PASS' if tick_ok else 'FAIL'}, "
          f"full replay {'PASS' if replay_ok else 'FAIL'}\n")

    e2e = bench_e2e_overhead()
    ov = e2e["overhead_ms"]
    print(f"[2] END-TO-END overhead via proxy (localhost mock upstream, "
          f"n={e2e['proxied']['n']}):")
    print(f"    direct  p50 {e2e['direct']['p50_us']/1000:.2f} ms   "
          f"p95 {e2e['direct']['p95_us']/1000:.2f} ms")
    print(f"    proxied p50 {e2e['proxied']['p50_us']/1000:.2f} ms   "
          f"p95 {e2e['proxied']['p95_us']/1000:.2f} ms")
    print(f"    overhead p50 {ov['p50']:.2f} ms   p95 {ov['p95']:.2f} ms   "
          f"mean {ov['mean']:.2f} ms")
    e2e_ok = ov["p50"] < 50.0
    bypass_ok = ov["p50"] < 20.0
    print(f"    budget < 50 ms: {'PASS' if e2e_ok else 'FAIL'}"
          f"   (developer-bypass target < 20 ms: {'PASS' if bypass_ok else 'FAIL'})\n")

    results = {
        "timestamp": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "meta_decision": meta, "e2e": e2e,
        "budgets": {"hrl_tick_under_2ms": tick_ok, "replay_under_2ms": replay_ok,
                    "e2e_under_50ms": e2e_ok, "e2e_under_20ms": bypass_ok},
    }
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"latency_{results['timestamp']}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"results written: {out_path}")
    return 0 if (tick_ok and replay_ok and e2e_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
