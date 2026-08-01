# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | yes |
| < 1.0 | no. The 0.x pre-releases had known fail-open defects, fixed in 1.0.0. Upgrade. |

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Use GitHub's [private vulnerability reporting](https://github.com/thegubernaut/gubernaut/security/advisories/new),
or email **contact@gubernaut.com** with `SECURITY` in the subject.

Please include the version, the platform, what you expected, what happened, and a minimal
reproduction if you have one. You will get an acknowledgement within a few days. This is a
small project and the honest answer is that response time depends on the week, so if you
have not heard back in a week, send a reminder.

Report privately, give a reasonable window for a fix, and you will be credited in the
advisory unless you would rather not be.

## What counts as a vulnerability here

Gubernaut is a control layer, so the interesting failures are control failures. All of
these are in scope:

- **A fail-open.** Any path where the proxy is unavailable, misconfigured or erroring and a
  request nevertheless reaches the upstream ungoverned. Deny-by-default and fail-closed are
  the design; a hole in either is a real bug.
- **Crossing the token boundary.** Any way to get non-numeric data into the controller, or
  to influence a posture decision through request text rather than through telemetry. The
  boundary is the central security property of this project.
- **Bypassing the hard stop.** Any way to make a request that should be stopped locally
  reach the upstream instead.
- **Leaking the `Authorization` header**, or any credential appearing in a log, a trace, a
  telemetry field or an error body.
- **Cross-request contamination.** The proxy is stateless by construction. Any way to make
  one request's state affect another's posture is a bug.

## What is a known limit rather than a vulnerability

These are documented in [docs/LIMITS.md](docs/LIMITS.md) and are not accepted as
vulnerability reports. They are all worth discussing in an ordinary issue.

- **The arbiter can be prompt-injected.** It reads raw text by necessity, and it is exactly
  as susceptible as the model behind it. Injection resistance is claimed for the
  **controller** only. Gubernaut is not injection-proof.
- **A model ignoring a posture directive.** Posture compliance is a measured property. The
  temperature clamp and the hard stop do not depend on the model cooperating; the
  directives do.
- **The v0 lexicon sensor missing calmly worded hostility.** A known recall gap, measured
  at 5/5 missed on that corpus. A better sensor is the fix.
- **A different result after changing `GCCConfig`.** The published numbers describe the
  defaults.

## Handling of secrets

The proxy forwards the client's `Authorization` header verbatim and stores nothing. It does
not need a key of its own, and it never writes one. If you find a code path that logs,
persists or transmits a credential anywhere other than to the configured upstream, that is
a vulnerability and belongs in the private channel above.
