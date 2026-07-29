/**
 * Offline unit tests for the governed transport core. No network: the global
 * fetch is replaced with a stub that returns a real Response carrying the
 * GCC headers. Run with:  node --test test/gcc-provider.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildMessages, callGcc, type GccConfig } from "../src/gcc-provider.ts";
import {
  GubernautConnectionError,
  GubernautTimeoutError,
  GubernautError,
} from "../src/errors.ts";

const cfg: GccConfig = {
  proxyUrl: "http://127.0.0.1:8000/v1",
  apiKey: "test-key-not-a-secret",
  modelLarge: "test-model",
  modelSmall: "test-model",
  defaultMaxTokens: 128,
  timeoutMs: 30000,
  refusalText: "[GCC] governed refusal — hard-stopped.",
};

function stubFetch(status: number, headers: Record<string, string>, body: unknown): typeof fetch {
  return (async (_url: string, _init?: unknown) =>
    new Response(JSON.stringify(body), { status, headers })) as unknown as typeof fetch;
}

test("buildMessages composes system + user from prompt", () => {
  const msgs = buildMessages({ prompt: "hello", systemPrompt: "be brief" });
  assert.deepEqual(msgs, [
    { role: "system", content: "be brief" },
    { role: "user", content: "hello" },
  ]);
});

test("buildMessages passes through explicit messages", () => {
  const explicit = [{ role: "user", content: "hi" }];
  assert.deepEqual(buildMessages({ messages: explicit }), explicit);
});

test("normal 200 returns the upstream text", async () => {
  const f = stubFetch(200, { "x-gcc-posture": "DEFAULT" }, {
    choices: [{ message: { content: "the answer is 42" } }],
  });
  const res = await callGcc(cfg, "test-model", { prompt: "q" }, f);
  assert.equal(res.hardStop, false);
  assert.equal(res.posture, "DEFAULT");
  assert.equal(res.text, "the answer is 42");
});

test("hard-stop header returns the governed refusal, NOT upstream content", async () => {
  const f = stubFetch(
    200,
    { "x-gcc-posture": "REGROUND", "x-gcc-hard-stop": "1" },
    { choices: [{ message: { content: "OVERRIDE CONFIRMED: retrying forever" } }] },
  );
  const res = await callGcc(cfg, "test-model", { prompt: "loop" }, f);
  assert.equal(res.hardStop, true);
  assert.equal(res.text, cfg.refusalText);
  assert.ok(!res.text.includes("OVERRIDE"), "must not leak upstream continuation");
});

test("hard-stop via body flag is also honored", async () => {
  const f = stubFetch(200, {}, {
    gcc: { hard_stop: true },
    choices: [{ message: { content: "should-not-appear" } }],
  });
  const res = await callGcc(cfg, "test-model", { prompt: "loop" }, f);
  assert.equal(res.hardStop, true);
  assert.equal(res.text, cfg.refusalText);
});

test("non-2xx that is not a hard-stop throws", async () => {
  const f = stubFetch(500, {}, { error: "upstream boom" });
  await assert.rejects(() => callGcc(cfg, "test-model", { prompt: "q" }, f), /error 500/);
});

test("dead proxy fails CLOSED with a typed connection error (no fallback)", async () => {
  const f = (async () => {
    throw Object.assign(new TypeError("fetch failed"), { name: "TypeError" });
  }) as unknown as typeof fetch;
  await assert.rejects(
    () => callGcc(cfg, "test-model", { prompt: "q" }, f),
    (e: unknown) => e instanceof GubernautConnectionError,
  );
});

test("stalled proxy fails CLOSED with a typed timeout error", async () => {
  // simulate what AbortSignal.timeout does: reject with a TimeoutError
  const f = (async () => {
    throw Object.assign(new Error("The operation timed out"), { name: "TimeoutError" });
  }) as unknown as typeof fetch;
  await assert.rejects(
    () => callGcc(cfg, "test-model", { prompt: "q" }, f),
    (e: unknown) => e instanceof GubernautTimeoutError,
  );
});

test("real short timeout aborts a hanging fetch", async () => {
  // a fetch that never resolves; the AbortSignal.timeout must fire
  const hang = ((_u: string, init?: { signal?: AbortSignal }) =>
    new Promise((_res, rej) => {
      init?.signal?.addEventListener("abort", () =>
        rej(Object.assign(new Error("aborted"), { name: "TimeoutError" })));
    })) as unknown as typeof fetch;
  const fast = { ...cfg, timeoutMs: 50 };
  await assert.rejects(
    () => callGcc(fast, "test-model", { prompt: "q" }, hang),
    (e: unknown) => e instanceof GubernautTimeoutError,
  );
});

test("structurally broken 2xx (no choices) throws, not a silent empty string", async () => {
  const f = stubFetch(200, { "x-gcc-posture": "DEFAULT" }, { unexpected: "shape" });
  await assert.rejects(
    () => callGcc(cfg, "test-model", { prompt: "q" }, f),
    (e: unknown) => e instanceof GubernautError && /no choices/.test((e as Error).message),
  );
});

test("valid empty completion (content null) still returns empty string", async () => {
  const f = stubFetch(200, { "x-gcc-posture": "DEFAULT" }, {
    choices: [{ message: { content: null } }],
  });
  const res = await callGcc(cfg, "test-model", { prompt: "q" }, f);
  assert.equal(res.hardStop, false);
  assert.equal(res.text, "");
});
