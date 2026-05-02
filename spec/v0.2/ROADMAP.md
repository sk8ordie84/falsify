# PRML v0.2 — Roadmap

**Status:** Working draft. RFC open until 2026-05-22 (freeze date).

**Target release:** 2026-06-15.

**Position:** v0.2 closes the three portability findings surfaced by the second-implementation exercise (see [`spec/analysis/canonicalization-portability-v0.1.md`](../analysis/canonicalization-portability-v0.1.md)) and adds the four extension fields foreseen in §10 of the v0.1 preprint. The v0.2 spec is intended to be implementable from grammar text alone, without reference to PyYAML or any single-language emitter.

---

## What changes

| # | Change | v0.1 | v0.2 | Why |
|---|---|---|---|---|
| 1 | Canonical string scalars | plain when possible, single-quoted otherwise (PyYAML heuristic) | **always single-quoted** | Eliminates plain-scalar predicate ambiguity across YAML libraries |
| 2 | `seed` representation | unquoted integer up to 2⁶⁴-1 | **quoted decimal string** | Removes JSON parser precision loss above 2⁵³ |
| 3 | `threshold` rendering | integer-valued floats render as integer | **always at least one decimal place** | Preserves float typing across JSON round-trips |
| 4 | `hash_alg` field | implicit `sha-256` | **explicit, enum** `sha-256 \| sha3-256 \| blake3` | Algorithm agility for the post-quantum decade |
| 5 | `tolerance` field | absent (bit-exact compare) | **optional, float**; verifier uses `\|observed - threshold\| ≤ tolerance` when present | Hardware non-determinism in floats |
| 6 | `claims:` sequence | one (metric, comparator, threshold) per manifest | **optional sequence** of claim tuples sharing dataset + seed | Multi-metric reports without manifest explosion |
| 7 | `producer.signature` | optional | **mandatory for high-risk Annex III** systems via `producer.tier: high-risk` | EU AI Act Article 15 cybersecurity requirements |
| 8 | Canonicalization grammar | English prose + 12 vectors | **formal ABNF grammar in spec §3** | Spec implementable from text alone |
| 9 | Test vectors | 12 | **24** (TV-013 → TV-024 cover Unicode normalisation, control chars, signature roundtrip, multi-claim, tolerance, prior_hash chains of length 5+) | Coverage for new fields and edge cases |
| 10 | Sidecar format | `<name>.prml.sha256` | **`<name>.prml.sha256` unchanged** + new `<name>.prml.sig` for signatures | Backward-compatible signature attachment |

---

## Detailed designs

### 1. Always-quoted string scalars

The v0.1 canonical form decides per-string whether to plain-render or single-quote, mirroring PyYAML's `safe_dump`. The predicate involves indicator characters, leading/trailing whitespace, colon-space ambiguity, and number/boolean/null/timestamp resolution. Different YAML libraries make subtly different decisions; the second-implementation exercise found `==` accepted as plain by PyYAML but quoted by `js-yaml` (TV-008).

**v0.2 rule:** every value of YAML type `string` is rendered with single-quotes in the canonical form, regardless of whether plain rendering would be valid. Internal single quotes are doubled (PyYAML standard).

**Cost:** approximately 8–12% larger canonical bytes per typical PRML manifest. For TV-001 the 12-line manifest grows from 308 to ~340 characters.

**Benefit:** eliminates an entire class of cross-library divergence. The new rule is a single sentence in §3.4.

**Migration:** v0.2 manifests are not byte-compatible with v0.1. The hash differs. v0.2 explicitly bumps the `version` field to `prml/0.2`, and a v0.2 verifier rejects a `prml/0.1` document with exit code 11 (GUARD).

### 2. `seed` as quoted decimal string

The v0.1 spec allows `seed` in the range $[0, 2^{64}-1]$. JSON parsers in JavaScript (default), Go (`int64`), and Java (`long`) lose precision above $2^{53}$, $2^{63}-1$, and $2^{63}-1$ respectively (TV-006).

**v0.2 rule:** `seed` is a string field whose value is a decimal representation of a non-negative integer in $[0, 2^{64}-1]$, with no leading zeros (except `'0'`), no thousands separators, no sign. Canonical rendering: single-quoted, e.g. `seed: '18446744073709551615'`.

**Trade-off considered:** capping seed at $2^{53}-1$ would also work and would match Number-native languages, but at the cost of losing one bit per common entropy source (most `numpy.random.SeedSequence` outputs use the full 64-bit space).

### 3. `threshold` always rendered with a decimal place

JSON's `1.0` and `1` are indistinguishable after parse in many languages (TV-008).

**v0.2 rule:** the canonical form of `threshold` always contains at least one decimal point. Integer-valued thresholds render as `1.0`, `0.5` renders as `0.5`, `0.875` renders as `0.875`. The shortest round-trip representation is used otherwise.

