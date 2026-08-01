# gubernaut-sdk

**A deterministic runtime governor for LLM agents**, packaged as an OpenAI-compatible local
proxy. It hard-stops runaway agent loops before they reach your API bill.

Adoption is one line:

```python
openai.base_url = "http://localhost:8000/v1"
```

```bash
pip install gubernaut-sdk
```

Full project, receipts and documentation:
[github.com/thegubernaut/gubernaut](https://github.com/thegubernaut/gubernaut)

## Quickstart

```python
import openai
from gubernaut_sdk import launch_proxy

proxy = launch_proxy(upstream="https://api.openai.com")
openai.base_url = proxy.base_url        # every call is now governed

resp = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.headers.get("x-gcc-posture"))   # DEFAULT | INHIBIT | REGROUND

proxy.stop()
```

**Set `base_url`.** The pre-v1 `openai.api_base` attribute is ignored silently by current
OpenAI SDKs, so a client configured that way goes straight upstream ungoverned and nothing
errors to tell you.

One distribution, two import packages: `gcc_proxy` is the proxy engine and CLI,
`gubernaut_sdk` is the one-call facade with framework helpers.

```python
from gubernaut_sdk import launch_proxy, langchain_kwargs
llm = ChatOpenAI(**langchain_kwargs("gpt-4o-mini", base_url=proxy.base_url))
```

## As a CLI

```bash
gcc-proxy --upstream https://api.openai.com    # or any OpenAI-compatible base
gubernaut-proxy --upstream ...                 # same entry point, alias
```

## What happens to a request

Every `/v1/chat/completions` request is governed on the way through:

- **IGL** appraises each user turn locally into `{intensity, valence, repetition}`.
  **Raw text stops there.**
- **HRL**, a deterministic token-free state machine over
  `{equilibrium, arousal, perseveration}`, commands a posture, `DEFAULT`, `INHIBIT` or
  `REGROUND`, plus a temperature ceiling.
- **Actuation** applies the posture to the outbound request. A saturated recursive loop is
  **hard-stopped before the upstream call**: a deterministic fallback completion with zero
  upstream spend. Disable with `--no-hard-stop`.

State is re-derived per request by replaying the visible history, so the proxy is
stateless, deterministic and fully replayable. Governed state is exposed in `X-GCC-*`
response headers and at `POST /gcc/state`.

**Credentials are never stored.** The client's `Authorization` header is forwarded
verbatim.

## Verify it yourself

```bash
python -m pytest tests -q            # includes the loop trap: REGROUND within 4 turns
python ../../bench/latency_bench.py  # latency budgets, results as JSON
```

The full reproduction guide, including the spend battery, is
[docs/REPRODUCE.md](https://github.com/thegubernaut/gubernaut/blob/main/docs/REPRODUCE.md).

## Configuration

Constants in `gcc_proxy/config.py` are the working defaults for this reference
implementation, overridable through `GCC_*` environment variables. They are not the
evaluated configuration from the validation record, and changing them means the published
figures no longer describe your deployment.

## Citation and license

Licensed under **Apache-2.0**. If you use Gubernaut, please cite the concept
(all-versions) DOI:

> Gubernaut Research. *Gubernaut Cognitive Controller (GCC).* Zenodo.
> https://doi.org/10.5281/zenodo.21303518

No consciousness claims. This is a regulation layer, measured and falsifiable.
Byline: Gubernaut Research.
