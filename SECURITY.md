# Security policy

## Reporting a vulnerability

Email **security@overtake.app** with the details and, if you can, a proof of
concept. Please do not open a public issue for a security problem, and please do
not test against other people's accounts or data.

We aim to acknowledge within 72 hours and to keep you updated while we work on a
fix. We will credit you when the fix ships, unless you prefer to stay anonymous.

## Scope

In scope: the API (`api.overtake.app`), the web app (`overtake.app`), and this
repository. Out of scope: denial of service, findings that require a
compromised device or physical access, and reports about third parties we
depend on (Stripe, the FPL API, our host) — report those to the party
concerned.

## What is already in place

The controls below are implemented and covered by adversarial tests
(`api/tests/integration/test_security.py`); this section is context for a
reporter, not a claim that the surface is closed.

- **No passwords.** Magic links only; both link and session tokens are stored
  as SHA-256 hashes, so a database dump cannot be used to sign in.
- **Opaque, server-side sessions** that can actually be revoked; `HttpOnly`,
  `SameSite=Lax`, `Secure` in production.
- **CSRF** by double-submit token on every mutating route. Webhooks are exempt
  because they authenticate by signature and carry no cookie.
- **Authorisation in two dimensions** — ownership and entitlement — enforced
  server-side by one shared dependency. Frontend plan state is never a gate.
- **Rate limits on every route**, enforced by a build-time audit so a new route
  cannot ship without one.
- **All third-party free text is treated as hostile** — normalised, stripped of
  control and bidirectional-override characters, truncated, and delimited as
  untrusted data inside LLM prompts. The LLM has no side-effecting tools.
- **Stripe handles all card data.** Webhooks are signature-verified and
  idempotent through a recorded event ledger.
- **Secrets never live in the repository.** They are injected from the host's
  secret store; production refuses to boot on a missing or weak secret.

## Supported versions

Only the currently deployed version is supported. There are no long-term support
branches.
