"""Leg-2 sidecar: the GCC proxy (from the installed 0.1.0 wheel) in front of a
deterministic in-proc mock upstream, on a fixed port. Started as a child of the
Node harness; prints PROXY_READY then stays up until killed.

Uses the destructive_qa Leg-1 venv (the installed wheel) — no source imports.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(r"<local>/harness")))
from mock_upstream import make_ok_transport  # noqa: E402

import gcc_proxy  # noqa: E402
assert "site-packages" in gcc_proxy.__file__, f"SOURCE SHADOW: {gcc_proxy.__file__}"
from gubernaut_sdk import GccProxy  # noqa: E402

PORT = 18085


def main() -> int:
    proxy = GccProxy(host="127.0.0.1", port=PORT,
                     transport=make_ok_transport(), hard_stop=True).start()
    print(f"PROXY_READY {proxy.base_url} wheel={gcc_proxy.__file__}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        proxy.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
