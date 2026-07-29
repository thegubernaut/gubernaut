import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  target: "node18",
  platform: "node",
  // Type-only peer: must never appear as a runtime require/import in dist
  // (grep-gated in the packaging run).
  external: ["@elizaos/core"],
  sourcemap: false,
  clean: true,
  minify: false,
});
