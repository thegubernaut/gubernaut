/**
 * Minimal ambient declaration of the `@elizaos/core` surface this plugin uses,
 * for OFFLINE typechecking only. At integration time the real `@elizaos/core`
 * (declared as a peerDependency) provides the full types and supersedes this.
 *
 * The shapes below match the interface verified live 2026-07-21
 * (docs.elizaos.ai/plugins/reference + elizaOS/eliza@develop
 * packages/docs/runtime/models.mdx).
 */
declare module "@elizaos/core" {
  export interface IAgentRuntime {
    getSetting(key: string): string | undefined;
    // (the real runtime has many more members; only getSetting is used here)
  }

  export type ModelHandler = (
    runtime: IAgentRuntime,
    params: { prompt?: string; [key: string]: unknown },
  ) => Promise<unknown>;

  export interface Plugin {
    name: string;
    description: string;
    init?: (config: Record<string, string>, runtime: IAgentRuntime) => Promise<void>;
    config?: { [key: string]: unknown };
    actions?: unknown[];
    providers?: unknown[];
    evaluators?: unknown[];
    services?: unknown[];
    models?: { [modelType: string]: (...args: any[]) => Promise<any> };
    dependencies?: string[];
  }

  export enum ModelType {
    TEXT_SMALL = "text:small",
    TEXT_MEDIUM = "text:medium",
    TEXT_LARGE = "text:large",
    TEXT_EMBEDDING = "text:embedding",
  }
}
