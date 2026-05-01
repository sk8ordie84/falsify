# Roadmap

Two roadmaps run side by side in this repository:

- **This file** — the `falsify` CLI tool. Features, integrations, dependencies.
- **[`spec/v0.2/ROADMAP.md`](spec/v0.2/ROADMAP.md)** — the PRML specification itself. Format changes, canonicalization grammar, conformance.

The CLI roadmap is downstream of the spec: when spec v0.2 freezes on 2026-05-22, the CLI updates to be v0.2-conformant about three weeks later. This file tracks the CLI side; the spec side is in the linked file.

This roadmap is directional, not a commitment. Items move as the community uses the tool and finds out what actually matters.

---

## Now — shipped (as of 2026-05-01)

Since the v0.1.0 release on 2026-04-21:

- **PRML v0.1 specification** at [spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1) — RFC-style, CC BY 4.0, 18 pages.
- **Conformance test suite** — 12 vectors with locked SHA-256 digests under [`spec/test-vectors/v0.1/`](spec/test-vectors/v0.1/).
- **Second reference implementation** — Node.js, 404 LOC, all 12 vectors pass byte-for-byte. See [`impl/js/`](impl/js/).
- **GitHub Action** [`falsify-verify`](.github/actions/falsify-verify) — composite action that scans `**/*.prml.yaml`, verifies against sidecars, fails on tampered or falsified.
- **EU AI Act mapping document** — Articles 12, 17, 18, 50, 72, 73 with field-level bindings; see [`spec/compliance/AI-Act-mapping-v0.1.md`](spec/compliance/AI-Act-mapping-v0.1.md).
- **arXiv preprint** — 14-page LaTeX working draft, CC BY 4.0; cs.CR submission in flight. See [`spec/paper/`](spec/paper/).
- **Compliance landing copy** — for compliance leads, notified body assessors, AI governance officers; see [`spec/compliance/landing.md`](spec/compliance/landing.md).
- **Positioning matrix** — PRML vs in-toto, SLSA, Model Cards, HELM, ClinicalTrials.gov; see [`spec/analysis/positioning-v0.1.md`](spec/analysis/positioning-v0.1.md).
- **Canonicalization portability findings** — three cross-language gotchas surfaced by the JS implementation, motivating v0.2 grammar work; see [`spec/analysis/canonicalization-portability-v0.1.md`](spec/analysis/canonicalization-portability-v0.1.md).
- **PRML scoring methodology** with twelve worked examples; see [`spec/analysis/scoring-methodology-v0.1.md`](spec/analysis/scoring-methodology-v0.1.md).

Original v0.1.0 highlights (CLI, hooks, CI, MCP scaffold, Claude Code skills) remain in [CHANGELOG.md](CHANGELOG.md).

---

## Next — CLI v0.2.0 (target 2026-06-15)

The spec v0.2 freeze is 2026-05-22; the CLI release follows about three weeks later. CLI v0.2.0 has two work streams: spec-conformance changes (driven by spec evolution) and tool-level features (independent of spec).

### Spec-conformance changes

These are direct consequences of the spec v0.2 changes documented in [`spec/v0.2/ROADMAP.md`](spec/v0.2/ROADMAP.md):

- **Update `_canonicalize`** to match v0.2 grammar — always-quoted string scalars, `threshold` always rendered with at least one decimal place, `seed` as quoted decimal string.
- **`falsify migrate v0.1 v0.2`** — one-command transformation of v0.1 manifests to v0.2, with a `prior_hash` link to preserve audit chain across the version boundary.
- **`hash_alg` field support** — verifier dispatches on the field; SHA-256 default, SHA3-256 and BLAKE3 added.
- **`tolerance` field** — verifier evaluates `|observed − threshold| ≤ tolerance` when present, falling back to bit-exact compare otherwise.
- **`claims:` sequence** — multi-metric manifests with shared dataset and seed; verdict PASSes only when every claim in the sequence passes.
- **`producer.tier: high-risk`** — Ed25519 detached signature verification via the new `*.prml.sig` sidecar; missing or invalid signature emits exit 11 (GUARD).
- **`falsify --version`** prints both tool and spec versions: `falsify 0.2.0 (PRML v0.2)`.

### Tool-level features

