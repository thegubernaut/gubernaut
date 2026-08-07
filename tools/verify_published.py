# Post-publish verification for every Gubernaut package.
#
# This does NOT trust the working tree, the built dist/, or a registry web page. For each
# package it asks the real registry what exists, installs from that registry into a
# throwaway environment, and then RUNS the installed artifact. Anything that errors here
# errors for a reader.
#
#   python tools/verify_published.py            # everything
#   python tools/verify_published.py --only py  # one ecosystem: py | rust | npm
#
# Must print: ALL PUBLISHED PACKAGES VERIFIED
#
# History worth keeping. The 1.0.0 release passed `twine check` and rendered correctly on
# its PyPI page, and its quickstart still crashed three different ways, because neither of
# those things executes anything. The 1.0.1 verifier fixed that for Python by extracting the
# quickstart from the served sdist and running it. This version extends the same principle
# to the crates and the npm packages: a package that installs but does not govern has not
# been verified.
#
# Registry propagation lags. A new version appears in a registry's JSON API up to a few
# minutes before installers can resolve it. Every install step here retries rather than
# failing, and NOTHING here ever re-publishes.
import argparse
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
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PY_PKG, PY_VER = "gubernaut-sdk", "1.0.1"
CRATE, CRATE_VER = "gubernaut-core", "1.0.1"
SHIM, SHIM_VER = "gcc-core", "1.0.1"
CORE_JS, CORE_JS_VER = "@gubernaut/core", "1.0.1"
PLUGIN, PLUGIN_VER = "@gubernaut/plugin-gcc", "1.0.1"

# The controller binary, unchanged since 0.1.1 and across the 1.0.1 rename.
WASM_SHA256 = "834015d73e6576d6c597b5a32a62c24ac56a50c7023261bf84b96beb01ded7d8"

MOCK_PORT = 9931
fail = 0
_tmpdirs: list[str] = []


def step(msg):
    print(f"\n=== {msg} ===")


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global fail
    fail += 1
    print(f"  FAIL {msg}")


def skip(msg):
    print(f"  --   {msg}")


def tmp(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    _tmpdirs.append(d)
    return d


def run(cmd, cwd=None, timeout=600, env=None):
    e = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=e, shell=False)


def fetch_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def retry_install(label, fn, attempts=6, delay=25):
    """Run an install, retrying on failure.

    A version is visible in a registry's JSON API before its installer index catches up, so
    a verifier run immediately after upload fails on "no matching distribution" even though
    the upload succeeded. That is a propagation delay, not a defect, and the correct
    response is to wait. Re-publishing would be the wrong response and is never done here.
    """
    for i in range(1, attempts + 1):
        r = fn()
        if r.returncode == 0:
            return r
        if i < attempts:
            print(f"       {label}: attempt {i} failed, waiting {delay}s for the index")
            time.sleep(delay)
    return r


