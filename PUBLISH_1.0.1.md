# Publishing 1.0.1 to PyPI

Everything up to the upload is done and verified. **The upload itself needs your PyPI
token, which exists nowhere in this tree** (no `.pypirc`, no keyring entry, no `.env` key,
no publish workflow). That is the correct posture for a credential and the reason this file
exists instead of a completed step.

## State

| | |
|---|---|
| Version bumped | `pyproject.toml` and `gcc_proxy.__version__` both read **1.0.1** |
| CHANGELOG | `## [1.0.1] - 2026-08-03`, all three defects described |
| Tests | **40 passed** |
| Claims gate | clean, 66 files |
| Artifacts built | `packages/python/dist/gubernaut_sdk-1.0.1{-py3-none-any.whl,.tar.gz}` |
| `twine check` | **PASSED** on both |
| Tag | `v1.0.1` pushed |
| GitHub Release | cut, both artifacts attached |
| **Artifact verified** | the Python quickstart was **extracted from the built sdist and executed** against a local mock upstream. It printed `DEFAULT`. All three defects asserted dead against the artifact, not the working tree |

## The upload

```bash
cd E:/AMT/12_product_repo/gubernaut/packages/python
python -m twine upload dist/gubernaut_sdk-1.0.1*
```

Username `__token__`, password is your PyPI API token. If you would rather not paste it:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-YOUR-TOKEN python -m twine upload dist/gubernaut_sdk-1.0.1*
```

**Do not delete or yank 1.0.0.** Published versions are immutable by this project's own
stated policy, and 1.0.0's defects are in its documentation rather than its behaviour: a
reader who wires the proxy correctly gets the same governed request path from either
release.

## Immediately after

Run the post-upload verifier. It installs from **the real PyPI** into a fresh virtual
environment, extracts the quickstart from the sdist PyPI actually served, and runs it:

```bash
python "C:/Users/dushy/AppData/Local/Temp/claude/e--AMT-08-website-gubernaut-site/82dcfdc6-0dd0-446f-a0b8-0f774be694c4/scratchpad/verify_pypi_101.py"
```

It must print `PUBLISHED 1.0.1 VERIFIED END TO END`. If it does not, the release is not
done, whatever PyPI's web page says.

## Then the site

The site currently pins `pip install gubernaut-sdk==1.0.0` and that command **still works
and still installs a package whose behaviour is correct** — the site's own snippet was
fixed and tested independently of the package version, so nothing on gubernaut.com is
broken while 1.0.1 is pending.

What changes once 1.0.1 is live is smaller than it looks, and it is gated:

1. `astro-site/src/data/facts.json` → `packages.pypi.version` and `packages.pypi.install`
   and `packages.version` all to `1.0.1`. **`numbers_audit` fails the build if you move one
   and not the others**, and it fails if the release train does not equal the highest
   registry version. npm and crates.io stay at 1.0.0 and the copy now reads each package's
   own version rather than asserting the three agree.
2. A `1.0.1` entry on `/releases`.
3. `npm run ship`, then deploy.
