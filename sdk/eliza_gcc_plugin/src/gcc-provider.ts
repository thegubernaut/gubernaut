/**
 * gcc-provider — the governed transport core (framework-agnostic, no ElizaOS
 * import, fully unit-testable offline).
 *
 * Routes a text-generation request through the Gubernaut Cognitive Controller
 * (GCC) local proxy (an OpenAI-compatible endpoint). Reads the proxy's
 * `x-gcc-posture` / `x-gcc-hard-stop` response headers; when the controller
 * hard-stops a saturating/looping agent, this returns a **governed refusal**
 * instead of relaying the upstream continuation — never a silent drop.
 */

import {
  GubernautError,
  GubernautConnectionError,
  GubernautTimeoutError,
} from "./errors.ts";

export interface GccConfig {
  /** GCC proxy base, OpenAI-compatible, e.g. http://127.0.0.1:8000/v1 */
  proxyUrl: string;
  /** upstream API key the proxy forwards verbatim */
  apiKey: string;
  modelLarge: string;
  modelSmall: string;
  defaultMaxTokens: number;
  /** text returned to the agent when the controller hard-stops the turn */
  refusalText: string;
  /** fetch deadline in ms; a stalled proxy fails closed instead of hanging */
  timeoutMs: number;
}

export interface ChatMessage {
  role: string;
  content: string;
}

/** Subset of ElizaOS TextGenerationParams this provider consumes. */
export interface TextParams {
  prompt?: string;
  messages?: ChatMessage[];
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
  stopSequences?: string[];
}

export interface GccCallResult {
  text: string;
  posture: string;
  hardStop: boolean;
  status: number;
}

export function buildMessages(params: TextParams): ChatMessage[] {
  if (params.messages && params.messages.length > 0) {
    return params.messages;
  }
  const msgs: ChatMessage[] = [];
  if (params.systemPrompt) {
    msgs.push({ role: "system", content: params.systemPrompt });
  }
  msgs.push({ role: "user", content: params.prompt ?? "" });
  return msgs;
}

/**
 * Call the GCC proxy. `fetchImpl` is injectable for testing (defaults to the
 * global fetch). Throws only on genuine transport/upstream errors; a controller
 * hard-stop is a first-class, non-error outcome (governed refusal).
 */
export async function callGcc(
  cfg: GccConfig,
  model: string,
  params: TextParams,
  fetchImpl: typeof fetch = fetch,
): Promise<GccCallResult> {
  const body: Record<string, unknown> = {
    model,
    messages: buildMessages(params),
    max_completion_tokens: params.maxTokens ?? cfg.defaultMaxTokens,
  };
  if (params.temperature !== undefined) {
    body.temperature = params.temperature;
  }
  if (params.stopSequences && params.stopSequences.length > 0) {
    body.stop = params.stopSequences;
  }

  const url = `${cfg.proxyUrl.replace(/\/$/, "")}/chat/completions`;
  const timeoutMs = cfg.timeoutMs && cfg.timeoutMs > 0 ? cfg.timeoutMs : 30000;

  // Bounded, guarded transport. A stalled proxy fails closed at the deadline
  // (was an unbounded hang in 0.1.0); a refused/broken connection surfaces as a
  // typed error with the cause preserved (was a raw `TypeError: fetch failed`).
  // Neither path ever falls back to an ungoverned upstream.
  let resp: Response;
  try {
    resp = await fetchImpl(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${cfg.apiKey}`,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    const name = (e as { name?: string })?.name;
    if (name === "TimeoutError" || name === "AbortError") {
      throw new GubernautTimeoutError(url, timeoutMs, e);
    }
    throw new GubernautConnectionError(url, e);
  }

  const posture = resp.headers.get("x-gcc-posture") ?? "";
  const hardStopHdr = resp.headers.get("x-gcc-hard-stop") ?? "";
  const headerHardStop = hardStopHdr === "1" || hardStopHdr === "true";

  // Non-2xx that is NOT a governed hard-stop is a real transport error.
  if (!resp.ok && !headerHardStop) {
    throw new GubernautError(`[plugin-gcc] proxy/upstream error ${resp.status}`);
  }

  let data: any = {};
  try {
    data = await resp.json();
  } catch {
    data = {};
  }
  const hardStop = headerHardStop || Boolean(data?.gcc?.hard_stop);

  if (hardStop) {
    // Governed refusal: do NOT relay any upstream continuation.
    return {
      text: cfg.refusalText,
      posture: posture || "REGROUND",
      hardStop: true,
      status: resp.status,
    };
  }

  // A structurally broken 2xx (no choices array) is NOT a valid empty
  // completion — throw rather than silently returning "" (a genuine empty /
  // tool-only completion, content null, still returns "" as before).
  const choices = (data as { choices?: unknown[] })?.choices;
  if (!Array.isArray(choices) || choices.length === 0) {
    throw new GubernautError(
      `[plugin-gcc] malformed upstream response (no choices) from ${url}`,
    );
  }
  const first = choices[0] as { message?: { content?: string } };
  const text = first?.message?.content ?? "";
  return { text, posture, hardStop: false, status: resp.status };
}
