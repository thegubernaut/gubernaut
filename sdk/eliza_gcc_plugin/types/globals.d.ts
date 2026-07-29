/**
 * Minimal ambient `process` declaration for offline typechecking without
 * installing @types/node. `fetch` / `Response` / `Headers` come from the
 * bundled DOM lib (see tsconfig `lib`). At runtime, Node (>=18) and
 * @types/node provide the real definitions.
 */
declare const process: {
  env: Record<string, string | undefined>;
};
