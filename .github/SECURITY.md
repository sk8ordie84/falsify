# Security policy

## Supported versions

Currently `0.1.x` is the only supported line. Older pre-releases
are not maintained; please upgrade before reporting.

## Reporting a vulnerability

If you find a way to:

- Make `falsify guard` pass on a contradicting claim.
- Make two semantically different specs produce the same SHA-256
  canonical hash (a collision breaks pre-registration).
- Execute arbitrary code through a crafted `spec.yaml` or
  `experiment.command` beyond what the user explicitly authored.

**Please do not open a public issue.** Email the maintainer directly
at `maintainer@example.com` *(placeholder — replace before the first
public release)*. A fix typically lands within 14 days; we'll
coordinate a disclosure window with you.

## What counts as a vulnerability

Any break of the determinism contract counts:

- **Exit codes** — getting a `0` when the criterion was violated,
  or `10` when it held.
- **Canonical hash** — two distinct specs hashing the same, or the
  same spec hashing differently across machines.
- **Guard semantics** — commit-msg guard passing text that
  affirmatively references a FAIL / INCONCLUSIVE verdict.
- **Leakage** — anything that exposes secrets from `spec.yaml`,
  run output, or the verdict store to unauthorized readers.

Cosmetic bugs, typos, or missing features don't qualify — use a
bug report or feature request instead.

## Credit

Disclosed issues are credited in `CHANGELOG.md` under the release
that fixes them, unless the reporter requests otherwise.

## Full threat model

For the complete enumeration of attacks falsify defends against,
attacks it explicitly does NOT defend against, and the mitigations
for each, see
[`docs/ADVERSARIAL.md`](../docs/ADVERSARIAL.md).
