/**
 * Typed errors for @gubernaut/plugin-gcc (added 0.1.1).
 *
 * Before 0.1.1 a dead proxy surfaced as a raw `TypeError: fetch failed` and a
 * stalled proxy hung forever (no fetch timeout). These give integrators a
 * stable, catchable surface and make the fail-CLOSED contract explicit: when
 * the governed proxy is unreachable or slow, you get a typed error with the
 * original transport failure preserved in `.cause` — never a silent
 * fall-through to an ungoverned upstream.
 */

export class GubernautError extends Error {}

export class GubernautConnectionError extends GubernautError {
  constructor(url: string, cause?: unknown) {
    super(
      `[plugin-gcc] GCC proxy unreachable at ${url} — refusing to proceed ungoverned.`,
      cause !== undefined ? { cause } : undefined,
    );
    this.name = "GubernautConnectionError";
  }
}

export class GubernautTimeoutError extends GubernautError {
  constructor(url: string, ms: number, cause?: unknown) {
    super(
      `[plugin-gcc] GCC proxy did not respond within ${ms}ms at ${url} — failing closed.`,
      cause !== undefined ? { cause } : undefined,
    );
    this.name = "GubernautTimeoutError";
  }
}

export class GubernautConfigError extends GubernautError {
  constructor(message: string) {
    super(message);
    this.name = "GubernautConfigError";
  }
}
