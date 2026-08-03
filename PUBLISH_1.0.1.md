# 1.0.1 — published and verified

**Status: DONE.** `gubernaut-sdk 1.0.1` is live on PyPI as of 2026-08-03 and was verified
end to end from the real index. This file is the record of how, kept because the next
release should be verified the same way.

<https://pypi.org/project/gubernaut-sdk/1.0.1/>

## What shipped

Documentation only. No behaviour changed and no controller constant moved. Three defects,
each of which made the published quickstart fail on paste, and each of which failed either
silently or with an error that did not name its cause. See `CHANGELOG.md` for the detail.

## The gate that mattered

Every earlier check passed against the **working tree**. The check that actually settles it
runs against the **artifact a stranger downloads**:

1. Install `gubernaut-sdk==1.0.1` from the real index into a throwaway virtual environment.
2. Download the sdist **PyPI serves** and read the README out of it.
3. Extract the Python quickstart from that README.
4. Run it against a local mock upstream.

It printed `DEFAULT`. Passing `twine check`, or the PyPI project page rendering, is not the
same thing and never was: the 1.0.0 release passed both and its quickstart still crashed.

The verifier is `verify_pypi_101.py` and it also asserts the shape of the served README
directly: no bare module-level `base_url` without a trailing slash, no `resp.headers` on a
parsed response, the client-object adoption form present, `with_raw_response` present.

## Release checklist, for next time

- [ ] Bump `pyproject.toml` **and** `gcc_proxy.__version__`. They are separate strings.
- [ ] `CHANGELOG.md` entry, defects described rather than merely fixed.
- [ ] `pytest packages/python/tests` and `tools/claims_check.py`.
- [ ] `python -m build`, then `twine check dist/*`.
- [ ] Tag, push the tag, cut a GitHub Release with both artifacts attached.
- [ ] Upload with the token read in place from the master key home. Never paste it, never
      put it on a command line, never write it to disk.
- [ ] **Wait for the simple index.** The JSON API reports a new version a minute or so
      before `pip` can resolve it, so a verifier run immediately after upload fails on
      "No matching distribution found" even though the upload succeeded.
- [ ] Run the end-to-end verifier against the published artifact.
- [ ] Do not yank the previous version. Published versions are immutable by policy.
- [ ] Update the site register: the package's own `version` and `install`, and
      `packages.version` if this is now the newest. `numbers_audit` fails the build if one
      moves without the others.

## The site

`gubernaut.com` points at 1.0.1 and was redeployed and verified: the hero install command
reads `pip install gubernaut-sdk==1.0.1`, `/releases` carries a `1.0.1` entry above the
`1.0.0` one, and npm and crates.io still read 1.0.0 because they are versioned
independently and were unaffected.
