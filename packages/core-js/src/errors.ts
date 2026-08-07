/**
 * Typed errors. Every failure mode gets its own class so a caller can branch on
 * the kind rather than string-matching a message.
 */

export class GubernautError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "GubernautError";
  }
}

/** The embedded controller could not be decoded, instantiated, or verified. */
export class GubernautWasmError extends GubernautError {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "GubernautWasmError";
  }
}

/**
 * Telemetry was outside the finite unit range the controller accepts.
 *
 * This is the token-free boundary doing its job, not a bug. The controller
 * takes three bounded numbers and nothing else; anything that is not a finite
 * float in range is refused at the door rather than coerced, because coercion
 * is how a text channel gets in.
 */
export class GubernautBoundaryError extends GubernautError {
  readonly telemetry: { intensity: number; valence: number; repetition: number };
  constructor(t: { intensity: number; valence: number; repetition: number }) {
    super(
      "telemetry rejected at the numeric boundary: " +
      `intensity=${t.intensity}, valence=${t.valence}, repetition=${t.repetition}. ` +
      "intensity and repetition must be finite in [0, 1]; valence finite in [-1, 1].",
    );
    this.name = "GubernautBoundaryError";
    this.telemetry = t;
  }
}
