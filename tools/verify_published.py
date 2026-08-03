# Post-upload verification for gubernaut-sdk 1.0.1.
#
# This does NOT trust the working tree, the built dist/, or the PyPI web page. It installs
# from the real index into a throwaway virtual environment, pulls the README out of the
# sdist PyPI actually served, extracts the Python quickstart from it, and runs that
# quickstart against a local mock upstream. Anything that errors here errors for a reader.
#
#   python verify_pypi_101.py
#
# Must print: PUBLISHED 1.0.1 VERIFIED END TO END
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PKG, VER, MOCK_PORT, PROXY_PORT = "gubernaut-sdk", "1.0.1", 9931, 8031
fail = 0


def step(msg):
    print(f"\n=== {msg} ===")


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global fail
    fail += 1
    print(f"  FAIL {msg}")


step(f"1. is {VER} actually on PyPI?")
try:
    meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{PKG}/json", timeout=30))
except Exception as e:
    print(f"  FAIL could not reach PyPI: {e}")
    sys.exit(1)
releases = meta.get("releases", {})
if VER in releases and releases[VER]:
    ok(f"{PKG} {VER} is present, {len(releases[VER])} file(s)")
else:
    bad(f"{PKG} {VER} is NOT on PyPI yet. Upload it first; nothing below can pass.")
    sys.exit(1)
if "1.0.0" in releases and releases["1.0.0"]:
    ok("1.0.0 is still present and was not yanked")
else:
    bad("1.0.0 is missing or yanked. Published versions are immutable by policy.")

step("2. install from the real index into a throwaway venv")
tmp = tempfile.mkdtemp(prefix="gsdk101_")
venv = os.path.join(tmp, "v")
subprocess.run([sys.executable, "-m", "venv", venv], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
py = os.path.join(venv, "Scripts", "python.exe")
if not os.path.exists(py):
    py = os.path.join(venv, "bin", "python")
r = subprocess.run([py, "-m", "pip", "install", "--quiet", f"{PKG}=={VER}", "openai"],
                   capture_output=True, text=True)
if r.returncode:
    bad(f"pip install failed: {r.stderr[-400:]}")
    sys.exit(1)
got = subprocess.run([py, "-c", "import gcc_proxy;print(gcc_proxy.__version__)"],
                     capture_output=True, text=True).stdout.strip()
ok(f"installed, and the package reports {got}") if got == VER else bad(
    f"installed package reports {got!r}, expected {VER!r}")

step("3. pull the README out of the sdist PyPI serves, and read its quickstart")
sd = next((f for f in releases[VER] if f["packagetype"] == "sdist"), None)
if not sd:
    bad("no sdist published for this version")
    sys.exit(1)
blob = urllib.request.urlopen(sd["url"], timeout=60).read()
sp = os.path.join(tmp, "s.tar.gz")
open(sp, "wb").write(blob)
with tarfile.open(sp) as t:
    name = [m for m in t.getnames() if m.endswith("/README.md")][0]
    readme = t.extractfile(name).read().decode("utf-8")
ok(f"README read from the served sdist ({name})")

for label, pattern, want in [
    ("no bare module-level base_url without a trailing slash",
     r'openai\.base_url\s*=\s*"[^"]*?/v1"', False),
    ("no resp.headers on a parsed response", r'resp\.headers\.get', False),
    ("uses the client-object adoption form", r'OpenAI\(base_url=', True),
    ("uses with_raw_response to read the posture", r'with_raw_response', True),
]:
    hit = bool(re.search(pattern, readme))
    ok(label) if hit == want else bad(f"{label} (pattern {'present' if hit else 'absent'})")

step("4. run that quickstart against a mock upstream")


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        b = json.dumps({"id": "x", "object": "chat.completion", "created": 0,
                        "model": "m", "choices": [{"index": 0, "message":
                        {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 5, "completion_tokens": 1,
                                  "total_tokens": 6}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", MOCK_PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

blocks = re.findall(r"```python\n(.*?)```", readme, re.S)
qs = next((b for b in blocks if "launch_proxy" in b), None)
if not qs:
    bad("no python quickstart containing launch_proxy found in the served README")
else:
    src = qs.replace('upstream="https://api.openai.com"', f'upstream="http://127.0.0.1:{MOCK_PORT}"')
    runner = os.path.join(tmp, "qs.py")
    open(runner, "w", encoding="utf-8").write(
        'import os\nos.environ["OPENAI_API_KEY"]="sk-mock"\n' + src)
    r = subprocess.run([py, runner], capture_output=True, text=True, timeout=180)
    if r.returncode:
        bad("the published quickstart RAISED:\n" + r.stderr[-700:])
    else:
        out = r.stdout.strip()
        ok(f"the published quickstart ran and printed: {out!r}")
        if out.splitlines()[-1].strip() in {"DEFAULT", "INHIBIT", "REGROUND"}:
            ok("its last line is a real posture, so the header path works")
        else:
            bad(f"expected a posture on the last line, got {out!r}")

srv.shutdown()
shutil.rmtree(tmp, ignore_errors=True)

print()
if fail:
    print(f"---- {fail} FAILED. 1.0.1 is not done. ----")
    sys.exit(1)
print("PUBLISHED 1.0.1 VERIFIED END TO END")
