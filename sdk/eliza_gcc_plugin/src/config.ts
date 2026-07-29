/**
 * config — resolve GCC settings from the ElizaOS runtime (runtime.getSetting)
 * with a process.env fallback, so the plugin works both inside a full agent and
 * in a bare Node process.
 */

import type { IAgentRuntime } from "@elizaos/core";
import type { GccConfig } from "./gcc-provider.ts";

const DEFAULTS = {
  proxyUrl: "http://127.0.0.1:8000/v1",
  modelLarge: "gpt-4o-mini",
  modelSmall: "gpt-4o-mini",
  defaultMaxTokens: 1024,
  timeoutMs: 30000,
  refusalText:
    "[GCC] This turn was hard-stopped by the Gubernaut Cognitive Controller: " +
    "the agent entered a saturating / perseverating state (REGROUND). The action " +
    "was NOT sent upstream and no budget was spent. Re-ground and change the " +
    "request before retrying.",
};

function setting(runtime: IAgentRuntime | undefined, key: string): string | undefined {
  const fromRuntime = runtime?.getSetting?.(key);
  if (fromRuntime !== undefined && fromRuntime !== null && `${fromRuntime}` !== "") {
    return `${fromRuntime}`;
  }
  const env = process.env[key];
  return env !== undefined && env !== "" ? env : undefined;
}

export function loadConfig(runtime?: IAgentRuntime): GccConfig {
  const apiKey =
    setting(runtime, "GCC_UPSTREAM_API_KEY") ??
    setting(runtime, "OPENAI_API_KEY") ??
    "";
  const maxTokens = Number(setting(runtime, "GCC_MAX_TOKENS") ?? DEFAULTS.defaultMaxTokens);
  const timeoutMs = Number(setting(runtime, "GCC_TIMEOUT_MS") ?? DEFAULTS.timeoutMs);
  return {
    proxyUrl: setting(runtime, "GCC_PROXY_URL") ?? DEFAULTS.proxyUrl,
    apiKey,
    modelLarge: setting(runtime, "GCC_MODEL_LARGE") ?? DEFAULTS.modelLarge,
    modelSmall: setting(runtime, "GCC_MODEL_SMALL") ?? DEFAULTS.modelSmall,
    defaultMaxTokens: Number.isFinite(maxTokens) ? maxTokens : DEFAULTS.defaultMaxTokens,
    timeoutMs: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : DEFAULTS.timeoutMs,
    refusalText: setting(runtime, "GCC_REFUSAL_TEXT") ?? DEFAULTS.refusalText,
  };
}
