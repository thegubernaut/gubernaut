# Gubernaut docs

Start with the [README](../README.md): see the stop, then add one line to your code.

**Use it**
- [Configuration](configuration.md): flags, environment variables, routes, headers, errors.
- [Integrations](../examples/README.md): OpenAI SDK, LangChain, LlamaIndex, AutoGen, ElizaOS, each in one line.
- Keel, in-process: [JavaScript and TypeScript](../packages/core-js/README.md) · [Rust](../packages/rust/README.md).
- [The Python package](../packages/python/README.md): the proxy as a CLI and from Python.

**Understand it**
- [Architecture](ARCHITECTURE.md): the sensor, the three numbers, the controller, the boundary between them.
- [Postures](POSTURES.md): `DEFAULT`, `INHIBIT`, `REGROUND`, the hard stop and the recovery window.
- [Determinism](DETERMINISM.md): same input, same decision, in Python, Rust and wasm.
- [Limits](LIMITS.md): what it does not do. Read before you deploy.
- [FAQ](FAQ.md): system prompts, spend caps, latency, chains.

**Check it**
- [Reproduce the record](REPRODUCE.md): three levels run on your machine without an API key.
- [The receipts](../receipts/): every published number, as script output.
- [Gubernaut_Validation](https://github.com/thegubernaut/Gubernaut_Validation): the paper's data.

**For maintainers**
- [Install command policy](INSTALL_COMMAND_POLICY.md): why install commands in prose are unpinned.
