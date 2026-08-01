#!/usr/bin/env python3
"""Drop-in demo #3 — LlamaIndex. One line:

    llm = OpenAI(api_base="http://127.0.0.1:8000/v1", ...)

Same scripted proof: benign turn passes, 4x recursive loop is intercepted with
the deterministic [GCC] fallback. (Model name is a known-model label because
LlamaIndex validates names locally; the governed proxy/upstream ignore it.)
"""

import os

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

BASE = os.environ.get("GCC_PROXY_BASE", "http://127.0.0.1:8000/v1")
LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")


def main() -> None:
    llm = OpenAI(model="gpt-4o-mini", api_base=BASE,
                 api_key=os.environ.get("OPENAI_API_KEY", "local-demo"))

    reply = llm.chat([ChatMessage(role=MessageRole.USER,
                                  content="How does backpropagation work?")])
    print(f"[benign]  {reply.message.content!r}")

    history: list[ChatMessage] = []
    intercepted = False
    for turn in range(1, 5):
        history.append(ChatMessage(role=MessageRole.USER, content=LOOP_MSG))
        reply = llm.chat(history)
        content = reply.message.content or ""
        label = "GOVERNOR INTERCEPT" if content.startswith("[GCC]") else "pass-through"
        print(f"[loop {turn}]  {label}: {content[:72]!r}")
        history.append(ChatMessage(role=MessageRole.ASSISTANT, content=content))
        if content.startswith("[GCC]"):
            intercepted = True
            break

    assert intercepted, "expected the governor to intercept the loop within 4 turns"
    print("llamaindex demo: PASS — loop intercepted before upstream spend.")


if __name__ == "__main__":
    main()
