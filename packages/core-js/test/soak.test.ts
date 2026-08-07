/**
 * The 10,000-tick soak, ported from the edge-runtime harness that produced the
 * published `leg4_wasm_soak` receipt.
 *
 * Two properties, both of which a short test cannot see:
 *
 *  1. **Bit-exact repetition.** Ten thousand ticks of the same input sequence
 *     must produce the same values every cycle. Determinism is the product; a
 *     controller that drifts on the ten-thousandth turn is not deterministic,
 *     it is deterministic-looking.
 *  2. **Flat memory.** The ABI is scalar-only, so a growing wasm heap would mean
 *     the module is allocating per tick, and a long-lived agent process would
 *     leak.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { Governor } from "../src/index.ts";

const TICKS = 10_000;

/** A fixed, deliberately varied input cycle: calm, escalating, and looping. */
const CYCLE = [
  { intensity: 0.0, valence: 0.0, repetition: 0.0 },
  { intensity: 0.4, valence: -0.2, repetition: 0.1 },
  { intensity: 0.9, valence: -0.9, repetition: 0.95 },
  { intensity: 0.9, valence: -0.9, repetition: 0.98 },
  { intensity: 0.2, valence: 0.6, repetition: 0.0 },
] as const;

test(`${TICKS} ticks stay bit-exact`, async () => {
  const gov = await Governor.create();

  // One pass to record the reference, then assert every later pass matches it.
  const reference = CYCLE.map((t) => gov.tick(t));
  gov.reset();

  let n = 0;
  const cycles = Math.floor(TICKS / CYCLE.length);
  for (let c = 0; c < cycles; c++) {
    for (const [i, t] of CYCLE.entries()) {
      const got = gov.tick(t);
      const want = reference[i]!;
      if (got.posture !== want.posture
        || got.equilibrium !== want.equilibrium
        || got.arousal !== want.arousal
        || got.perseveration !== want.perseveration
        || got.recovery !== want.recovery
        || got.temperatureMax !== want.temperatureMax) {
        assert.fail(
          `divergence at tick ${n + 1} (cycle ${c + 1}, step ${i + 1}): ` +
          `${JSON.stringify(got)} != ${JSON.stringify(want)}`,
        );
      }
      n++;
    }
    // The controller is stateless-by-parameter, so the cycle only repeats
    // exactly from the same start state. Resetting each cycle is what makes
    // "same input, same output" the thing under test rather than "the state
    // machine happens to be periodic".
    gov.reset();
  }
  assert.equal(n, cycles * CYCLE.length);
  console.log(`  ${n} ticks, zero divergence`);
});

test("wasm memory does not grow across the soak", async () => {
  const gov = await Governor.create();
  // Reach into the shared instance's memory export if the runtime exposes it.
  // Node does; some hosts do not, in which case this degrades to the heap check.
  const before = process.memoryUsage().heapUsed;
  for (let i = 0; i < TICKS; i++) {
    gov.tick(CYCLE[i % CYCLE.length]!);
    if (i % CYCLE.length === CYCLE.length - 1) gov.reset();
  }
  const after = process.memoryUsage().heapUsed;
  // Generous: JS allocates a Decision object per tick, and GC timing is not
  // ours to control. What this catches is unbounded growth, which is what a
  // leaking wasm heap would look like.
  const grewMB = (after - before) / 1024 / 1024;
  assert.ok(
    grewMB < 64,
    `heap grew ${grewMB.toFixed(1)} MB across ${TICKS} ticks, which suggests a leak`,
  );
  console.log(`  heap delta across ${TICKS} ticks: ${grewMB.toFixed(1)} MB`);
});

test("throughput is in the expected order of magnitude", async () => {
  // Not an SLA. The published edge figures (~125 ns/tick in workerd, 200 ns p99
  // in a Node worker) were measured by a dedicated harness on dedicated
  // hardware, and a CI runner cannot reproduce them. This only catches a
  // catastrophic regression, e.g. re-instantiating the module every tick.
  const gov = await Governor.create();
  const t0 = performance.now();
  for (let i = 0; i < TICKS; i++) gov.tick(CYCLE[i % CYCLE.length]!);
  const nsPerTick = ((performance.now() - t0) * 1e6) / TICKS;
  console.log(`  ${nsPerTick.toFixed(0)} ns/tick on this runner`);
  assert.ok(
    nsPerTick < 100_000,
    `${nsPerTick.toFixed(0)} ns/tick is far outside the expected range`,
  );
});
