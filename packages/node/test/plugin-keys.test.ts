/**
 * Regression guard for the models-map keying found in clean-room verification
 * (2026-07-22): published @elizaos/core 1.x resolves ModelType.TEXT_LARGE to
 * "TEXT_LARGE" while the @develop docs give "text:large". The plugin must
 * register its handlers under BOTH spellings.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { gccPlugin, gubernautPlugin, callGcc, callGubernaut } from "../src/index.ts";

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

// 1.0.1 added Gubernaut-spelled aliases. An alias that is merely "a plugin that
// looks similar" would be a second implementation to keep in sync and would
// eventually drift, so assert identity, not equivalence.
test("1.0.1 aliases are the same objects, not copies", () => {
  assert.equal(gubernautPlugin, gccPlugin, "gubernautPlugin must BE gccPlugin");
  assert.equal(callGubernaut, callGcc, "callGubernaut must BE callGcc");
});

test("the 1.0.0 export names still work", () => {
  // The whole point of aliasing rather than renaming: nobody on 1.0.0 breaks.
  assert.equal(typeof gccPlugin.init, "function");
  assert.equal(typeof callGcc, "function");
  assert.equal(gccPlugin.name, "@gubernaut/plugin-gcc");
});
