# gubernaut-sdk — Gubernaut Cognitive Controller, local drop-in proxy

Deterministic runtime governor for LLM agents, packaged as an
OpenAI-compatible local proxy. Adoption is one line:

```python
openai.base_url = "http://localhost:8000/v1"
```

## Install

```bash
pip install gubernaut-sdk
pip install -e .[dev]            # or: editable, for development
```

One distribution, two import packages: `gcc_proxy` (the proxy engine + CLI)
and `gubernaut_sdk` (the one-call facade). Programmatic start is one import,
one call:

```python
from gubernaut_sdk import launch_proxy, langchain_kwargs

proxy = launch_proxy(upstream="https://api.openai.com")   # ephemeral port
llm = ChatOpenAI(**langchain_kwargs("gpt-4o-mini", base_url=proxy.base_url))
...
proxy.stop()
```

## Run (CLI)

```bash
gcc-proxy --upstream https://api.openai.com        # or any OpenAI-compatible base
gubernaut-proxy --upstream ...                     # same entry point, alias
```

Every `/v1/chat/completions` request is governed on the way through:

- **IGL (telemetry v0)** appraises each user turn locally into
  `{intensity, valence, repetition}` — raw text stops there.
- **HRL** — a deterministic, token-free state machine over
  `{equilibrium, arousal, perseveration}` — commands a posture:
  `DEFAULT` / `INHIBIT` / `REGROUND`, plus a temperature ceiling.
- **Actuation** applies the posture to the outbound request; saturated
  recursive loops are **hard-stopped before the upstream call** (deterministic
  fallback, zero upstream spend). Disable with `--no-hard-stop`.

State is re-derived per request by replaying the visible history — the proxy
is stateless, deterministic, and fully replayable. Governed state is exposed
in `X-GCC-*` response headers and at `POST /gcc/state`. Credentials are never
stored: the client's `Authorization` header is forwarded verbatim.

Constants in `gcc_proxy/config.py` are working defaults for this reference
implementation (env-overridable, `GCC_*`); they are not the evaluated
configuration from the validation record.

## Verify

```bash
python -m pytest tests -q             # 30 tests, incl. loop-trap REGROUND ≤ 4 turns
python ..\bench\latency_bench.py      # latency budgets, results as JSON
```

No consciousness claims: a measured, falsifiable regulation layer.
Byline: Gubernaut Research.
## Citation & license

Licensed under **Apache-2.0** (see `LICENSE`). If you use Gubernaut, please cite
the concept (all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

Byline: Gubernaut Research.
