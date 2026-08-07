/**
 * @gubernaut/plugin-gcc — an ElizaOS plugin that natively routes an agent's LLM
 * calls through the Gubernaut Cognitive Controller (GCC) local proxy.
 *
 * Registering this plugin makes every `runtime.useModel(ModelType.TEXT_LARGE|
 * TEXT_SMALL, ...)` call flow through the GCC proxy: deterministic homeostatic
 * governance (postures DEFAULT / INHIBIT / REGROUND), a runaway-loop hard-stop
 * at zero upstream cost, and cost containment. A hard-stop surfaces to the agent
 * as an explicit governed refusal, never a silent drop.
 *
 * ElizaOS interface verified live 2026-07-21:
 *   - docs.elizaos.ai/plugins/reference (Plugin.models map, ModelHandler)
 *   - elizaOS/eliza @develop packages/docs/runtime/models.mdx
 *     (ModelType string values: TEXT_LARGE="text:large", TEXT_SMALL="text:small";
 *      handler shape (runtime, params) => Promise<string>).
 */

import type { Plugin, IAgentRuntime } from "@elizaos/core";
import { loadConfig } from "./config.ts";
import { callGcc, type TextParams } from "./gcc-provider.ts";
import { GubernautConfigError } from "./errors.ts";

// ElizaOS ModelType keys. The @develop docs give lowercase colon values
// ("text:large"), but the PUBLISHED @elizaos/core 1.x enum values are the
// constant names ("TEXT_LARGE") — found in clean-room verification against
// @elizaos/core 1.7.2 (2026-07-22). The models map registers BOTH spellings,
// so the plugin binds under either runtime. Literals keep this module free of
// a runtime import from @elizaos/core (portable, type-only peer).
const MODEL_TEXT_LARGE = "text:large";
const MODEL_TEXT_SMALL = "text:small";
const MODEL_TEXT_LARGE_V1 = "TEXT_LARGE";
const MODEL_TEXT_SMALL_V1 = "TEXT_SMALL";

async function handleTextLarge(runtime: IAgentRuntime, params: TextParams): Promise<string> {
  const cfg = loadConfig(runtime);
  const result = await callGcc(cfg, cfg.modelLarge, params);
  return result.text;
}

async function handleTextSmall(runtime: IAgentRuntime, params: TextParams): Promise<string> {
  const cfg = loadConfig(runtime);
  const result = await callGcc(cfg, cfg.modelSmall, params);
  return result.text;
}

export const gccPlugin: Plugin = {
  name: "@gubernaut/plugin-gcc",
  description:
    "Routes ElizaOS LLM calls through the Gubernaut Cognitive Controller (GCC) " +
    "local proxy: deterministic homeostatic governance, runaway-loop hard-stop, " +
    "and cost containment. Hard-stops surface as a governed refusal.",
  config: {
    GCC_PROXY_URL: process.env.GCC_PROXY_URL,
    GCC_UPSTREAM_API_KEY: process.env.GCC_UPSTREAM_API_KEY,
    GCC_MODEL_LARGE: process.env.GCC_MODEL_LARGE,
    GCC_MODEL_SMALL: process.env.GCC_MODEL_SMALL,
    GCC_MAX_TOKENS: process.env.GCC_MAX_TOKENS,
  },
  async init(_config: Record<string, string>, runtime: IAgentRuntime): Promise<void> {
    const cfg = loadConfig(runtime);
    if (!cfg.apiKey) {
      throw new Error(
        "[plugin-gcc] no upstream API key. Set GCC_UPSTREAM_API_KEY (the key the " +
          "GCC proxy forwards to your upstream).",
      );
    }
    // A missing/invalid proxy is a deploy error, not a silent fallthrough to an
    // ungoverned upstream — surface it early. (Before 0.1.1 this guard was dead:
    // an empty GCC_PROXY_URL silently defaulted to loopback, and a malformed URL
    // only blew up later inside fetch. Now the URL is validated at init.)
    let parsed: URL;
    try {
      parsed = new URL(cfg.proxyUrl);
    } catch {
      throw new GubernautConfigError(
        `[plugin-gcc] GCC_PROXY_URL is not a valid URL: ${JSON.stringify(cfg.proxyUrl)}`,
      );
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      throw new GubernautConfigError(
        `[plugin-gcc] GCC_PROXY_URL must be http(s): ${JSON.stringify(cfg.proxyUrl)}`,
      );
    }
  },
  models: {
    [MODEL_TEXT_LARGE]: handleTextLarge,
    [MODEL_TEXT_LARGE_V1]: handleTextLarge,
    [MODEL_TEXT_SMALL]: handleTextSmall,
    [MODEL_TEXT_SMALL_V1]: handleTextSmall,
  },
};

export default gccPlugin;
export { callGcc, loadConfig };

// Preferred names as of 1.0.1. "gcc" reads as the GNU Compiler Collection to
// anyone who has not read the paper, so the Gubernaut-spelled names lead in the
// docs. These are ALIASES, not replacements: `gccPlugin` and `callGcc` are the
// published 1.0.0 surface and keep working indefinitely. Same object, same
// function — asserted in test/plugin-keys.test.ts, because an alias that
// drifted from its original would be worse than no alias at all.
export const gubernautPlugin = gccPlugin;
export { callGcc as callGubernaut };

export {
  GubernautError,
  GubernautConnectionError,
  GubernautTimeoutError,
  GubernautConfigError,
} from "./errors.ts";
export type { GccConfig, TextParams, GccCallResult } from "./gcc-provider.ts";
// Gubernaut-spelled type alias for GccConfig; the original name is unchanged.
export type { GccConfig as GubernautConfig } from "./gcc-provider.ts";
