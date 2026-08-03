# gubernaut-sdk

**A deterministic runtime governor for LLM agents**, packaged as an OpenAI-compatible local
proxy. It hard-stops runaway agent loops before they reach your API bill.

Start the governor, then change one line in your code:

```bash
pip install gubernaut-sdk
gcc-proxy --upstream https://api.openai.com     # binds 127.0.0.1:8000
```

```python
client = OpenAI(base_url="http://localhost:8000/v1")   # the one line of adoption
```

Full project, receipts and documentation:
[github.com/thegubernaut/gubernaut](https://github.com/thegubernaut/gubernaut)

## Quickstart

```python
from openai import OpenAI
from gubernaut_sdk import launch_proxy

proxy = launch_proxy(upstream="https://api.openai.com")
client = OpenAI(base_url=proxy.base_url)   # every call is now governed

resp = client.chat.completions.with_raw_response.create(
    model="gpt-5.6-sol",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.http_response.headers.get("x-gcc-posture"))   # DEFAULT | INHIBIT | REGROUND

proxy.stop()
```

**Set `base_url` on the client.** Three things bite here, all of them silent:

- The pre-v1 `openai.api_base` attribute is ignored by current OpenAI SDKs, so a client
  configured that way goes straight upstream ungoverned and nothing errors to tell you.
- The **module-level** `openai.base_url` attribute needs a **trailing slash**. Without one
  the SDK builds `/v1chat/completions` and you get a 404. Setting `base_url` on the client
  object, as above, works either way, which is why every example here uses that form.
- `launch_proxy()` binds an **ephemeral** port unless you pass `port=`. Read
  `proxy.base_url` rather than assuming 8000, or start it with
  `launch_proxy(upstream=..., port=8000)`.

Reading the posture needs `with_raw_response`: a plain `create()` returns a parsed
`ChatCompletion`, which carries no headers.

One distribution, two import packages: `gcc_proxy` is the proxy engine and CLI,
`gubernaut_sdk` is the one-call facade with framework helpers.

```python
from gubernaut_sdk import launch_proxy, langchain_kwargs
llm = ChatOpenAI(**langchain_kwargs("gpt-5.6-sol", base_url=proxy.base_url))
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
