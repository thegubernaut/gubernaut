#!/usr/bin/env python3
"""See the stop in one command, with no API key and no network.

    pip install gubernaut-sdk
    python hard_stop_demo.py

An agent sends the same request 25 times, twice:

- once straight to the model, with nothing watching;
- once through Gubernaut Tiller, the real proxy, running on a local port.

The "model" is a stand-in inside this script. It never leaves your machine, and it counts every
request that reaches it, because every request that reaches a real model is billed. The proxy,
the controller and its decision are the published package, unchanged.

The only line an agent changes to adopt Tiller is the address it sends its calls to:

    client = OpenAI(base_url="http://127.0.0.1:8000/v1")
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import uvicorn

from gcc_proxy.config import GCCConfig
from gcc_proxy.proxy import create_app

TRIES = 25
REQUEST = ("Retry the plan: call search(), parse the result, then call "
           "search() again with the same query until it succeeds.")


class StandInModel:
    """Answers like an OpenAI-compatible model and counts what reaches it."""

    def __init__(self) -> None:
        self.billed = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.billed += 1
        return httpx.Response(200, json={
            "id": "chatcmpl-standin", "object": "chat.completion", "created": int(time.time()),
            "model": "stand-in",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant",
                                     "content": "Searching again with the same query."}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 8, "total_tokens": 16},
        })


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_agent(client: httpx.Client, url: str, model: StandInModel) -> list[bool]:
    """Send the same request TRIES times. Returns, per try, whether the model was billed for it."""
    messages: list[dict] = []
    billed: list[bool] = []
    for _ in range(TRIES):
        messages.append({"role": "user", "content": REQUEST})
        before = model.billed
        r = client.post(url, json={"model": "stand-in", "messages": messages})
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"] or ""
        messages.append({"role": "assistant", "content": reply})
        billed.append(model.billed > before)
    return billed


def lane(name: str, billed: list[bool]) -> None:
    marks = "".join("■" if b else "□" for b in billed)
    n = sum(billed)
    first_stop = next((i + 1 for i, b in enumerate(billed) if not b), None)
    tail = f"{n} billed, stopped at try {first_stop}" if first_stop else f"{n} tries, {n} billed"
    print(f"  {name:<17}{marks}  {tail}")


def main() -> int:
    # 1. Nothing watching: the agent talks to the model directly.
    alone = StandInModel()
    with httpx.Client(transport=httpx.MockTransport(alone.handle),
                      base_url="http://model.local") as direct:
        unwatched = run_agent(direct, "/v1/chat/completions", alone)

    # 2. With Gubernaut: the same agent, pointed at the real proxy on a local port.
    governed = StandInModel()
    port = free_port()
    app = create_app(GCCConfig(upstream_base="http://model.local", port=port),
                     transport=httpx.MockTransport(governed.handle))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
        for _ in range(100):
            try:
                if client.get("/gcc/health").status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.05)
        else:
            raise SystemExit("the proxy did not start")
        watched = run_agent(client, "/v1/chat/completions", governed)
    server.should_exit = True

    print(f"\nThe same request, repeated {TRIES} times  (■ billed  □ stopped, never billed)\n")
    lane("Nothing watching", unwatched)
    lane("With Gubernaut", watched)
    print()
    if all(watched):
        print("No stop happened. That is not the expected behaviour: please open an issue.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
