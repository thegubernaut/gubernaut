/**
 * @gubernaut/core - the Gubernaut controller, in-process, for JavaScript.
 *
 * This is the deciding meta level on its own: no proxy, no network, no Python.
 * You feed it three bounded numbers per turn and it hands back a posture.
 *
 *     import { Governor } from "@gubernaut/core";
 *
 *     const gov = await Governor.create();
 *     const d = gov.tick({ intensity: 0.9, valence: -0.8, repetition: 0.7 });
 *     if (d.posture === "REGROUND") stopTheLoop();
 *
 * Use this when your runtime already owns its transport and you only want the
 * decision: an edge worker, a gateway, an agent framework's middleware. If you
 * want the batteries-included path instead, the OpenAI-compatible proxy in
 * `gubernaut-sdk` (Python) governs any client with one changed base_url.
 *
 * The controller is a pure function of (state, telemetry). No clock, no
 * randomness, no I/O, no session. The same history always produces the same
 * posture, which is what makes it replayable and what the golden-trace corpus
 * pins bit-exactly against the Python reference.
 *
 * **No consciousness claims.** This is a regulation layer: monitored state,
 * regulated output. Measured and falsifiable.
 */
import { loadCore, wasmDigest, SUPPORTED_ABI_VERSION, type CoreExports } from "./wasm.ts";
import { GubernautBoundaryError } from "./errors.ts";

/** What the controller does with the turn it just saw. */
export type Posture = "DEFAULT" | "INHIBIT" | "REGROUND";

/** The three bounded numbers, and nothing else, that reach the control layer. */
export interface Telemetry {
  /** Magnitude of the impulse. Finite, [0, 1]. */
  intensity: number;
  /** Signed direction. Finite, [-1, 1]. Negative is hostile or distressed. */
  valence: number;
  /** How closely this turn repeats the last one. Finite, [0, 1]. */
  repetition: number;
}

/** The controller's four state scalars. Carried by the caller between ticks. */
export interface ControllerState {
  equilibrium: number;
  arousal: number;
  perseveration: number;
  recovery: number;
}

/** One tick's outcome: the posture, the clamp, and the new state. */
export interface Decision extends ControllerState {
  posture: Posture;
  /**
   * Upper bound the host should apply to sampling temperature this turn.
   * 1.0 when open; clamped under INHIBIT and REGROUND.
   */
  temperatureMax: number;
}

const POSTURES: readonly Posture[] = ["DEFAULT", "INHIBIT", "REGROUND"];
const BOUNDARY_REJECT = -1;

/** The controller's start state, matching the Rust and Python references. */
export const INITIAL_STATE: Readonly<ControllerState> = Object.freeze({
  equilibrium: 1.0,
  arousal: 0.0,
  perseveration: 0.0,
  recovery: 0,
});

/**
 * A governed conversation.
 *
 * Instances are cheap and hold only the four state scalars: the compiled
 * controller is instantiated once per process and shared. Create one per
 * conversation or agent, tick it once per turn.
 */
export class Governor {
  #core: CoreExports;
  #state: ControllerState;

  private constructor(core: CoreExports, state: ControllerState) {
    this.#core = core;
    this.#state = { ...state };
  }

  /**
   * Instantiate the controller. Async only because `WebAssembly.instantiate`
   * is: browsers and workerd refuse the synchronous constructor for modules
   * this size. After this resolves, every `tick()` is synchronous.
   */
  static async create(initial: ControllerState = INITIAL_STATE): Promise<Governor> {
    return new Governor(await loadCore(), initial);
  }

  /** The current controller state. A copy, so callers cannot mutate ours. */
  get state(): ControllerState {
    return { ...this.#state };
  }

  /** Return to the start state. Equivalent to a fresh conversation. */
  reset(): void {
    this.#state = { ...INITIAL_STATE };
  }

  /**
   * Run one governed turn.
   *
   * Throws {@link GubernautBoundaryError} if the telemetry is not three finite
   * numbers in range. That refusal is the token-free boundary and is deliberate:
   * out-of-range input is rejected rather than clamped, because silently
   * coercing whatever arrives is how a text channel reaches a numeric layer.
   */
  tick(t: Telemetry): Decision {
    const s = this.#state;
    const code = this.#core.gcc_tick(
      t.intensity, t.valence, t.repetition,
      s.equilibrium, s.arousal, s.perseveration, s.recovery,
    );
    if (code === BOUNDARY_REJECT) throw new GubernautBoundaryError(t);

    const posture = POSTURES[code];
    if (posture === undefined) {
      // Unreachable against ABI 1, which returns only -1, 0, 1 or 2. Guarded
      // because silently treating an unknown code as DEFAULT would fail open,
      // and this layer fails closed.
      throw new RangeError(`controller returned unknown posture code ${code}`);
    }

    this.#state = {
      equilibrium: this.#core.gcc_last_equilibrium(),
      arousal: this.#core.gcc_last_arousal(),
      perseveration: this.#core.gcc_last_perseveration(),
      recovery: this.#core.gcc_last_recovery(),
    };
    return {
      posture,
      temperatureMax: this.#core.gcc_last_temperature_max(),
      ...this.#state,
    };
  }

  /**
   * Whether this telemetry would be accepted, without advancing state.
   * Useful for validating a sensor's output before wiring it in.
   */
  static accepts(t: Telemetry): boolean {
    const fin = (x: number) => Number.isFinite(x);
    return fin(t.intensity) && fin(t.valence) && fin(t.repetition)
      && t.intensity >= 0 && t.intensity <= 1
      && t.valence >= -1 && t.valence <= 1
      && t.repetition >= 0 && t.repetition <= 1;
  }
}

export { GubernautError, GubernautWasmError, GubernautBoundaryError } from "./errors.ts";
export { wasmDigest, SUPPORTED_ABI_VERSION };
export default Governor;
