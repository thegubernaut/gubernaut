---
name: gubernaut
description: Add Gubernaut to a project so an LLM agent stuck in a retry loop is stopped before the next call is billed. Use when the user's agent loops, repeats the same request, runs up an API bill, or when they ask to add Gubernaut, Tiller, Keel, a loop breaker or a runaway-spend guard to code that calls an OpenAI-compatible API (OpenAI SDK, LangChain, LlamaIndex, AutoGen, ElizaOS) or runs an agent loop in JavaScript, TypeScript or Rust.
---

# Add Gubernaut to a project

Gubernaut watches each turn of an agent and stops a loop that repeats the same request. On a verbatim
loop the stop lands at turn 4; turns 1 to 3 still reach the model and are billed. Pick the product by
how the user's code runs, change as little as possible, then prove the stop works.

## 1. Pick the product

| The code | Use | Why |
| --- | --- | --- |
| Calls an OpenAI-compatible API from any language | **Tiller**, the proxy | One line changes: the client's base URL. Tiller stops the call itself |
| Runs its own loop in JS/TS (Node, Deno, Bun, edge, browser), must not run a proxy, and can compute the three numbers per turn | **Keel**, `@gubernaut/core` | In-process. It decides; the code supplies the numbers and acts on the decision |
| Rust | **Keel**, `gubernaut-core` | Same, as a library |

When unsure, use Tiller.

## 2. Tiller

```bash
pip install gubernaut-sdk
gubernaut-proxy --upstream https://api.openai.com      # serves http://127.0.0.1:8000/v1
```

Change only the client's base URL:

```python
client = OpenAI(base_url="http://localhost:8000/v1")
```

- Set `base_url` on the client object. `openai.api_base` is ignored by current SDKs, and the module-level
  `openai.base_url` needs a trailing slash.
- For other upstreams, pass `--upstream <their OpenAI-compatible base URL>`. The user's API key is
  forwarded as is and never stored.
- In a Python program, the proxy can start in-process instead:
  `from gubernaut_sdk import launch_proxy; proxy = launch_proxy(upstream=..., port=8000)`.
- Framework one-liners are in `examples/` of github.com/thegubernaut/gubernaut (LangChain
  `ChatOpenAI(base_url=...)`, LlamaIndex `OpenAI(api_base=...)`, AutoGen, ElizaOS `OPENAI_BASE_URL`).

**End the loop on a stop.** A stopped call returns a normal completion that cost nothing: the reply
starts with `[GCC]`, `usage` is all zeros, and the response header `x-gcc-hard-stop` is `true`. Add a
check so the agent ends or changes its plan instead of retrying:

```python
if reply.startswith("[GCC]"):
    break   # or: change the approach, escalate to a human
```

## 3. Keel (JavaScript or TypeScript)

```bash
npm install @gubernaut/core
```

```js
import { Governor } from "@gubernaut/core";
const gov = await Governor.create();
const { posture, temperatureMax } = gov.tick({ intensity, valence, repetition });
if (posture === "REGROUND") break;   // the loop is saturating: stop it
```

Keel decides; it does not intercept. **The code must supply the three numbers each turn**
(`intensity` 0 to 1, `valence` -1 to 1, `repetition` 0 to 1) and act on the posture. Keel does not
read text. If the project has no way to compute these, use Tiller, which derives them itself. Read
the package README for the API before writing code:
https://github.com/thegubernaut/gubernaut/blob/main/packages/core-js/README.md. For Rust:
`cargo add gubernaut-core` and https://github.com/thegubernaut/gubernaut/blob/main/packages/rust/README.md.

## 4. Prove it works

1. Run the keyless demo from a clone of the repository: `python examples/hard_stop_demo.py`. It must
   print `3 billed, stopped at try 4` for the Gubernaut lane.
2. In the user's project, with the proxy running, `curl http://127.0.0.1:8000/gcc/health` must answer.
3. Send one normal request through the changed client and check the response header `x-gcc-posture`
   (use `client.chat.completions.with_raw_response.create(...)` to read headers in the OpenAI SDK).

## Say these limits to the user

- The first three tries of a verbatim loop are still paid.
- Tiller scores the messages sent as the user. A loop made only of tool calls or model replies is not
  one it catches.
- It is not a content filter and not injection-proof.
- If the proxy is down, the client gets a connection error, so the agent stops rather than running
  unguarded. Keep the proxy running wherever the agent runs.

Full reference: https://github.com/thegubernaut/gubernaut/blob/main/docs/configuration.md
