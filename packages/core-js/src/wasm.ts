/**
 * Loading and verifying the embedded controller.
 *
 * The wasm exports a scalar-only C ABI: no heap, no pointers, no wasm-bindgen
 * glue. `gcc_tick` performs one governed tick and returns a posture code; five
 * getters read back the f64 outputs it stashed. That is the entire interface,
 * which is why this file is short and why the module runs anywhere
 * `WebAssembly` exists.
 */
import { WASM_BASE64, WASM_BYTE_LENGTH, WASM_SHA256 } from "./wasm-bytes.ts";
import { GubernautWasmError } from "./errors.ts";

/** The exports the controller module is contractually required to provide. */
export interface CoreExports {
  gcc_tick(
    intensity: number, valence: number, repetition: number,
    inEquilibrium: number, inArousal: number,
    inPerseveration: number, inRecovery: number,
  ): number;
  gcc_last_equilibrium(): number;
  gcc_last_arousal(): number;
  gcc_last_perseveration(): number;
  gcc_last_recovery(): number;
  gcc_last_temperature_max(): number;
  gcc_abi_version(): number;
}

/** ABI generation this package speaks. `gcc_abi_version()` must return it. */
export const SUPPORTED_ABI_VERSION = 1;

const REQUIRED_EXPORTS = [
  "gcc_tick",
  "gcc_last_equilibrium",
  "gcc_last_arousal",
  "gcc_last_perseveration",
  "gcc_last_recovery",
  "gcc_last_temperature_max",
  "gcc_abi_version",
] as const;

function decodeBase64(b64: string): Uint8Array {
  // atob exists in browsers, workerd, Deno, Bun and Node >= 16. Buffer does
  // not exist outside Node. Preferring atob keeps one path on every runtime.
  if (typeof atob === "function") {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  // Fallback for an exotic host without atob.
  const B = (globalThis as { Buffer?: { from(s: string, e: string): Uint8Array } }).Buffer;
  if (B) return new Uint8Array(B.from(b64, "base64"));
  throw new GubernautWasmError(
    "no base64 decoder on this runtime: neither atob nor Buffer is available",
  );
}

let cached: Promise<CoreExports> | null = null;

/**
 * Instantiate the controller once per process and share it.
 *
 * Sharing is safe. The ABI is stateless-by-parameter: the caller owns the four
 * controller scalars and threads them in and out on every tick, so the module's
 * only internal state is a scratch cell written by `gcc_tick` and read by the
 * getters immediately afterwards, synchronously, with no await between. Two
 * Governor instances therefore cannot observe each other's values. If a future
 * ABI ever made a tick asynchronous, this sharing would have to go.
 */
export function loadCore(): Promise<CoreExports> {
  if (cached) return cached;
  cached = (async () => {
    const bytes = decodeBase64(WASM_BASE64);
    if (bytes.length !== WASM_BYTE_LENGTH) {
      throw new GubernautWasmError(
        `embedded controller is ${bytes.length} bytes, expected ${WASM_BYTE_LENGTH}. ` +
        "The package is corrupt; reinstall it.",
      );
    }
    let instance: WebAssembly.Instance;
    try {
      // Compile then instantiate, rather than the one-shot BufferSource
      // overload: TypeScript resolves that overload against `Module` on some
      // lib configurations, and this form is unambiguous on all of them. It is
      // also the shape workerd documents.
      const module = await WebAssembly.compile(bytes as BufferSource);
      instance = await WebAssembly.instantiate(module, {});
    } catch (cause) {
      throw new GubernautWasmError(
        `could not instantiate the controller: ${(cause as Error).message}`,
        { cause },
      );
    }
    const ex = instance.exports as unknown as CoreExports;

    // A module that loads but is missing an export would fail later, deep in a
    // tick, as an unhelpful "not a function". Check the contract at load.
    const missing = REQUIRED_EXPORTS.filter(
      (k) => typeof (ex as unknown as Record<string, unknown>)[k] !== "function",
    );
    if (missing.length) {
      throw new GubernautWasmError(
        `controller module is missing exports: ${missing.join(", ")}. ` +
        "This is not a Gubernaut controller build.",
      );
    }
    const abi = ex.gcc_abi_version();
    if (abi !== SUPPORTED_ABI_VERSION) {
      throw new GubernautWasmError(
        `controller ABI ${abi}, this package speaks ${SUPPORTED_ABI_VERSION}. ` +
        "Upgrade @gubernaut/core.",
      );
    }
    return ex;
  })();
  return cached;
}

/** SHA-256 of the embedded controller, for provenance checks. */
export const wasmDigest = WASM_SHA256;
