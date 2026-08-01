"""SDK-facade tests: the gubernaut_sdk surface over a REAL server thread.

Unlike test_proxy.py (in-process TestClient), these start the actual uvicorn
host on an ephemeral port and talk to it over HTTP — the exact path a customer
of the packaged wheel takes. Upstream is an injected httpx.MockTransport, so
everything runs offline and deterministically.
"""

import httpx

import gubernaut_sdk
from gubernaut_sdk import (
    ALL_HEADERS,
    HARD_STOP_TEXT,
    HEADER_HARD_STOP,
    HEADER_POSTURE,
    GccProxy,
    langchain_kwargs,
    launch_proxy,
    llamaindex_kwargs,
    openai_kwargs,
)

COMPLETION = {
    "id": "chatcmpl-mock", "object": "chat.completion", "created": 1,
    "model": "mock-model",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "mock reply"},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}

LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")


def _upstream(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/chat/completions":
        return httpx.Response(200, json=COMPLETION)
    return httpx.Response(404, json={"error": "not found"})


def make_proxy(**kwargs) -> GccProxy:
    kwargs.setdefault("transport", httpx.MockTransport(_upstream))
    return launch_proxy(**kwargs)


def chat_body(user_texts):
    messages = []
    for t in user_texts:
        messages.append({"role": "user", "content": t})
        messages.append({"role": "assistant", "content": "…"})
    return {"model": "mock-model", "messages": messages[:-1]}


def test_facade_exports_exist():
    for name in ("launch_proxy", "GccProxy", "GCCConfig", "HARD_STOP_TEXT",
                 "default_base_url", "openai_kwargs", "langchain_kwargs",
                 "llamaindex_kwargs", "ALL_HEADERS", "__version__"):
        assert hasattr(gubernaut_sdk, name), name
    assert HARD_STOP_TEXT.startswith("[GCC]")
    assert len(ALL_HEADERS) == 8


def test_kwargs_factories_shapes(monkeypatch):
    monkeypatch.delenv("GCC_PROXY_BASE", raising=False)
    assert openai_kwargs() == {"base_url": "http://127.0.0.1:8000/v1"}
    assert openai_kwargs(api_key="k") == {
        "base_url": "http://127.0.0.1:8000/v1", "api_key": "k"}
    assert langchain_kwargs("m", base_url="http://x/v1") == {
        "model": "m", "base_url": "http://x/v1"}
    assert llamaindex_kwargs("m") == {
        "model": "m", "api_base": "http://127.0.0.1:8000/v1"}
    monkeypatch.setenv("GCC_PROXY_BASE", "http://127.0.0.1:9999/v1")
    assert openai_kwargs()["base_url"] == "http://127.0.0.1:9999/v1"


def test_launch_binds_ephemeral_port_and_health():
    proxy = make_proxy()
    try:
        assert proxy.port > 0
        assert proxy.base_url == f"http://127.0.0.1:{proxy.port}/v1"
        r = httpx.get(f"{proxy.root_url}/gcc/health", timeout=5.0)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
    finally:
        proxy.stop()


def test_benign_turn_over_http():
    proxy = make_proxy()
    try:
        r = httpx.post(f"{proxy.base_url}/chat/completions",
                       json=chat_body(["How does backpropagation work?"]),
                       timeout=10.0)
        assert r.status_code == 200
        assert r.headers[HEADER_POSTURE] == "DEFAULT"
        assert r.headers[HEADER_HARD_STOP] == "false"
        assert r.json()["choices"][0]["message"]["content"] == "mock reply"
    finally:
        proxy.stop()


def test_loop_hard_stops_and_host_survives():
    proxy = make_proxy()
    try:
        # Incremental client loop, exactly as a customer app accumulates history.
        history, stop_turn = [], None
        for turn in range(1, 6):
            history.append({"role": "user", "content": LOOP_MSG})
            r = httpx.post(f"{proxy.base_url}/chat/completions",
                           json={"model": "mock-model", "messages": history},
                           timeout=10.0)
            assert r.status_code == 200
            content = r.json()["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": content})
            if r.headers[HEADER_HARD_STOP] == "true":
                stop_turn = turn
                assert content.startswith("[GCC]")
                assert r.json()["usage"]["total_tokens"] == 0
                break
        assert stop_turn is not None and stop_turn <= 5
        # Host not crashed: a fresh benign conversation still succeeds.
        r = httpx.post(f"{proxy.base_url}/chat/completions",
                       json=chat_body(["What is a Fourier transform?"]),
                       timeout=10.0)
        assert r.status_code == 200
        assert r.headers[HEADER_HARD_STOP] == "false"
    finally:
        proxy.stop()


def test_header_constants_match_live_response():
    proxy = make_proxy()
    try:
        r = httpx.post(f"{proxy.base_url}/chat/completions",
                       json=chat_body(["hello"]), timeout=10.0)
        for header in ALL_HEADERS:
            assert header in r.headers, header
    finally:
        proxy.stop()


def test_stop_terminates_thread_and_frees_port():
    proxy = make_proxy()
    port = proxy.port
    proxy.stop()
    try:
        httpx.get(f"http://127.0.0.1:{port}/gcc/health", timeout=2.0)
        connected = True
    except httpx.TransportError:
        connected = False
    assert not connected


def test_context_manager_lifecycle():
    with GccProxy(transport=httpx.MockTransport(_upstream)) as proxy:
        r = httpx.get(f"{proxy.root_url}/gcc/health", timeout=5.0)
        assert r.status_code == 200
