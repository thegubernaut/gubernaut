#!/usr/bin/env python3
"""Keyless mock upstream so every wrapper demo runs without an API key.

Answers any /v1/chat/completions with a canned completion (stream or not).
Run:  python mock_upstream.py   (listens on 127.0.0.1:18081)
Then: gcc-proxy --upstream http://127.0.0.1:18081
"""

import json
import time

import uvicorn

PORT = 18081


def _completion() -> dict:
    return {
        "id": "chatcmpl-mock", "object": "chat.completion",
        "created": int(time.time()), "model": "mock-model",
        "choices": [{"index": 0,
                     "message": {"role": "assistant",
                                 "content": "(mock upstream reply) Understood — proceeding."},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 8, "total_tokens": 16},
    }


def _chunk(delta: dict, finish: str | None = None) -> bytes:
    payload = {"id": "chatcmpl-mock", "object": "chat.completion.chunk",
               "created": int(time.time()), "model": "mock-model",
               "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
    return f"data: {json.dumps(payload)}\n\n".encode()


async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    body = b""
    while True:
        event = await receive()
        body += event.get("body", b"")
        if event["type"] != "http.request" or not event.get("more_body"):
            break
    try:
        stream = json.loads(body or b"{}").get("stream", False)
    except json.JSONDecodeError:
        stream = False

    if scope["path"].endswith("/chat/completions") and stream:
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")]})
        for part in (_chunk({"role": "assistant"}),
                     _chunk({"content": "(mock upstream reply) "}),
                     _chunk({"content": "Understood — proceeding."}),
                     _chunk({}, finish="stop"),
                     b"data: [DONE]\n\n"):
            await send({"type": "http.response.body", "body": part, "more_body": True})
        await send({"type": "http.response.body", "body": b""})
        return

    payload = _completion() if scope["path"].endswith("/chat/completions") else {
        "object": "list", "data": [{"id": "mock-model", "object": "model"}]}
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": json.dumps(payload).encode()})


if __name__ == "__main__":
    print(f"mock upstream on http://127.0.0.1:{PORT}/v1 (no key required)")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")
