#!/usr/bin/env python3
"""claims_check - the numbers and claims gate for this repository.

Every published figure in this project is a script output, and the rules that keep
them honest (never round up, never say "all", a number travels with its qualifier)
were enforced only by attention until now. Attention published $0.1670.

This checks the repository against .github/claims.json on every push and pull
request. It has no dependencies beyond the standard library.

    python tools/claims_check.py              # check the repository
    python tools/claims_check.py --list       # print the rules, check nothing
    python tools/claims_check.py --self-test  # prove the gate actually fires

Exit code 0 clean, 1 on any violation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / ".github" / "claims.json"

RED, YEL, GRN, DIM, OFF = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[0m"
if not sys.stdout.isatty():
    RED = YEL = GRN = DIM = OFF = ""


class Finding:
    def __init__(self, path: Path, line: int, rule: str, found: str, why: str):
        self.path, self.line, self.rule, self.found, self.why = path, line, rule, found, why

    def render(self) -> str:
        rel = self.path.relative_to(ROOT).as_posix()
        return (f"{RED}{rel}:{self.line}{OFF}  [{self.rule}]  {YEL}{self.found!r}{OFF}\n"
                f"    {DIM}{self.why}{OFF}")


def load_rules() -> dict:
    if not RULES.exists():
        sys.exit(f"claims register not found: {RULES}")
    return json.loads(RULES.read_text(encoding="utf-8"))


def matches(rel: str, pat: str) -> bool:
    """Glob match that understands a leading '**/'.

    fnmatch has no notion of '**', so it translates '**/*.md' into a pattern that
    requires a literal slash, and a root-level 'README.md' never matches it. That
    silently excluded EVERY root-level file from this gate: README.md, SECURITY.md,
    CONTRIBUTING.md and CODE_OF_CONDUCT.md. The gate reported "clean, 62 files" and
    the repository's front page, the one file that actually published $0.1670, was
    not among them. Found 2026-08-01, before the first push that would have relied
    on it. `test_root_files_are_scanned` in the self-test is the regression guard.
    """
    if fnmatch(rel, pat):
        return True
    return pat.startswith("**/") and fnmatch(rel, pat[3:])


def in_scope(rel: str, cfg: dict) -> bool:
    scope = cfg["scope"]
    if any(matches(rel, p) for p in scope["exclude_globs"]):
        return False
    return any(matches(rel, p) for p in scope["include_globs"])


def is_curated(rel: str, cfg: dict) -> bool:
    return any(matches(rel, p) for p in cfg["scope"]["curated_docs"])


def collect(cfg: dict) -> list[Path]:
    files = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if in_scope(rel, cfg):
            files.append(p)
    return sorted(files)


_MANIFEST_CACHE: dict[int, dict[str, str]] = {}


def manifest_versions(cfg: dict) -> dict[str, str]:
    """Read each package's version from its own manifest. Cached per config.

    The manifest is the only authority. Prose that disagrees with it is the
    defect, never the other way round.
    """
    key = id(cfg)
    if key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[key]
    out: dict[str, str] = {}
    for pkg, spec in cfg["version_pins"]["packages"].items():
        path = ROOT / spec["manifest"]
        if not path.exists():
            continue  # a package not yet created is not a violation
        m = re.search(spec["version_re"], path.read_text(encoding="utf-8"), re.M)
        if m:
            out[pkg] = m.group(1)
    _MANIFEST_CACHE[key] = out
    return out


def install_pins_in(line: str, pkg: str, pins: dict) -> list[tuple[str, str]]:
    """Version pins for `pkg` that appear in an INSTALL form on this line.

    Returns (version, matched_text) pairs. A bare mention of a version is not an
    install form and is deliberately not matched, so a changelog sentence or a
    "not yanked" note about an older release stays legal.
    """
    hits = []
    for tmpl in pins["install_forms"]:
        pat = tmpl.replace("{name}", re.escape(pkg))
        for m in re.finditer(pat, line):
            hits.append((m.group("ver"), m.group(0)))
    return hits


def check_file(path: Path, text: str, cfg: dict) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix()
    lines = text.splitlines()
    lower_lines = [ln.lower() for ln in lines]
    found: list[Finding] = []

    def context(i: int) -> str:
        """The line plus its neighbours, lowered, with markdown emphasis stripped.

        Negation escapes are checked against this rather than the single line,
        because prose wraps. "a measured property rather than a structural
        guarantee" splits across two lines at 96 columns, and a line-based
        check fails the very sentence the escape exists to permit.

        Backticks and asterisks are stripped because escapes are prose patterns
        and markdown is not prose. CONTRIBUTING.md line 82 reads "The flagship is
        `$0.1669`, not `$0.1670`." and the escape "not $0.1670" missed it on a
        code span. The self-test had asserted the same sentence WITHOUT the
        backticks and passed, which is how the defect survived: a rule tested
        against a tidied version of the text it is supposed to read.
        """
        lo, hi = max(0, i - 2), min(len(lower_lines), i + 1)
        joined = " ".join(lower_lines[lo:hi])
        return joined.replace("`", "").replace("*", "").replace("_", "")

    def escaped(i: int, oks: list[str]) -> bool:
        return any(ok in context(i) for ok in oks)

    # 1. exact banned substrings
    for bad, spec in cfg["banned_strings"].items():
        if bad.startswith("$comment"):
            continue
        why = spec if isinstance(spec, str) else spec["why"]
        only_in = None if isinstance(spec, str) else spec.get("only_in")
        if only_in and not any(matches(rel, p) for p in only_in):
            continue
        oks = [] if isinstance(spec, str) else [o.lower() for o in spec.get("negated_ok", [])]
        for i, ln in enumerate(lines, 1):
            if bad in ln and not escaped(i, oks):
                found.append(Finding(path, i, "banned-string", bad, why))

    # 2. banned vocabulary, word-boundary, with negation escapes
    #    'provenance' must not trip 'proven', and the required disclaimer
    #    'Gubernaut is not injection-proof' must not trip 'injection-proof'.
    for word, spec in cfg["banned_words"].items():
        if word.startswith("$comment"):
            continue
        why = spec["why"]
        oks = [o.lower() for o in spec.get("negated_ok", [])]
        pattern = re.compile(r"(?<![\w-])" + re.escape(word.lower()) + r"(?![\w-])")
        for i, ln in enumerate(lower_lines, 1):
            if not pattern.search(ln):
                continue
            if escaped(i, oks):
                continue
            found.append(Finding(path, i, "banned-word", word, why))

    # 3. fabricated social proof
    sp = cfg["social_proof_patterns"]
    sp_oks = [o.lower() for o in sp.get("negated_ok", [])]
    for pat in sp["patterns"]:
        rx = re.compile(pat, re.IGNORECASE)
        for i, ln in enumerate(lines, 1):
            m = rx.search(ln)
            if m and not escaped(i, sp_oks):
                found.append(Finding(path, i, "social-proof", m.group(0), sp["why"]))

    # 4. required pairings, whole-file
    for rule in cfg["required_together"]:
        triggers = [t for t in rule["if_any"] if t in text]
        if not triggers:
            continue
        missing = [t for t in rule.get("then_all", []) if t not in text]
        any_req = rule.get("then_any", [])
        if any_req and not any(t in text for t in any_req):
            missing.append(" or ".join(any_req))
        if missing:
            line = next((i for i, ln in enumerate(lines, 1)
                         if any(t in ln for t in triggers)), 1)
            found.append(Finding(path, line, "required-together",
                                 f"{triggers[0]} without {', '.join(missing)}",
                                 rule["why"]))

    # 5. version pins. An install command that names a version is a promise a
    #    reader executes verbatim, so it is a claim like any other, and it went
    #    stale the moment 1.0.1 shipped: the README front page still said
    #    `pip install gubernaut-sdk==1.0.0` while PyPI, the site and the
    #    changelog all read 1.0.1. Every other gate was green. Found 2026-08-07.
    #
    #    Only INSTALL forms are checked, never bare mentions. "gcc-core 1.0.0
    #    stays published and is not yanked" is a true sentence about an old
    #    version and must stay sayable; `cargo add gcc-core@1.0.0` is a stale
    #    instruction and must not.
    pins = cfg.get("version_pins")
    if pins:
        declared = manifest_versions(cfg)
        for i, ln in enumerate(lines, 1):
            for pkg, want in declared.items():
                for got, form in install_pins_in(ln, pkg, pins):
                    if got != want:
                        found.append(Finding(
                            path, i, "version-pin", f"{form} (manifest says {want})",
                            f"{pkg} is at {want}. An install command pinning {got} tells a "
                            f"reader to install a version we no longer ship. Bump it here, "
                            f"or bump the manifest, but never leave them disagreeing."))

    # 6. dash ban, curated documentation surface only
    if is_curated(rel, cfg):
        for ch in cfg["dash_ban"]["chars"]:
            for i, ln in enumerate(lines, 1):
                if ch in ln:
                    found.append(Finding(path, i, "dash-ban", ch,
                                         "Em-dash and en-dash are banned. Use a period, "
                                         "comma, colon or middot. Ranges read '4.1% to 20.2%'."))
    return found


def run(cfg: dict) -> list[Finding]:
    findings: list[Finding] = []
    for path in collect(cfg):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings.extend(check_file(path, text, cfg))
    return findings


def self_test(cfg: dict) -> int:
    """Prove the gate fires. A green gate that cannot fail is not a gate."""

    def _v(pkg: str) -> str:
        """The live manifest version, so these cases never need editing on a bump."""
        got = manifest_versions(cfg).get(pkg)
        if got is None:
            raise SystemExit(
                f"self-test cannot run: no manifest version for {pkg}. "
                "Check version_pins.packages in .github/claims.json.")
        return got

    def _bump(ver: str) -> str:
        """A version this package definitely is not, for the must-fire cases."""
        parts = ver.split(".")
        return ".".join(parts[:-1] + [str(int(parts[-1]) + 1)])

    cases = [
        ("$0.1670 is the flagship spend.", "banned-string", True),
        ("$0.1669 is the flagship spend.", "banned-string", False),
        ("The result is proven correct.", "banned-word", True),
        ("Sealed provenance is intact.", "banned-word", False),
        ("Gubernaut is not injection-proof.", "banned-word", False),
        ("Gubernaut is injection-proof.", "banned-word", True),
        ("Regulated wins 15/16 cells.", "required-together", True),
        ("15/16 cells, 13/16 at p<.05, null -0.04.", "required-together", False),
        ("Trusted by 4,000 developers.", "social-proof", True),
        ("No customer reviews, testimonials or logos exist.", "social-proof", False),
        ("openai.api_base = 'http://x'", "banned-string", True),
        ("OpenAI(api_base='http://x')", "banned-string", False),
        # CONTRIBUTING.md teaches the rule by naming the wrong value. Stating the
        # correct figure and rejecting the wrong one is this gate's job, not a
        # breach of it. Asserting the wrong value on its own still fails, above.
        # Verbatim from CONTRIBUTING.md:82, backticks included. An earlier version
        # of this case stripped them, passed, and left the real line failing.
        ("- **Never round up.** The flagship is `$0.1669`, not `$0.1670`.",
         "banned-string", False),
        ("The flagship spend is $0.1670.", "banned-string", True),
        # Prose wraps. A negation escape that only looks at one line fails the
        # very sentence it exists to permit. These two cases are the regression
        # test for that, and both were live defects on 2026-08-01.
        ("compliance is a measured property rather than a\nstructural guarantee.",
         "banned-word", False),
        ("The deciding meta level accepts floats only.\nNo consciousness, sentience, or "
         "experience is claimed\nor implied.", "banned-word", False),
        # version-pin, added 2026-08-07 after the front page shipped a stale
        # install command through a fully green gate. These cases are written
        # against the LIVE manifests, so they keep working as versions move.
        (f"pip install gubernaut-sdk=={_bump(_v('gubernaut-sdk'))}", "version-pin", True),
        (f"pip install gubernaut-sdk=={_v('gubernaut-sdk')}", "version-pin", False),
        (f"cargo add gubernaut-core@{_bump(_v('gubernaut-core'))}", "version-pin", True),
        (f"cargo add gubernaut-core@{_v('gubernaut-core')}", "version-pin", False),
        (f"npm install @gubernaut/plugin-gcc@{_bump(_v('@gubernaut/plugin-gcc'))}",
         "version-pin", True),
        # The whole point of matching install FORMS and not bare mentions: this
        # sentence is true, is load-bearing, and must never be gated away.
        ("`gcc-core` 1.0.0 stays published and is not yanked.", "version-pin", False),
        ("Renamed from gcc-core at 1.0.1. gcc-core 1.0.0 is the last real release "
         "under that name.", "version-pin", False),
    ]
    fake = ROOT / "README.md"
    ok = True
    print(f"{DIM}self-test: proving each rule fires and does not over-fire{OFF}\n")
    for text, rule, should_fire in cases:
        hits = [f for f in check_file(fake, text, cfg) if f.rule == rule]
        fired = bool(hits)
        good = fired == should_fire
        ok &= good
        mark = f"{GRN}pass{OFF}" if good else f"{RED}FAIL{OFF}"
        want = "fires" if should_fire else "silent"
        print(f"  {mark}  [{rule:18}] {want:6}  {text[:52]}")

    # Rules firing correctly on a string proves nothing if the file never reaches
    # them. Every case above runs against a fake README.md path while collect()
    # was returning zero root-level files. Assert discovery, not just matching.
    print()
    scanned = {p.relative_to(ROOT).as_posix() for p in collect(cfg)}
    for must in ("README.md", "SECURITY.md", "CONTRIBUTING.md"):
        present = must in scanned
        ok &= present
        mark = f"{GRN}pass{OFF}" if present else f"{RED}FAIL{OFF}"
        print(f"  {mark}  [{'discovery':18}] scanned  {must}")
    excluded = "CHANGELOG.md" not in scanned
    ok &= excluded
    print(f"  {f'{GRN}pass{OFF}' if excluded else f'{RED}FAIL{OFF}'}  "
          f"[{'discovery':18}] skipped  CHANGELOG.md (it must be able to quote the defect)")

    print()
    if ok:
        print(f"{GRN}self-test passed. The gate fires on every defect it claims to catch.{OFF}")
        return 0
    print(f"{RED}self-test FAILED. The gate is not enforcing what it says it enforces.{OFF}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="the numbers and claims gate")
    ap.add_argument("--list", action="store_true", help="print the rules and exit")
    ap.add_argument("--self-test", action="store_true", help="prove the gate fires")
    args = ap.parse_args()
    cfg = load_rules()

    if args.list:
        print(f"banned strings     {len([k for k in cfg['banned_strings'] if not k.startswith('$')])}")
        print(f"banned words       {len([k for k in cfg['banned_words'] if not k.startswith('$')])}")
        print(f"required pairings  {len(cfg['required_together'])}")
        print(f"social-proof rules {len(cfg['social_proof_patterns']['patterns'])}")
        print(f"dash ban scope     {', '.join(cfg['scope']['curated_docs'])}")
        return 0

    if args.self_test:
        return self_test(cfg)

    findings = run(cfg)
    n_files = len(collect(cfg))

    if not findings:
        print(f"{GRN}claims_check: clean{OFF}  ({n_files} files)")
        return 0

    print(f"{RED}claims_check: {len(findings)} violation(s) across {n_files} files{OFF}\n")
    for f in findings:
        print(f.render())
    print(f"\n{DIM}Rules: .github/claims.json. Numbers change in the sealed register "
          f"first, then here, then the prose.{OFF}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
