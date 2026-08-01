"""Proxy integration tests against a mock upstream (httpx.MockTransport):
passthrough fidelity, directive injection, temperature clamp, hard stop,
credential forwarding, and streaming relay."""

import json

import httpx
from fastapi.testclient import TestClient

from gcc_proxy.config import GCCConfig
from gcc_proxy.proxy import create_app

COMPLETION = {
    "id": "chatcmpl-mock", "object": "chat.completion", "created": 1,
    "model": "mock-model",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}

HOSTILE_TURNS = [
    "That's wrong and useless!!",
    "You are the worst assistant, a liar!!",
    "This is garbage, absolutely pathetic!!",
]

LOOP_MSG = "Retry: call search() with the same query until it succeeds."


def make_client(cfg=None):
    seen = []

    class SSEStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"mock":1}\n\n'
            yield b"data: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/chat/completions":
            if b"stream" in request.content and json.loads(request.content).get("stream"):
                return httpx.Response(
                    200, stream=SSEStream(),
                    headers={"content-type": "text/event-stream"})
            return httpx.Response(200, json=COMPLETION)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": []})
        return httpx.Response(404, json={"error": "not found"})

    app = create_app(cfg or GCCConfig(), transport=httpx.MockTransport(handler))
    return TestClient(app), seen


def chat_body(user_texts, **extra):
    messages = []
    for t in user_texts:
        messages.append({"role": "user", "content": t})
        messages.append({"role": "assistant", "content": "…"})
    messages = messages[:-1]  # latest turn is the pending user message
    return {"model": "mock-model", "messages": messages, **extra}


def test_benign_request_passes_untouched():
    client, seen = make_client()
    with client:
        r = client.post("/v1/chat/completions",
                        json=chat_body(["How does backpropagation work?"]),
                        headers={"Authorization": "Bearer sk-test-123"})
    assert r.status_code == 200
    assert r.headers["x-gcc-posture"] == "DEFAULT"
    assert r.headers["x-gcc-hard-stop"] == "false"
    sent = json.loads(seen[-1].content)
    assert all("[governor]" not in str(m.get("content", "")) for m in sent["messages"])
    assert "temperature" not in sent
    assert seen[-1].headers["authorization"] == "Bearer sk-test-123"


def test_hostile_history_injects_directive_and_clamps_temperature():
    client, seen = make_client()
    with client:
        r = client.post("/v1/chat/completions",
                        json=chat_body(HOSTILE_TURNS, temperature=0.9))
    assert r.status_code == 200
    assert r.headers["x-gcc-posture"] == "INHIBIT"
    sent = json.loads(seen[-1].content)
    last = sent["messages"][-1]
    assert last["role"] == "system" and last["content"].startswith("[governor]")
    assert sent["temperature"] == 0.3


def test_saturated_loop_hard_stops_without_upstream_call():
    client, seen = make_client()
    with client:
        r = client.post("/v1/chat/completions", json=chat_body([LOOP_MSG] * 4))
    assert r.status_code == 200
    assert r.headers["x-gcc-hard-stop"] == "true"
    payload = r.json()
    assert payload["gcc"]["hard_stop"] is True
    assert "[GCC]" in payload["choices"][0]["message"]["content"]
    assert payload["usage"]["total_tokens"] == 0
    assert not seen                                  # upstream never touched


def test_streaming_is_relayed():
    client, seen = make_client()
    with client:
        r = client.post("/v1/chat/completions",
                        json=chat_body(["hello there"], stream=True))
    assert r.status_code == 200
    assert "data: [DONE]" in r.text
    assert r.headers["x-gcc-posture"] == "DEFAULT"


def test_state_endpoint_reports_decision():
    client, _ = make_client()
    with client:
        r = client.post("/gcc/state", json=chat_body([LOOP_MSG] * 4))
    body = r.json()
    assert body["posture"] == "REGROUND"
    assert body["hard_stop"] is True
    assert 0.0 <= body["state"]["equilibrium"] <= 1.0


def test_non_chat_routes_pass_through():
    client, seen = make_client()
    with client:
        r = client.get("/v1/models")
    assert r.status_code == 200
    assert seen[-1].url.path == "/v1/models"


def test_malformed_body_fails_closed():
    # 0.1.1: a body the governor cannot read as a chat completion is NOT
    # forwarded ungoverned (was fail-OPEN passthrough in 0.1.0 — flipped, and
    # disclosed in the Session-8 destructive-QA mission).
    client, seen = make_client()
    with client:
        r = client.post("/v1/chat/completions", content=b"not json",
                        headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert r.headers["x-gcc-error"] == "ungovernable_body"
    assert r.json()["error"]["governed"] is False
    assert not seen                                    # upstream never touched


def test_malformed_body_passthrough_when_opted_out():
    cfg = GCCConfig(allow_ungoverned_routes=True)
    client, seen = make_client(cfg)
    with client:
        r = client.post("/v1/chat/completions", content=b"not json",
                        headers={"content-type": "application/json"})
    assert r.status_code == 200                         # explicit opt-out restores it
    assert seen[-1].content == b"not json"


def test_ungoverned_generative_route_blocked_by_default():
    client, seen = make_client()
    with client:
        r = client.post("/v1/responses", json={"model": "m", "input": "loop"})
    assert r.status_code == 403
    assert r.headers["x-gcc-error"] == "route_not_governed"
    assert not seen                                    # upstream never touched


def test_ungoverned_route_allowed_when_opted_out():
    cfg = GCCConfig(allow_ungoverned_routes=True)
    client, seen = make_client(cfg)
    with client:
        client.post("/v1/responses", json={"model": "m", "input": "loop"})
    assert seen[-1].url.path == "/v1/responses"         # opt-out forwards it


def test_upstream_failure_returns_typed_502_with_headers():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("mock upstream down", request=request)

    app = create_app(GCCConfig(), transport=httpx.MockTransport(handler))
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions",
                        json=chat_body(["a normal benign question about physics"]))
    assert r.status_code == 502
    assert r.headers["x-gcc-error"] == "upstream_unreachable"
    assert r.headers["x-gcc-posture"] == "DEFAULT"      # governed headers preserved
    assert r.json()["error"]["governed"] is False
