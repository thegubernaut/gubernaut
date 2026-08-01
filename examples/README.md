# Framework examples

Each demo proves the same two things through a different client stack:

1. **Drop-in.** Adoption is one line: point the client's base URL at the proxy.
2. **Runaway protection.** A 4x recursive loop is intercepted by the governor with a
   deterministic `[GCC]` fallback before any upstream spend.

| Demo | Stack | Drop-in line |
|---|---|---|
| `openai_sdk_demo.py` | OpenAI Python SDK | `OpenAI(base_url="http://127.0.0.1:8000/v1")` |
| `langchain_demo.py` | LangChain | `ChatOpenAI(base_url="http://127.0.0.1:8000/v1")` |
| `llamaindex_demo.py` | LlamaIndex | `OpenAI(api_base="http://127.0.0.1:8000/v1")` |
| `autogen_demo.py` | AutoGen (`autogen-agentchat` 0.7 or newer) | `OpenAIChatCompletionClient(base_url="http://127.0.0.1:8000/v1", ...)` |
| `eliza_config.md` | ElizaOS | `.env: OPENAI_BASE_URL=...` (verified against eliza v2.0.4, 2026-07-18) |

**LlamaIndex takes `api_base` as its own constructor argument**, which is a different thing
from the deprecated `openai.api_base` module attribute. The module attribute is silently
ignored by current OpenAI SDKs; LlamaIndex's parameter works.

All Python demos honour `GCC_PROXY_BASE` to target a proxy on another port.

## Run it, keyless and fully local

From `packages/python`, in three terminals, or background the first two:

```bash
# 1. mock upstream, no API key needed
python ../../examples/mock_upstream.py

# 2. the governed proxy, pointed at the mock
python -m gcc_proxy --upstream http://127.0.0.1:18081

# 3. any demo
python ../../examples/openai_sdk_demo.py
python ../../examples/langchain_demo.py
python ../../examples/llamaindex_demo.py
```

Demo dependencies, which are not part of the proxy package:

```bash
pip install openai langchain-openai llama-index-llms-openai \
            autogen-agentchat "autogen-ext[openai]"
```

Against a real upstream, skip the mock and export your real key. The proxy stores nothing
and forwards the client's `Authorization` header verbatim.
