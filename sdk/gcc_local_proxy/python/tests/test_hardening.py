"""0.1.1 hardening tests: strict boolean config parsing, typed SDK errors, and
the opt-in preflight probe. (Route policy + typed HTTP errors are covered in
test_proxy.py.)"""

import httpx
import pytest

from gcc_proxy.config import GCCConfig
from gubernaut_sdk import (launch_proxy, preflight,
                           GubernautConnectionError, GubernautError)


def _ok_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": "x", "object": "chat.completion", "created": 1, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    return httpx.MockTransport(handler)


def test_strict_bool_rejects_typo(monkeypatch):
    # a typo must abort startup, never silently disable the spend veto
    monkeypatch.setenv("GCC_HARD_STOP_ENABLED", "disabled")
    with pytest.raises(ValueError):
        GCCConfig.from_env()


def test_strict_bool_accepts_known_tokens(monkeypatch):
    monkeypatch.setenv("GCC_HARD_STOP_ENABLED", "off")
    assert GCCConfig.from_env().hard_stop_enabled is False
    monkeypatch.setenv("GCC_HARD_STOP_ENABLED", "on")
    assert GCCConfig.from_env().hard_stop_enabled is True


def test_typed_error_hierarchy():
    assert issubclass(GubernautConnectionError, GubernautError)
    e = GubernautConnectionError("http://127.0.0.1:8000/v1", "boom")
    assert "unreachable" in str(e) and "ungoverned" in str(e)


def test_preflight_raises_on_dead_proxy():
    with pytest.raises(GubernautConnectionError):
        preflight("http://127.0.0.1:19993/v1", timeout=1.0)


def test_preflight_succeeds_on_live_proxy():
    proxy = launch_proxy(transport=_ok_transport())
    try:
        health = preflight(proxy.base_url, timeout=2.0)
        assert health["status"] == "ok"
        assert health["governed_route"] == "/v1/chat/completions"
    finally:
        proxy.stop()


def test_launch_proxy_preflight_flag():
    # preflight=True must return a live, health-verified proxy
    proxy = launch_proxy(preflight=True, transport=_ok_transport())
    try:
        assert proxy.port > 0
    finally:
        proxy.stop()
