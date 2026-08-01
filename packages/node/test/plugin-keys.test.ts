/**
 * Regression guard for the models-map keying found in clean-room verification
 * (2026-07-22): published @elizaos/core 1.x resolves ModelType.TEXT_LARGE to
 * "TEXT_LARGE" while the @develop docs give "text:large". The plugin must
 * register its handlers under BOTH spellings.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { gccPlugin } from "../src/index.ts";

test("models map registers both ModelType spellings", () => {
  for (const key of ["text:large", "TEXT_LARGE", "text:small", "TEXT_SMALL"]) {
    assert.equal(typeof gccPlugin.models?.[key], "function", key);
  }
});

test("large/small spellings share one handler each", () => {
  assert.equal(gccPlugin.models?.["text:large"], gccPlugin.models?.["TEXT_LARGE"]);
  assert.equal(gccPlugin.models?.["text:small"], gccPlugin.models?.["TEXT_SMALL"]);
  assert.notEqual(gccPlugin.models?.["text:large"], gccPlugin.models?.["text:small"]);
});