class MockUpstream(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        b = json.dumps({
            "id": "x", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


# ---------------------------------------------------------------- Python

def verify_python():
    step(f"PyPI: {PY_PKG} {PY_VER}")
    try:
        meta = fetch_json(f"https://pypi.org/pypi/{PY_PKG}/json")
    except Exception as e:
        bad(f"could not reach PyPI: {e}")
        return
    releases = meta.get("releases", {})
    if releases.get(PY_VER):
        ok(f"{PY_VER} is present, {len(releases[PY_VER])} file(s)")
    else:
        bad(f"{PY_PKG} {PY_VER} is NOT on PyPI")
        return
    if releases.get("1.0.0"):
        ok("1.0.0 is still present and was not yanked")
    else:
        bad("1.0.0 is missing or yanked. Published versions are immutable by policy.")

    urls = meta["info"].get("project_urls") or {}
    for field in ("Repository", "Homepage"):
        ok(f"{field}: {urls[field]}") if urls.get(field) else bad(f"no {field} on the page")

    d = tmp("gsdk_")
    venv = os.path.join(d, "v")
    subprocess.run([sys.executable, "-m", "venv", venv], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        py = os.path.join(venv, "bin", "python")
    r = retry_install("pip", lambda: run(
        [py, "-m", "pip", "install", "--quiet", f"{PY_PKG}=={PY_VER}", "openai"]))
    if r.returncode:
        bad(f"pip install failed: {r.stderr[-400:]}")
        return
    got = run([py, "-c", "import gcc_proxy;print(gcc_proxy.__version__)"]).stdout.strip()
    ok(f"installed, reports {got}") if got == PY_VER else bad(
        f"installed package reports {got!r}, expected {PY_VER!r}")

    # Both console scripts must exist. `gubernaut-proxy` is what the docs now lead with and
    # `gcc-proxy` is what every 1.0.x reader already has in a script somewhere.
    bindir = os.path.dirname(py)
    for name in ("gubernaut-proxy", "gcc-proxy"):
        hit = any(os.path.exists(os.path.join(bindir, name + ext))
                  for ext in ("", ".exe", ".cmd"))
        ok(f"console script {name} installed") if hit else bad(f"missing console script {name}")

    step("PyPI: run the quickstart out of the sdist PyPI actually serves")
    sd = next((f for f in releases[PY_VER] if f["packagetype"] == "sdist"), None)
    if not sd:
        bad("no sdist published for this version")
        return
    blob = urllib.request.urlopen(sd["url"], timeout=60).read()
    sp = os.path.join(d, "s.tar.gz")
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

    srv = HTTPServer(("127.0.0.1", MOCK_PORT), MockUpstream)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        blocks = re.findall(r"```python\n(.*?)```", readme, re.S)
        qs = next((b for b in blocks if "launch_proxy" in b), None)
        if not qs:
            bad("no python quickstart containing launch_proxy in the served README")
        else:
            src = qs.replace('upstream="https://api.openai.com"',
                             f'upstream="http://127.0.0.1:{MOCK_PORT}"')
            runner = os.path.join(d, "qs.py")
            open(runner, "w", encoding="utf-8").write(
                'import os\nos.environ["OPENAI_API_KEY"]="sk-mock"\n' + src)
            r = run([py, runner], timeout=180)
            if r.returncode:
                bad("the published quickstart RAISED:\n" + r.stderr[-700:])
            else:
                out = r.stdout.strip()
                last = out.splitlines()[-1].strip() if out else ""
                if last in {"DEFAULT", "INHIBIT", "REGROUND"}:
                    ok(f"the published quickstart ran and printed a real posture: {last}")
                else:
                    bad(f"expected a posture on the last line, got {out!r}")
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- Rust

def verify_rust():
    if not shutil.which("cargo"):
        skip("cargo not on PATH, skipping the crate checks")
        return

    for name, ver in ((CRATE, CRATE_VER), (SHIM, SHIM_VER)):
        step(f"crates.io: {name} {ver}")
        try:
            meta = fetch_json(f"https://crates.io/api/v1/crates/{name}")
        except Exception as e:
            bad(f"could not reach crates.io for {name}: {e}")
            continue
        versions = {v["num"]: v for v in meta.get("versions", [])}
        if ver in versions:
            ok(f"{ver} is present")
        else:
            bad(f"{name} {ver} is NOT on crates.io (saw {sorted(versions)})")
            continue
        if versions[ver].get("yanked"):
            bad(f"{name} {ver} is yanked")
        c = meta.get("crate", {})
        for field in ("repository", "homepage"):
            ok(f"{field}: {c[field]}") if c.get(field) else bad(f"no {field} on the page")
        if name == SHIM:
            desc = (c.get("description") or "").lower()
            if "deprecat" in desc or "renamed" in desc:
                ok("the shim's description says it is deprecated")
            else:
                bad("the shim does not announce the rename in its description")
            if versions.get("1.0.0", {}).get("yanked"):
                bad("gcc-core 1.0.0 is yanked; policy is that it stays installable")
            elif "1.0.0" in versions:
                ok("gcc-core 1.0.0 is still present and not yanked")

    step("crates.io: a scratch crate compiles against both names")
    d = tmp("gcrate_")
    proj = os.path.join(d, "probe")
    r = run(["cargo", "new", "--bin", "--quiet", proj])
    if r.returncode:
        bad(f"cargo new failed: {r.stderr[-300:]}")
        return
    # Depend on BOTH: the new crate, and the old name through the shim. If the shim did not
    # actually forward, this is where it shows, because the code below uses the old path.
    with open(os.path.join(proj, "Cargo.toml"), "a", encoding="utf-8") as f:
        f.write(f'gubernaut-core = "{CRATE_VER}"\ngcc-core = "{SHIM_VER}"\n')
    open(os.path.join(proj, "src", "main.rs"), "w", encoding="utf-8").write(
        "// The old path must still resolve AND still decide.\n"
        "use gcc_core::{Config, ControllerState, HomeostaticLoop, Posture, Telemetry};\n"
        "fn main() {\n"
        "    let l = HomeostaticLoop::new(Config::default());\n"
        "    let t = Telemetry::new(0.1, 0.5, 0.0).expect('x');\n"
        "    let d = l.update(ControllerState::default(), t);\n"
        "    assert_eq!(d.posture, Posture::Default);\n"
        "    assert!(Telemetry::new(f64::NAN, 0.0, 0.0).is_err());\n"
        "    println!('SHIM_FORWARDS_OK');\n"
        "}\n".replace("'x'", '"telemetry in range"').replace("'SHIM_FORWARDS_OK'",
                                                             '"SHIM_FORWARDS_OK"'))
    r = retry_install("cargo", lambda: run(["cargo", "run", "--quiet"], cwd=proj))
    if r.returncode:
        bad(f"scratch crate failed to build/run:\n{r.stderr[-700:]}")
    elif "SHIM_FORWARDS_OK" in r.stdout:
        ok("both crates resolve from crates.io; the old path still decides correctly")
    else:
        bad(f"scratch crate ran but printed {r.stdout.strip()!r}")


# ---------------------------------------------------------------- npm

def npm_meta(name):
    return fetch_json("https://registry.npmjs.org/" + name.replace("/", "%2F"))


def verify_npm():
    if not shutil.which("npm") and not shutil.which("npm.cmd"):
        skip("npm not on PATH, skipping the npm checks")
        return
    npm = "npm.cmd" if os.name == "nt" and shutil.which("npm.cmd") else "npm"

    for name, ver in ((CORE_JS, CORE_JS_VER), (PLUGIN, PLUGIN_VER)):
        step(f"npm: {name} {ver}")
        try:
            meta = npm_meta(name)
        except Exception as e:
            bad(f"could not reach the npm registry for {name}: {e}")
            continue
        versions = meta.get("versions", {})
        if ver in versions:
            ok(f"{ver} is present")
        else:
            bad(f"{name} {ver} is NOT on npm (saw {sorted(versions)})")
            continue
        v = versions[ver]
        ok(f"license: {v.get('license')}") if v.get("license") == "Apache-2.0" else bad(
            f"license is {v.get('license')!r}, expected Apache-2.0")
        rep = (v.get("repository") or {}).get("url")
        ok(f"repository: {rep}") if rep else bad("no repository field")
        ok(f"homepage: {v['homepage']}") if v.get("homepage") else bad("no homepage field")

    step("npm: install both packages from the registry and run them")
    d = tmp("gnpm_")
    open(os.path.join(d, "package.json"), "w", encoding="utf-8").write(
        json.dumps({"name": "probe", "private": True, "version": "1.0.0", "type": "module"}))
    r = retry_install("npm", lambda: run(
        [npm, "install", "--silent", "--no-audit", "--no-fund",
         f"{CORE_JS}@{CORE_JS_VER}", f"{PLUGIN}@{PLUGIN_VER}"], cwd=d, timeout=900))
    if r.returncode:
        bad(f"npm install failed: {r.stderr[-500:]}")
        return
    ok("both packages installed from the registry")

    # The real test: drive a saturating loop through the INSTALLED core and require the
    # escalation. A load check would pass on a package whose wasm never instantiates.
    probe = os.path.join(d, "probe.mjs")
    open(probe, "w", encoding="utf-8").write(f"""
import {{ Governor, wasmDigest }} from "{CORE_JS}";
import {{ gccPlugin, gubernautPlugin, callGcc, callGubernaut }} from "{PLUGIN}";

if (wasmDigest !== "{WASM_SHA256}") {{
  console.error("EMBEDDED CONTROLLER IS NOT THE VERIFIED BINARY: " + wasmDigest);
  process.exit(1);
}}
const gov = await Governor.create();
const seq = [[0.9,-0.9,0.9],[0.9,-0.9,0.95],[0.9,-0.9,0.98],[0.9,-0.9,0.99]];
const postures = seq.map(([i,v,r]) => gov.tick({{intensity:i, valence:v, repetition:r}}).posture);
if (postures[postures.length-1] !== "REGROUND") {{
  console.error("installed core did not escalate: " + postures.join(" -> "));
  process.exit(1);
}}
// The numeric boundary must survive publication too.
let refused = false;
try {{ gov.tick({{intensity: NaN, valence: 0, repetition: 0}}); }} catch {{ refused = true; }}
if (!refused) {{ console.error("installed core accepted NaN"); process.exit(1); }}

// The plugin's 1.0.0 names and its 1.0.1 aliases must both be present and identical.
for (const [k, val] of Object.entries({{gccPlugin, gubernautPlugin, callGcc, callGubernaut}})) {{
  if (!val) {{ console.error("plugin export missing: " + k); process.exit(1); }}
}}
if (gubernautPlugin !== gccPlugin || callGubernaut !== callGcc) {{
  console.error("plugin aliases are not identical to their originals"); process.exit(1);
}}
console.log("NPM_VERIFIED " + postures.join(" -> "));
""")
    r = run(["node", probe], cwd=d, timeout=300)
    if r.returncode:
        bad("the installed npm packages failed:\n" + (r.stderr or r.stdout)[-700:])
    elif "NPM_VERIFIED" in r.stdout:
        ok(f"installed core governs and the plugin surface is intact: "
           f"{r.stdout.strip().split('NPM_VERIFIED ')[-1]}")
    else:
        bad(f"probe ran but printed {r.stdout.strip()!r}")

    step("npm: replay the golden corpus through the INSTALLED wasm")
    corpus = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "packages", "rust", "tests", "golden", "traces.jsonl")
    if not os.path.exists(corpus):
        skip("golden corpus not found next to this checkout; skipping the parity replay")
        return
    # The corpus comes from the repository, the wasm from the registry. That is the point:
    # it proves the PUBLISHED binary reproduces the Python reference, not the local build.
    replay = os.path.join(d, "replay.mjs")
    open(replay, "w", encoding="utf-8").write(f"""
import {{ readFileSync }} from "node:fs";
import {{ Governor }} from "{CORE_JS}";
const lines = readFileSync({json.dumps(corpus)}, "utf8")
  .split("\\n").filter(Boolean).map(JSON.parse);
let steps = 0;
for (const sc of lines.filter(l => l.type === "scenario")) {{
  const gov = await Governor.create();
  for (const [i, st] of sc.steps.entries()) {{
    const [a,b,c] = st.tel;
    const got = gov.tick({{intensity:a, valence:b, repetition:c}});
    const w = st.expect;
    const bad = got.posture !== w.posture || got.equilibrium !== w.equilibrium
      || got.arousal !== w.arousal || got.perseveration !== w.perseveration
      || got.recovery !== w.recovery || got.temperatureMax !== w.temperature_max;
    if (bad) {{
      console.error(`DIVERGENCE ${{sc.name}} step ${{i+1}}: ` +
        JSON.stringify(got) + " != " + JSON.stringify(w));
      process.exit(1);
    }}
    steps++;
  }}
}}
console.log("PARITY_OK " + steps);
""")
    r = run(["node", replay], cwd=d, timeout=300)
    if r.returncode:
        bad("published wasm diverged from the Python reference:\n" +
            (r.stderr or r.stdout)[-700:])
    elif "PARITY_OK" in r.stdout:
        n = r.stdout.strip().split()[-1]
        ok(f"{n} value-exact steps replayed through the published wasm")
    else:
        bad(f"replay printed {r.stdout.strip()!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=["py", "rust", "npm"],
                    help="verify one ecosystem instead of all of them")
    args = ap.parse_args()

    print("Verifying against the real registries. Nothing here trusts the working tree.")
    try:
        if args.only in (None, "py"):
            verify_python()
        if args.only in (None, "rust"):
            verify_rust()
        if args.only in (None, "npm"):
            verify_npm()
    finally:
        for d in _tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    print()
    if fail:
        print(f"---- {fail} FAILED. The published set is not verified. ----")
        return 1
    print("ALL PUBLISHED PACKAGES VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
