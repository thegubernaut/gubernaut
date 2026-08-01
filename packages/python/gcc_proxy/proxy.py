"""The drop-in proxy server.

OpenAI-compatible surface: point any client at http://localhost:8000/v1 and
every chat completion is governed on the way through:

  request in -> engine replay (numbers only at the meta level) -> posture
  actuation on the outbound body -> upstream -> response out, with the
  governed state exposed in X-GCC-* headers.

No credentials are stored or read from disk: the client's own Authorization
header is forwarded verbatim to the upstream. Requests the governor does not
understand pass through untouched (fail-open transport; the governor never
becomes an availability risk).
"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from gcc_proxy.actuation import apply_decision, hard_stop_response
from gcc_proxy.config import GCCConfig
from gcc_proxy.engine import EngineResult, GovernorEngine

_HOP_HEADERS = {
    "host", "content-length", "connection", "keep-alive", "transfer-encoding",
    "te", "upgrade", "proxy-authorization", "proxy-connection", "accept-encoding",
}

_UPSTREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0)

# Route policy (0.1.1): which /v1/* routes may pass through UNGOVERNED. These are
# non-generative and not loop-prone, so forwarding them is not a firewall hole.
# Every other /v1/* route (notably the generative /v1/responses and
# /v1/completions) is denied by default — see GCCConfig.allow_ungoverned_routes.
_PASSTHROUGH_ALLOWLIST = {"models", "embeddings"}


def _forward_headers(request: Request) -> dict[str, str]:
    return {k: v for k, v in request.headers.items() if k.lower() not in _HOP_HEADERS}


def _gcc_error(status: int, code: str, message: str,
               extra_headers: dict[str, str] | None = None) -> JSONResponse:
    """A typed, header-carrying error (never an opaque 500). ``x-gcc-error``
    names the failure class; any governed-decision headers computed before the
    failure are preserved so the caller can tell an upstream outage from a proxy
    bug. ``governed: False`` signals no ungoverned traffic was forwarded."""
    headers = {"x-gcc-error": code}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        {"error": {"type": "gcc_error", "code": code, "message": message,
                   "governed": False}},
        status_code=status, headers=headers)


def _gcc_headers(result: EngineResult) -> dict[str, str]:
    d, t = result.decision, result.telemetry
    s = d.state
    return {
        "x-gcc-posture": d.posture.value,
        "x-gcc-temperature-max": f"{d.temperature_max:.2f}",
        "x-gcc-equilibrium": f"{s.equilibrium:.3f}",
        "x-gcc-arousal": f"{s.arousal:.3f}",
        "x-gcc-perseveration": f"{s.perseveration:.3f}",
        "x-gcc-repetition": f"{t.repetition:.3f}",
        "x-gcc-recovery": str(d.recovery_window),
        "x-gcc-hard-stop": "true" if result.hard_stop else "false",
    }


def create_app(config: GCCConfig | None = None,
               transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`transport` lets tests inject an httpx.MockTransport as the upstream."""
    cfg = config or GCCConfig.from_env()
    engine = GovernorEngine(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.client = httpx.AsyncClient(base_url=cfg.upstream_base,
                                             timeout=_UPSTREAM_TIMEOUT,
                                             transport=transport)
        try:
            yield
        finally:
            await app.state.client.aclose()

    app = FastAPI(title="GCC Local Proxy", docs_url=None, redoc_url=None,
                  lifespan=lifespan)
    app.state.cfg = cfg
    app.state.engine = engine

    @app.get("/gcc/health")
    async def health() -> dict:
        return {"status": "ok", "upstream": cfg.upstream_base,
                "hard_stop_enabled": cfg.hard_stop_enabled,
                "allow_ungoverned_routes": cfg.allow_ungoverned_routes,
                "governed_route": "/v1/chat/completions",
                "passthrough_allowlist": sorted(_PASSTHROUGH_ALLOWLIST)}

    @app.post("/gcc/state")
    async def state(request: Request) -> JSONResponse:
        """Debug/cockpit endpoint: messages in, governed decision out. No upstream call."""
        body = await request.json()
        result = engine.evaluate_messages(body.get("messages", []))
        d, s = result.decision, result.decision.state
        return JSONResponse({
            "posture": d.posture.value,
            "temperature_max": d.temperature_max,
            "recovery_window": d.recovery_window,
            "state": {"equilibrium": s.equilibrium, "arousal": s.arousal,
                      "perseveration": s.perseveration},
            "telemetry": {"intensity": result.telemetry.intensity,
                          "valence": result.telemetry.valence,
                          "repetition": result.telemetry.repetition},
            "hard_stop": result.hard_stop,
            "replayed_turns": result.replayed_turns,
        })

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        raw = await request.body()
        # A body we cannot read as a chat request is a body we cannot govern.
        # Fail CLOSED — do NOT forward it ungoverned — unless explicitly opted out.
        try:
            body = json.loads(raw)
            messages = body.get("messages")
            malformed = not isinstance(messages, list)
        except json.JSONDecodeError:
            body, messages, malformed = None, None, True
        if malformed:
            if cfg.allow_ungoverned_routes:
                return await _passthrough(request, raw)
            return _gcc_error(
                400, "ungovernable_body",
                "request body is not a governable chat completion (messages must "
                "be a list); blocked fail-closed — not forwarded ungoverned. Set "
                "GCC_ALLOW_UNGOVERNED_ROUTES=1 to forward such bodies anyway.")

        # A governor fault must never fall through to an ungoverned upstream call.
        try:
            result = engine.evaluate_messages(messages)
            headers = _gcc_headers(result)
        except Exception as e:      # pragma: no cover - defensive fail-closed
            return _gcc_error(
                500, "governor_fault",
                f"governor raised {type(e).__name__}: {e}; blocked fail-closed "
                "(no upstream call made).")

        if result.hard_stop:
            payload = hard_stop_response(model=str(body.get("model", "unknown")),
                                         created=int(time.time()))
            return JSONResponse(payload, headers=headers)

        governed = apply_decision(body, result.decision)
        upstream_headers = _forward_headers(request)
        upstream_headers["content-type"] = "application/json"
        client: httpx.AsyncClient = app.state.client

        try:
            if governed.get("stream"):
                upstream_request = client.build_request(
                    "POST", "/v1/chat/completions",
                    content=json.dumps(governed), headers=upstream_headers)
                upstream_response = await client.send(upstream_request, stream=True)

                async def relay():
                    try:
                        async for chunk in upstream_response.aiter_raw():
                            yield chunk
                    finally:
                        await upstream_response.aclose()

                media_type = upstream_response.headers.get("content-type", "text/event-stream")
                return StreamingResponse(relay(), status_code=upstream_response.status_code,
                                         media_type=media_type, headers=headers)

            upstream_response = await client.post("/v1/chat/completions",
                                                  content=json.dumps(governed),
                                                  headers=upstream_headers)
        except httpx.HTTPError as e:
            # Upstream unreachable/timeout → a typed, header-carrying 502, not an
            # opaque 500. The governor already ran (its x-gcc-* headers are
            # attached), so the caller can distinguish an upstream outage from a
            # proxy bug — and nothing ungoverned was sent.
            return _gcc_error(
                502, "upstream_unreachable",
                f"upstream call failed: {type(e).__name__}: {e}",
                extra_headers=headers)

        media_type = upstream_response.headers.get("content-type", "application/json")
        return Response(content=upstream_response.content,
                        status_code=upstream_response.status_code,
                        media_type=media_type, headers=headers)

    @app.api_route("/v1/{path:path}",
                   methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def passthrough(path: str, request: Request) -> Response:
        first = path.split("/", 1)[0]
        if cfg.allow_ungoverned_routes or first in _PASSTHROUGH_ALLOWLIST:
            return await _passthrough(request, await request.body())
        # Deny-by-default: an ungoverned generative route (/v1/responses,
        # /v1/completions, or any unknown /v1/*) is a hole in the firewall.
        return _gcc_error(
            403, "route_not_governed",
            f"/v1/{path} is not a governed route. This proxy governs "
            f"/v1/chat/completions and passes through {sorted(_PASSTHROUGH_ALLOWLIST)}; "
            "everything else is blocked so no generative traffic escapes "
            "ungoverned. Route it through /v1/chat/completions, or set "
            "GCC_ALLOW_UNGOVERNED_ROUTES=1 to forward this route ungoverned.")

    async def _passthrough(request: Request, raw: bytes) -> Response:
        client: httpx.AsyncClient = app.state.client
        upstream_response = await client.request(
            request.method, request.url.path,
            params=dict(request.query_params) or None,
            content=raw or None, headers=_forward_headers(request))
        media_type = upstream_response.headers.get("content-type")
        return Response(content=upstream_response.content,
                        status_code=upstream_response.status_code,
                        media_type=media_type)

    return app
