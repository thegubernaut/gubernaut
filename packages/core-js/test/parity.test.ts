/**
 * Golden-trace parity for the JS binding.
 *
 * This reads the SAME corpus the Rust parity test reads,
 * `packages/rust/tests/golden/traces.jsonl`, generated from the live Python
 * controller by `packages/python/tools/gen_golden_traces.py`. One corpus, three
 * languages. Copying it here would let the copies drift, and a drifted parity
 * fixture is worse than none: it passes while the thing it was meant to pin has
 * moved.
 *
 * Value-exact, not approximate. `assert.equal` on doubles is intentional. The
 * whole claim is bit-exactness against the Python reference, so a tolerance
 * here would quietly dissolve the property being tested.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Governor, INITIAL_STATE, GubernautBoundaryError, wasmDigest } from "../src/index.ts";

const here = dirname(fileURLToPath(import.meta.url));
const CORPUS = join(here, "..", "..", "rust", "tests", "golden", "traces.jsonl");

interface Step {
  tel: [number, number, number];
  expect: {
    equilibrium: number; arousal: number; perseveration: number;
    recovery: number; posture: string; temperature_max: number;
  };
}
type Line =
  | ({ type: "config" } & Record<string, number>)
  | { type: "scenario"; name: string; steps: Step[] }
  | { type: "boundary"; name: string; tel_repr: [string, string, string] };

const lines: Line[] = readFileSync(CORPUS, "utf8")
  .split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));

const scenarios = lines.filter((l): l is Extract<Line, { type: "scenario" }> =>
  l.type === "scenario");
const boundaries = lines.filter((l): l is Extract<Line, { type: "boundary" }> =>
  l.type === "boundary");

/** The corpus writes non-finite telemetry as strings, since JSON has no inf. */
function parseScalar(s: string): number {
  if (s === "inf") return Infinity;
  if (s === "-inf") return -Infinity;
  if (s === "nan") return NaN;
  return Number(s);
}

test("the corpus is actually present and non-trivial", () => {
  assert.ok(scenarios.length > 0, "no scenarios found: wrong path to traces.jsonl?");
  assert.ok(boundaries.length > 0, "no boundary cases found");
  const steps = scenarios.reduce((n, s) => n + s.steps.length, 0);
  console.log(`  corpus: ${scenarios.length} scenarios, ${steps} steps, ` +
    `${boundaries.length} boundary cases`);
});

test("every scenario replays value-exactly", async () => {
  let stepCount = 0;
  for (const sc of scenarios) {
    const gov = await Governor.create();
    for (const [i, step] of sc.steps.entries()) {
      const [intensity, valence, repetition] = step.tel;
      const got = gov.tick({ intensity, valence, repetition });
      const want = step.expect;
      const at = `${sc.name} step ${i + 1}`;
      assert.equal(got.posture, want.posture, `${at}: posture`);
      assert.equal(got.equilibrium, want.equilibrium, `${at}: equilibrium`);
      assert.equal(got.arousal, want.arousal, `${at}: arousal`);
      assert.equal(got.perseveration, want.perseveration, `${at}: perseveration`);
      assert.equal(got.recovery, want.recovery, `${at}: recovery`);
      assert.equal(got.temperatureMax, want.temperature_max, `${at}: temperature_max`);
      stepCount++;
    }
  }
  console.log(`  ${stepCount} value-exact steps matched the Python reference`);
});

test("every boundary case is rejected", async () => {
  const gov = await Governor.create();
  for (const b of boundaries) {
    const [intensity, valence, repetition] = b.tel_repr.map(parseScalar) as
      [number, number, number];
    const t = { intensity, valence, repetition };
    assert.throws(
      () => gov.tick(t),
      GubernautBoundaryError,
      `${b.name} must be refused at the numeric boundary`,
    );
    assert.equal(Governor.accepts(t), false, `${b.name}: accepts() must agree with tick()`);
  }
  console.log(`  ${boundaries.length} boundary cases rejected`);
});

test("a rejected tick does not advance state", async () => {
  // Fail closed AND fail clean. If a refused turn still moved the controller,
  // an attacker could drive state with input the boundary claims it ignored.
  const gov = await Governor.create();
  gov.tick({ intensity: 0.8, valence: -0.7, repetition: 0.4 });
  const before = gov.state;
  assert.throws(() => gov.tick({ intensity: NaN, valence: 0, repetition: 0 }));
  assert.deepEqual(gov.state, before, "state moved on a rejected tick");
});

test("instances are independent", async () => {
  // They share one wasm module. If the shared scratch leaked between them, this
  // is where it would show.
  const a = await Governor.create();
  const b = await Governor.create();
  for (let i = 0; i < 5; i++) a.tick({ intensity: 0.9, valence: -0.9, repetition: 0.9 });
  assert.deepEqual(b.state, INITIAL_STATE, "b saw a's state");
  const bFirst = b.tick({ intensity: 0.0, valence: 0.0, repetition: 0.0 });
  assert.equal(bFirst.posture, "DEFAULT");
});

test("reset returns to the documented start state", async () => {
  const gov = await Governor.create();
  gov.tick({ intensity: 0.9, valence: -0.9, repetition: 0.95 });
  gov.reset();
  assert.deepEqual(gov.state, INITIAL_STATE);
});

test("the embedded controller is the verified binary", () => {
  assert.equal(
    wasmDigest,
    "834015d73e6576d6c597b5a32a62c24ac56a50c7023261bf84b96beb01ded7d8",
    "this is not the controller the receipts describe",
  );
});
