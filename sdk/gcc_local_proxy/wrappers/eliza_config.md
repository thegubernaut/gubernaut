# Drop-in config #4 — ElizaOS (Web3-native agent framework)

Eliza's OpenAI plugin honours a configurable API endpoint, so the GCC proxy
drops in via environment config — no code change to the agent:

```dotenv
# .env of your Eliza project
OPENAI_API_KEY=sk-your-real-key        # forwarded verbatim by the proxy
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
```

**Verified against the current ElizaOS monorepo** (2026-07-18): the OpenAI
plugin documents `OPENAI_BASE_URL` (default `https://api.openai.com/v1`,
"Override for compatible endpoints") in
`plugins/plugin-openai/README.md` on `main` — monorepo `eliza` v2.0.4,
commit `249403b5364d40a8e1db37e2a6b2bbb2e39fee14` (2026-07-13); the project
publishes no GitHub releases, so commit + root version are the pin.
Source: <https://github.com/elizaOS/eliza/tree/main/plugins/plugin-openai>.

Notes from the same verification:

- The repo-root `.env.example` template lists only `OPENAI_API_KEY` — add
  the `OPENAI_BASE_URL` line yourself; the plugin reads it regardless.
- Modality-specific overrides exist if you govern only chat:
  `OPENAI_EMBEDDING_URL`, `OPENAI_IMAGE_DESCRIPTION_BASE_URL`, and browser
  variants — point ONLY the chat traffic at the proxy if embeddings should
  go direct.
- The former standalone `elizaos-plugins/plugin-openai` repo is gone (404);
  the plugin lives in-monorepo now.

Run the proxy first:

```text
gcc-proxy --upstream https://api.openai.com
```

Every agent turn is then governed: telemetry `{intensity, valence,
repetition}` is extracted locally, the deterministic meta-level decides a
posture (DEFAULT / INHIBIT / REGROUND), and saturated recursive loops are
hard-stopped before they spend upstream tokens — the failure mode that
matters most for autonomous on-chain agents holding funds.

> Re-verify the variable name against the then-current ElizaOS main before
> each public citation (law: verify external claims live). Pin above is
> 2026-07-18.
