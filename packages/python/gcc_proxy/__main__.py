"""CLI entry point: `python -m gcc_proxy` or the `gcc-proxy` script.

    gcc-proxy --port 8000 --upstream https://api.openai.com

Then point any OpenAI-compatible client at http://localhost:8000/v1.
"""

from __future__ import annotations

import argparse
import dataclasses

import uvicorn

from gcc_proxy.config import GCCConfig
from gcc_proxy.proxy import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="gcc-proxy",
                                     description="Gubernaut Cognitive Controller — local drop-in proxy")
    parser.add_argument("--host", default=None, help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="bind port (default 8000)")
    parser.add_argument("--upstream", default=None,
                        help="upstream base URL (default https://api.openai.com; env GCC_UPSTREAM_BASE)")
    parser.add_argument("--no-hard-stop", action="store_true",
                        help="disable the runaway hard stop (advisory postures only)")
    parser.add_argument("--allow-ungoverned-routes", action="store_true",
                        help="forward non-chat /v1/* routes (e.g. /v1/responses) "
                             "ungoverned instead of blocking them (opt-in; weakens "
                             "the firewall)")
    args = parser.parse_args()

    cfg = GCCConfig.from_env()
    overrides = {}
    if args.host is not None:
        overrides["host"] = args.host
    if args.port is not None:
        overrides["port"] = args.port
    if args.upstream is not None:
        overrides["upstream_base"] = args.upstream
    if args.no_hard_stop:
        overrides["hard_stop_enabled"] = False
    if args.allow_ungoverned_routes:
        overrides["allow_ungoverned_routes"] = True
    if overrides:
        cfg = dataclasses.replace(cfg, **overrides)

    uvicorn.run(create_app(cfg), host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
