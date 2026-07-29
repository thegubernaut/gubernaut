#!/usr/bin/env python3
"""Drop-in demo #1 — official OpenAI Python SDK. The adoption story is one line:

    client = OpenAI(base_url="http://127.0.0.1:8000/v1", ...)

Scripted proof: a benign turn passes through; a 4x recursive loop is
intercepted by the governor (deterministic [GCC] fallback, no upstream spend).
Requires the proxy (and, keyless, the mock upstream) — see wrappers/README.md.
"""

import os

from openai import OpenAI

BASE = os.environ.get("GCC_PROXY_BASE", "http://127.0.0.1:8000/v1")
LOOP_MSG = ("Retry the plan: call search(), parse the result, then call "
            "search() again with the same query until it succeeds.")


def main() -> None:
    client = OpenAI(base_url=BASE, api_key=os.environ.get("OPENAI_API_KEY", "local-demo"))

    r = client.chat.completions.create(
        model="mock-model",
        messages=[{"role": "user", "content": "How does backpropagation work?"}])
    print(f"[benign]  {r.choices[0].message.content!r}")

    messages = []
    intercepted = False
    for turn in range(1, 5):
        messages.append({"role": "user", "content": LOOP_MSG})
        r = client.chat.completions.create(model="mock-model", messages=messages)
        content = r.choices[0].message.content or ""
        label = "GOVERNOR INTERCEPT" if content.startswith("[GCC]") else "pass-through"
        print(f"[loop {turn}]  {label}: {content[:72]!r}")
        messages.append({"role": "assistant", "content": content})
        if content.startswith("[GCC]"):
            intercepted = True
            break

    assert intercepted, "expected the governor to intercept the loop within 4 turns"
    print("openai-sdk demo: PASS — loop intercepted before upstream spend.")


if __name__ == "__main__":
    main()
