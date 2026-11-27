# Configuration reference: Tiller

Everything the proxy reads, sends back and refuses. Every value below is read from the code:
[`config.py`](../packages/python/gcc_proxy/config.py), [`proxy.py`](../packages/python/gcc_proxy/proxy.py)
and [`actuation.py`](../packages/python/gcc_proxy/actuation.py).

## Start it

```bash
gubernaut-proxy --upstream https://api.openai.com      # also installed as gcc-proxy
```

| Flag | Default | What it does |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Address to bind |
| `--port` | `8000` | Port to bind |
| `--upstream` | `https://api.openai.com` | The OpenAI-compatible API to forward governed calls to |
| `--no-hard-stop` | off | Keep the postures, never hard-stop. Advisory only |
| `--allow-ungoverned-routes` | off | Forward non-chat `/v1/*` routes and unreadable bodies ungoverned. Weakens the firewall |

From Python, the same proxy in one call:

```python
from gubernaut_sdk import launch_proxy

proxy = launch_proxy(upstream="https://api.openai.com", port=8000)   # port=0 picks a free port
print(proxy.base_url)    # http://127.0.0.1:8000/v1
proxy.stop()             # or use it as a context manager: with launch_proxy(...) as proxy:
```

`launch_proxy(preflight=True)` waits until the proxy answers before returning. The helpers
`openai_kwargs()`, `langchain_kwargs(model)` and `llamaindex_kwargs(model)` return the client
arguments for each framework.

## Environment variables

Every setting is also an environment variable: `GCC_` plus the field name in capitals. A flag wins
over the variable. A boolean must be `1/true/yes/on` or `0/false/no/off`; anything else stops the
proxy at startup rather than guessing.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GCC_UPSTREAM_BASE` | `https://api.openai.com` | Upstream API |
| `GCC_HOST`, `GCC_PORT` | `127.0.0.1`, `8000` | Bind address |
| `GCC_HARD_STOP_ENABLED` | `true` | The hard stop. `false` is the same as `--no-hard-stop` |
| `GCC_HARD_STOP_REPETITION` | `0.80` | Repetition must stay at or above this… |
| `GCC_HARD_STOP_TURNS` | `2` | …for this many consecutive `REGROUND` turns before the stop |
| `GCC_ALLOW_UNGOVERNED_ROUTES` | `false` | Same as `--allow-ungoverned-routes` |
| `GCC_SIMILARITY_WINDOW` | `8` | Prior same-role messages that repetition is measured against |
| `GCC_REPLAY_WINDOW` | `16` | User turns the engine replays to rebuild state |

The controller's constants (`GCC_RETAIN`, `GCC_GAIN`, `GCC_DECAY_RECOVERY`, `GCC_PERSEV_RETAIN`,
`GCC_PERSEV_GAIN`, `GCC_T_INHIBIT`, `GCC_T_REGROUND`, `GCC_RECOVERY_TURNS`, `GCC_TEMP_OPEN`,
`GCC_TEMP_CLAMPED`) can be overridden the same way. Their defaults are working defaults for the open
reference implementation, not the configuration the validation record used. What each one does:
[ARCHITECTURE.md](ARCHITECTURE.md).

## Routes

| Route | Behaviour |
| --- | --- |
| `POST /v1/chat/completions` | Governed. Streaming works |
| `/v1/models`, `/v1/embeddings` | Passed through: they generate nothing |
| Any other `/v1/*` (for example `/v1/responses`) | Refused with `403`, unless ungoverned routes are allowed |
| `GET /gcc/health` | Status, the upstream, and whether the hard stop is on |
| `POST /gcc/state` | Send `{"messages": [...]}`, get back the posture and the three numbers. No upstream call |

## What comes back

Every governed response carries these headers:

| Header | Value |
| --- | --- |
| `x-gcc-posture` | `DEFAULT`, `INHIBIT` or `REGROUND` ([POSTURES.md](POSTURES.md)) |
| `x-gcc-hard-stop` | `true` when the call was stopped locally |
| `x-gcc-temperature-max` | The temperature ceiling applied to this call |
| `x-gcc-repetition` | This turn's repetition score |
| `x-gcc-equilibrium`, `x-gcc-arousal`, `x-gcc-perseveration` | The controller's state |
| `x-gcc-recovery` | Above 0 while a recovery window is open ([POSTURES.md](POSTURES.md#the-recovery-window)) |

With the OpenAI SDK, read them through `client.chat.completions.with_raw_response.create(...)`; a
plain `create()` returns a parsed object without headers.

**A stopped call** returns an ordinary chat completion with `usage` all zeros, `"gcc":
{"hard_stop": true}`, and a reply that starts with `[GCC]`. Nothing went upstream. Check for that
prefix or the header to end your loop.

## Errors

The proxy fails closed: when it cannot govern a call, it does not send it.

| Status | `code` | When |
| --- | --- | --- |
| `400` | `ungovernable_body` | The body is not a chat completion (`messages` is not a list) |
| `403` | `route_not_governed` | A generative route other than chat completions |
| `500` | `governor_fault` | The controller raised. No upstream call was made |
| `502` | `upstream_unreachable` | The upstream could not be reached |

If the proxy itself is down, your client gets a connection error, so the agent stops. It never
carries on unguarded.

## Pitfalls with the OpenAI SDK

- Set `base_url` on the client object: `OpenAI(base_url="http://localhost:8000/v1")`.
- The old module attribute `openai.api_base` is ignored by current SDKs, so the client silently
  goes straight upstream.
- The module-level `openai.base_url` needs a trailing slash, or the SDK builds `/v1chat/completions`.
- Your `Authorization` header is forwarded as is and never stored.