Independent of spec evolution; could ship in a CLI v0.1.x point release as well:

- **MCP verdict-log server** — expose `.falsify/*/verdict.json` via Model Context Protocol so any Claude session — Desktop, Code, custom — can query locked verdicts without shelling out. Tool functions implemented in v0.1.0 (`mcp_server/`); v0.2 wires the SDK adapter.
- **Managed Agents integration** — deploy `verdict-refresher` on a cron schedule, posting refresh summaries to a repo Discussion or Issue thread.
- **GitHub PR bot** — `falsify audit` mode that comments on PRs with the `claim-audit` result inline.
- **Remote artifacts** — optional S3 / GCS backend for `.falsify/<name>/runs/` so teams can share verdict history without committing run artifacts to git.

---

## Soon — CLI v0.3.0 (target Q4 2026)

Larger moves, scoped loosely:

- **Spec library** — a curated set of shareable spec templates (`falsify install-template classification-accuracy-v1`) with versioned schemas.
- **Bayesian stopping rules** — first-class support for sequential / adaptive stopping, not just fixed sample. The spec declares the rule; falsify enforces it and rejects mid-run peeking.
- **Diff-aware reruns** — `falsify run <name> --only-if-changed` detects which inputs changed since the last run and skips redundant work.
- **Provenance chaining** — link each verdict to the git SHA, dataset hash, and (when present) PRML manifest hash, so a third party can reproduce the PASS/FAIL.
- **Third reference implementation** — Rust or Go, contributed by community against the v0.2 conformance suite. Open call out as soon as v0.2 freezes.

---

## Later — speculative

Ideas worth exploring if the tool sees adoption:

- **VS Code / JetBrains extension** — inline verdict status in editor gutters.
- **Slack / Discord bot** — post verdict changes to a channel; challenge-mode mini-games.
- **Anti-p-hacking gamification** — personal / team leaderboards for pre-registration discipline.
- **Federated verdict registry** — cross-org claim registry, opt-in and privacy-preserving.
- **AI agent integration** — agents auto-generate specs from a plain-English claim via the `hypothesis-author` skill, commit them, and run `falsify lock` before acting on the claim.

---

## What won't ship (non-goals)

Honest scope boundaries — unchanged from v0.1.0:

- **Not a statistics package.** We don't compute p-values or confidence intervals. The spec declares the threshold; the tool enforces it.
- **Not an experiment orchestrator.** `falsify` runs one command per spec and reads the output. Airflow / Dagster / Prefect do that job better.
- **Not a secrets manager.** Specs must not embed API keys; pass them through environment variables read by `experiment.command`.
- **Not a distributed system.** The verdict store is per-repo and on-disk. Remote backends (CLI v0.2.x) are opt-in sync, not a replacement.
- **Not a compliance product.** PRML is a primitive that makes named regulatory obligations satisfiable. The tool implements the primitive; it does not sell a quality management system, an audit consultancy, or notified-body services. See [`spec/compliance/landing.md`](spec/compliance/landing.md) for the precise position.

---

## How to influence this roadmap

- For **specification** changes (format, canonicalization, fields, threat model): comment in [GitHub Discussion #6](https://github.com/sk8ordie84/falsify/discussions/6) before the v0.2 freeze on 2026-05-22. The five open RFC questions in [`spec/v0.2/ROADMAP.md`](spec/v0.2/ROADMAP.md) are where outside opinion carries the most weight right now.
- For **CLI** changes (UX, integrations, performance): open a GitHub issue with the `roadmap` label describing the use case you need.
- For a **third-language reference implementation** (Rust, Go, Java, Swift, OCaml…): the [12 conformance vectors](spec/test-vectors/v0.1/) are the contract. If your canonicalizer reproduces all twelve byte-for-byte, your implementation is conformant. Open a PR against `impl/<language>/`.
- For private or commercial inquiries, contact the maintainer directly: email in [`.github/SECURITY.md`](.github/SECURITY.md), or `hello@studio-11.co`.

---

## A note on discipline

Every item above is subject to the same contract as v0.1.0:

- Deterministic exit codes
- Canonical hashing
- Standard-library-only runtime where possible (Python: stdlib + pyyaml; JS: stdlib only)
- Feature creep dilutes the trust the tool sells

Small, deterministic, verifiable. That's the product.