**Implementation hint:** every conformant emitter must field-detect `threshold` and force `.0` suffix when the underlying value is an integer-valued float. The spec lists the field by name in §3.2.

### 4. `hash_alg` field

The v0.1 spec hard-codes SHA-256. Post-quantum migration is named in §10.3 as future work.

**v0.2 rule:** required field `hash_alg`, lowercase string, enum:

- `'sha-256'` — the v0.1 default; v0.2 default for backwards interoperability
- `'sha3-256'` — for environments that want SHA-3 as a hedge
- `'blake3'` — for high-throughput pipelines that need keyed hashing

A verifier processes the manifest by running the named algorithm over the canonical bytes. The sidecar file format extends to `<digest hex> <space> <alg>`, e.g. `1a3466cc... sha-256`.

### 5. `tolerance` field

Floating-point determinism is not bit-exact across hardware classes (CUDA vs CPU, AVX-512 vs AVX2). v0.1 demands bit-exact compare; v0.2 allows declared tolerance.

**v0.2 rule:** optional field `tolerance`, float, non-negative. When present, the verdict predicate becomes:

\[
\text{verdict} = \begin{cases}
\text{PASS} & \text{if } |observed - threshold| \leq tolerance \text{ and } observed \mathbin{\texttt{comparator}} threshold \\
\text{FAIL} & \text{otherwise}
\end{cases}
\]

When absent, behaviour is identical to v0.1: bit-exact compare.

### 6. `claims:` sequence (multi-metric)

A typical eval report includes accuracy, F1, AUROC, and latency at various p99 buckets. Under v0.1, each requires its own manifest. v0.2 allows a single manifest to bind multiple claims sharing the same dataset and seed.

**v0.2 rule:** optional field `claims`, sequence of `(metric, comparator, threshold, tolerance?)` tuples. When `claims` is present, the top-level `metric`/`comparator`/`threshold`/`tolerance` are absent. The verdict is `PASS` iff all claims in the sequence pass.

**Canonical form:** sequence items are sorted lexicographically by `metric`, then by `comparator`, then by `threshold`. Each item is rendered as a block-style mapping.

### 7. Mandatory signatures for high-risk Annex III systems

EU AI Act Article 15 requires high-risk systems to demonstrate cybersecurity. Producer signatures are an inexpensive cryptographic component of that demonstration.

**v0.2 rule:** new optional field `producer.tier`, enum: `'standard'` (default), `'high-risk'`. When `'high-risk'`:

- `producer.public_key` is required (Ed25519 hex, 64 chars).
- A sidecar `<name>.prml.sig` containing the Ed25519 signature over the canonical manifest bytes is required.
- Verifier exit code 11 (GUARD) when missing or invalid.

For non-high-risk producers the signature remains optional. The format is identical so a producer can opt-in incrementally.

### 8. Formal canonicalization ABNF grammar

