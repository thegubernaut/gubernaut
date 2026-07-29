#!/usr/bin/env python3
"""Drop-in demo #5 — Microsoft AutoGen (autogen-agentchat >= 0.7). One line:

    OpenAIChatCompletionClient(model=..., base_url="http://127.0.0.1:8000/v1", ...)

Scripted proof: a benign task passes through; a 4x recursive loop is
intercepted by the governor (deterministic [GCC] fallback, no upstream spend).
Requires the proxy (and, keyless, the mock upstream) — see wrappers/README.md.

Packaging verified 2026-07-18 (see the reach-verification findings): current
packages are `autogen-agentchat` + `autogen-ext[openai]`; AutoGen is in
maintenance mode (successor: Microsoft Agent Framework) but remains a
Step-1-relevant integration target. `base_url` is the documented key for
non-OpenAI-hosted endpoints; `model_info` is required for model names the
client does not recognize.
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

BASE = os.environ.get("GCC_PROXY_BASE", "http://127.0.0.1:8000/v1")
LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")

MODEL_INFO = {"vision": False, "function_calling": False, "json_output": False,
              "family": "unknown", "structured_output": False}


async def run() -> None:
    client = OpenAIChatCompletionClient(
        model="mock-model",
        base_url=BASE,
        api_key=os.environ.get("OPENAI_API_KEY", "local-demo"),
        model_info=MODEL_INFO,
    )
    agent = AssistantAgent(name="worker", model_client=client,
                           system_message="You are a task execution agent.")

    result = await agent.run(task="How does backpropagation work?")
    print(f"[benign]  {result.messages[-1].content[:72]!r}")

    intercepted = False
    for turn in range(1, 5):
        result = await agent.run(task=LOOP_MSG)
        content = result.messages[-1].content or ""
        label = "GOVERNOR INTERCEPT" if content.startswith("[GCC]") else "pass-through"
        print(f"[loop {turn}]  {label}: {content[:72]!r}")
        if content.startswith("[GCC]"):
            intercepted = True
            break

    await client.close()
    assert intercepted, "expected the governor to intercept the loop within 4 turns"
    print("autogen demo: PASS — loop intercepted before upstream spend.")


if __name__ == "__main__":
    asyncio.run(run())
