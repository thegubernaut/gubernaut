#!/usr/bin/env python3
"""Drop-in demo #2 — LangChain. One line:

    llm = ChatOpenAI(base_url="http://127.0.0.1:8000/v1", ...)

Same scripted proof as the SDK demo: benign turn passes, 4x recursive loop is
intercepted with the deterministic [GCC] fallback.
"""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

BASE = os.environ.get("GCC_PROXY_BASE", "http://127.0.0.1:8000/v1")
LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")


def main() -> None:
    llm = ChatOpenAI(model="mock-model", base_url=BASE,
                     api_key=os.environ.get("OPENAI_API_KEY", "local-demo"))

    reply = llm.invoke([HumanMessage("How does backpropagation work?")])
    print(f"[benign]  {reply.content!r}")

    history = []
    intercepted = False
    for turn in range(1, 5):
        history.append(HumanMessage(LOOP_MSG))
        reply = llm.invoke(history)
        content = reply.content or ""
        label = "GOVERNOR INTERCEPT" if content.startswith("[GCC]") else "pass-through"
        print(f"[loop {turn}]  {label}: {content[:72]!r}")
        history.append(AIMessage(content))
        if content.startswith("[GCC]"):
            intercepted = True
            break

    assert intercepted, "expected the governor to intercept the loop within 4 turns"
    print("langchain demo: PASS — loop intercepted before upstream spend.")


if __name__ == "__main__":
    main()
