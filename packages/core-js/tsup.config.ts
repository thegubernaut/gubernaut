import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  // `neutral`, not `node`. This package must load unchanged in Deno, Bun,
  // Cloudflare workerd and the browser, so the build must not inject any
  // Node-only shim. The wasm is base64-inlined and decoded with atob for the
  // same reason: no fs, no fetch, no bundler plugin, no loader config.
  target: "es2022",
  platform: "neutral",
  sourcemap: false,
  clean: true,
  minify: false,
});
