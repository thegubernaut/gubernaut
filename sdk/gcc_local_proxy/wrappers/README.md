# Framework wrappers — drop-in demos

Each demo proves the same two things through a different client stack:

1. **Drop-in**: adoption is one line — point the client's base URL at the proxy.
2. **Runaway protection**: a 4x recursive loop is intercepted by the governor
   with a deterministic `[GCC]` fallback before any upstream spend.

| Demo | Stack | Drop-in line |
|---|---|---|
| `openai_sdk_demo.py` | OpenAI Python SDK | `OpenAI(base_url="http://127.0.0.1:8000/v1")` |
| `langchain_demo.py` | LangChain | `ChatOpenAI(base_url="http://127.0.0.1:8000/v1")` |
| `llamaindex_demo.py` | LlamaIndex | `OpenAI(api_base="http://127.0.0.1:8000/v1")` |
| `autogen_demo.py` | AutoGen (`autogen-agentchat` ≥ 0.7) | `OpenAIChatCompletionClient(base_url="http://127.0.0.1:8000/v1", ...)` |
| `eliza_config.md` | ElizaOS (Web3) | `.env: OPENAI_BASE_URL=…` (verified vs eliza v2.0.4, 2026-07-18) |

All Python demos honour `GCC_PROXY_BASE` to target a proxy on another port.

## Run (keyless, fully local)

From the lane's `python/` directory, three terminals — or background the first two:

```powershell
# 1. mock upstream (no API key needed)
.venv\Scripts\python.exe ..\wrappers\mock_upstream.py

# 2. the governed proxy, pointed at the mock
.venv\Scripts\python.exe -m gcc_proxy --upstream http://127.0.0.1:18081

# 3. any demo
.venv\Scripts\python.exe ..\wrappers\openai_sdk_demo.py
.venv\Scripts\python.exe ..\wrappers\langchain_demo.py
.venv\Scripts\python.exe ..\wrappers\llamaindex_demo.py
```

Demo dependencies (not part of the proxy package):
`pip install openai langchain-openai llama-index-llms-openai autogen-agentchat "autogen-ext[openai]"`

Against a real upstream, skip the mock and export your real key — the proxy
stores nothing and forwards the client's `Authorization` header verbatim.