The v0.1 spec describes canonicalization in English plus twelve test vectors. v0.2 publishes a complete ABNF grammar in §3.4. With the always-quoted rule (change #1) the grammar is short — approximately 40 production rules — and unambiguous.

The grammar is the source of truth for conformance. Test vectors illustrate; the grammar defines.

### 9. Twenty-four conformance vectors

v0.1 ships twelve. v0.2 adds twelve more, targeting:

| Vector | Property |
|---|---|
| TV-013 | Unicode NFC normalisation in `producer.id` (NFC vs NFD canonical equivalence) |
| TV-014 | Control character rejection (`\x07` in any string field → exit 11) |
| TV-015 | Maximum-length field (1 MiB string) |
| TV-016 | `claims:` sequence of length 5 |
| TV-017 | `tolerance: 1.0e-6` with bit-exact pass |
| TV-018 | `tolerance: 1.0e-6` with within-tolerance pass |
| TV-019 | `tolerance` violation produces FAIL |
| TV-020 | `hash_alg: sha3-256` digest reproduction |
| TV-021 | `hash_alg: blake3` digest reproduction |
| TV-022 | `producer.tier: high-risk` with valid Ed25519 signature → PASS |
| TV-023 | `producer.tier: high-risk` with invalid signature → exit 11 GUARD |
| TV-024 | Amendment chain of length 5 with mixed `hash_alg` (allowed) |

### 10. Sidecar formats

v0.1 sidecar: single-line lowercase hex SHA-256.

v0.2 sidecar: single line, `<digest hex> <space> <alg>`, e.g. `1a3466cc08ee... sha-256`. Backward-compatible with v0.1: a v0.1 verifier reading a v0.2 sidecar takes the first whitespace-delimited token as the digest and ignores the rest.

A new optional sidecar `<name>.prml.sig` carries the Ed25519 detached signature when `producer.tier == 'high-risk'`.

---

## Migration v0.1 → v0.2

A v0.1 manifest is converted to a v0.2 manifest by:

1. Setting `version: 'prml/0.2'`.
2. Adding `hash_alg: 'sha-256'`.
3. Quoting all string scalars (always-single-quoted rule).
4. Converting `seed` from integer to string.
5. Forcing `threshold` to render with a decimal point.

The `falsify migrate` subcommand performs this transformation in one step. The output is a new manifest with a different hash; the migration is not in-place. The v0.1 manifest's history is preserved as the `prior_hash` of the v0.2 manifest, so the audit chain bridges versions cleanly.

---

## Schedule

| Date | Milestone |
|---|---|
| 2026-05-01 | RFC opens (this document published) |
| 2026-05-08 | Open RFC questions answered; field designs frozen |
| 2026-05-15 | Twelve new test vectors generated; reference Python impl updated |
| 2026-05-22 | **Spec freeze** — no further breaking changes |
| 2026-05-29 | Final review window for ABNF grammar, signature flow, migration tool |
| 2026-06-05 | Conformance suite v0.2 finalized; second implementation (Node.js) updated |
| 2026-06-15 | **v0.2 release** — published at `spec.falsify.dev/v0.2`, GitHub tag `v0.2.0` |

---

## Open RFC questions

The following are not yet resolved. Comment in [GitHub Discussions](https://github.com/studio-11-co/falsify/discussions/6) before 2026-05-22.

**RFC-Q-01:** Should `hash_alg: blake3` ship in v0.2 or wait until v0.3?

There is a practical case for BLAKE3 (high throughput, keyed mode for HMAC-style integrity). There is a practical case against (NIST has not yet standardised BLAKE3, and notified bodies prefer FIPS-validated primitives). Default position: include with a footnote that for FIPS contexts, `sha-256` or `sha3-256` is required.

**RFC-Q-02:** Should `claims:` allow per-claim seeds or only manifest-level seed?

Per-claim seeds support the case where each metric has its own random state (e.g. metric-specific bootstrapping). Manifest-level seed is simpler and matches the typical eval harness. Default position: manifest-level only in v0.2; per-claim seeds deferred to v0.3.

**RFC-Q-03:** Should `tolerance` be absolute or relative or both?

Absolute (`|o - t| ≤ tol`) is simple and what most consumers expect. Relative (`|o - t| / |t| ≤ tol`) handles wide-dynamic-range metrics like FLOPs. Both is overkill. Default position: absolute only; if relative is needed, encode as percentage in `notes` for v0.2 and add a structured field in v0.3.

**RFC-Q-04:** Should the always-quoted rule apply to numbers as well?

Numbers in v0.1 are unquoted (`seed: 42`, `threshold: 0.85`). Always-quoting numbers (`seed: '42'`, `threshold: '0.85'`) would close the integer-vs-float ambiguity entirely but at the cost of human readability.

**Updated position (2026-05-01):** evidence from the v0.2 candidate vector run (TV-018, `threshold: 1e-6`) shows that small-magnitude float rendering diverges three ways across Python (`1.0e-06`), JavaScript (`0.000001`), and Go (`1e-06`) — see [Finding 4 in the portability analysis](../analysis/canonicalization-portability-v0.1.md#finding-4-float-rendering-for-small-magnitude-values-diverges-three-ways). Each is a defensible language-stdlib default; specifying a single canonical numeric format would force every implementation to reimplement Python's `repr(float)`, which is brittle.

**Recommendation:** adopt the always-quoted rule for numbers as well as strings. The producer chooses the textual form once (e.g. `threshold: '0.000001'` or `threshold: '1.0e-06'`); verifiers honour it byte-for-byte. Cost: ~5% additional canonical bytes for typical PRML manifests. Benefit: language-stdlib float-rendering quirks become invisible; TV-018 (and any future small-float vector) becomes promotable to normative.

This now joins change #1 (always-quoted strings) under one consistent rule: **all leaf scalars are single-quoted in the canonical form**.

**RFC-Q-05:** Should signatures be detached (in `.prml.sig`) or inline (as a `producer.signature` field)?

Detached preserves clean separation of identity and content. Inline simplifies file management. Default position: detached; the signature is itself content-addressable and independently verifiable.

---

## Non-goals for v0.2

These are deliberately out of scope and remain v0.3+:

- On-chain anchoring of chain hashes
- Native CBOR encoding alongside YAML
- Per-claim seeds inside `claims:` sequences
- Per-claim datasets inside `claims:` sequences
- Compute-envelope semantics (HW class, SW stack hash) beyond the v0.1 free-form `compute_envelope` field
- Differential-privacy budget binding
- Multi-producer signatures (e.g. for federated training claims)

---

## What this document is not

- It is not the v0.2 specification itself. The spec is published at `spec.falsify.dev/v0.2` once the freeze passes.
- It is not a marketing document. The audience is implementers, reviewers, and auditors.
- It is not committed in the strict normative sense until 2026-05-22. Field designs may shift in response to RFC comments.

---

*Working draft, CC BY 4.0. Comments via [GitHub Discussions](https://github.com/studio-11-co/falsify/discussions/6) or `hello@studio-11.co`.*
