# PRML — Pre-Registered ML Manifest Specification

**Version:** 0.1 (Draft)
**Date:** 2026-05-01
**Status:** Working Draft — Public Review
**Editor:** Studio-11 \<hello@studio-11.co\>
**Reference Implementation:** [falsify](https://github.com/sk8ordie84/falsify) (MIT)
**Canonical URL:** https://spec.falsify.dev/v0.1
**License:** CC BY 4.0

---

## Abstract

PRML defines a content-addressed serialization format for pre-registered machine
learning evaluation claims. A PRML manifest binds a metric, a numeric threshold,
a dataset content hash, and a random seed to a SHA-256 digest produced **before**
the experiment runs. After the experiment, an independent verifier recomputes the
hash, executes the evaluation against the pre-registered parameters, and emits a
deterministic verdict.

The format is designed to be implementable in any language, transmittable as a
plain text artifact, and verifiable without network access. PRML is **not** an
experiment-tracking platform; it is a primitive intended to underlie such
platforms and to satisfy regulatory audit-trail obligations under regimes
including the EU AI Act (Regulation 2024/1689) Articles 12 and 18.

---

## Status of This Memo

This document is a working draft published for public review. It is **not** a
finished standard. Comments are invited at
`github.com/sk8ordie84/falsify/discussions` or by email to `hello@studio-11.co`.

The next planned revision (v0.2) will incorporate review feedback and freeze the
canonicalization rules of §3.

---

## 1. Introduction

### 1.1 Motivation

Machine learning evaluations suffer from a credibility gap that conventional
experiment-tracking tools do not close. The metric, threshold, dataset, and seed
that a team claims to have committed to *before* a training run are typically
recorded only after results are observed, if at all. Post-hoc revision of these
parameters — moving a threshold from 0.85 to 0.83, swapping a held-out split,
re-rolling a seed — is mechanically indistinguishable from honest reporting in
the absence of a cryptographic pre-commitment.

Three contemporary forces make this gap urgent:

1. **Regulatory.** The EU AI Act's logging (Article 12) and recordkeeping
   (Article 18) obligations enter force August 2, 2026. High-risk AI providers
   must demonstrate that performance claims attached to a deployed model are the
   same claims registered prior to deployment.
2. **Scientific.** Benchmark contamination, data leakage, and selective
   reporting consistently degrade the informativeness of public evaluations.
3. **Commercial.** Capability claims attached to frontier model releases are
   frequently disputed precisely because no public, tamper-evident record of the
   evaluation contract exists.

PRML proposes the smallest sufficient primitive to close this gap: a hash-bound
manifest, written before the run, verified after.

### 1.2 Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in [RFC 2119].

The following terms have specific meaning in this specification:

- **Manifest** — A document conforming to §2 that pre-registers an evaluation
  claim.
- **Canonical bytes** — The byte sequence produced by serializing a manifest
  according to §3.
- **Manifest hash** — `SHA-256(canonical bytes)`, encoded as 64 lowercase
  hexadecimal characters.
- **Producer** — The party that creates and publishes a manifest before the
  evaluation runs.
- **Verifier** — Any party (including the producer) that independently
  recomputes the manifest hash and the evaluation outcome.
- **Audit log** — The append-only sequence of manifests covering successive
  amendments to a registered claim (§6).

---

## 2. Manifest Structure

### 2.1 Required Fields

A PRML manifest is a YAML 1.2 document. Implementations **MUST** populate the
following top-level keys:

| Key | Type | Description |
|---|---|---|
| `version` | string | Spec version. **MUST** equal `"prml/0.1"` for this revision. |
| `claim_id` | string | UUIDv7 identifier for the claim. **MUST** be unique per producer. |
| `created_at` | string | RFC 3339 timestamp in UTC, second precision. |
| `metric` | string | Identifier of the metric being claimed. See §2.3.1. |
| `comparator` | string | One of `>=`, `>`, `==`, `<=`, `<`. See §5.1. |
| `threshold` | number | Real number the metric is compared against. |
| `dataset` | mapping | Identifier and content hash of the dataset. See §2.3.2. |
| `seed` | integer | Non-negative 64-bit integer. |
| `producer` | mapping | Identity of the manifest producer. See §2.3.3. |

### 2.2 Optional Fields

| Key | Type | Description |
|---|---|---|
| `metric_args` | mapping | Free-form arguments parameterizing the metric. |
| `model` | mapping | Identifier of the model under test, if known pre-run. |
| `code` | mapping | Identifier of the code (e.g., git commit) used to evaluate. |
| `prior_hash` | string | Manifest hash of the previous claim in an amendment chain (§6). |
| `notes` | string | Human-readable annotation. **MUST NOT** affect verification. |

### 2.3 Field Semantics

#### 2.3.1 `metric`

The `metric` value **MUST** be either:

- A registered identifier from the PRML Metric Registry (forthcoming, §11), or
- A URI dereferencing to a published definition.

Examples: `accuracy`, `f1_macro`, `https://example.org/metrics/calibration_ece`.

#### 2.3.2 `dataset`

```yaml
dataset:
  id: <human-readable identifier>
  hash: <hex SHA-256 of canonical dataset bytes>
  uri: <optional retrieval URI>
```

The `hash` field **MUST** be the SHA-256 digest of the dataset's canonical byte
representation. The canonical representation is dataset-format-specific and
**SHOULD** be documented in the dataset's accompanying datasheet.

#### 2.3.3 `producer`

```yaml
producer:
  id: <DNS-name, ORCID, or GitHub handle>
  signature: <optional detached PGP or minisign signature>
```

The `signature` field, when present, **MUST** be a signature over the manifest
hash, not over the manifest contents. This permits signature verification
without re-running canonicalization.

---

## 3. Canonical Serialization

### 3.1 YAML Subset

A PRML manifest **MUST** be expressible in the following YAML subset:

- Block-style mappings only (no flow-style).
- Plain scalars, double-quoted scalars, and integers.
- No anchors, aliases, or tags beyond `!!str`, `!!int`, `!!float`.
- ASCII-only, except where UTF-8 is explicitly permitted (e.g., `notes`).

### 3.2 Key Ordering

For canonicalization, all mappings **MUST** be reserialized with keys in
lexicographic byte order. Nested mappings are ordered recursively.

### 3.3 Whitespace and Encoding

- Canonical output **MUST** be UTF-8 encoded.
- Indentation **MUST** be exactly two spaces per level.
- Each key-value line **MUST** terminate with a single LF (`0x0A`).
- The canonical byte sequence **MUST** end with a single LF.
- Trailing whitespace is **PROHIBITED**.
- Comments are **PROHIBITED** in canonical form.

A reference canonicalizer is provided by the falsify implementation and produces
output byte-equivalent to the rules above for any conforming input.

---

## 4. Hash Algorithm

The manifest hash **MUST** be computed as:

```
hash = lowercase_hex(SHA-256(canonical_bytes))
```

Implementations **MUST NOT** strip a trailing newline, normalize line endings to
CRLF, or otherwise alter `canonical_bytes` before hashing.

The hash **SHOULD** be published alongside the manifest in a sidecar file
named `<claim_id>.prml.sha256`.

---

## 5. Verification Semantics

### 5.1 Comparison Operators

| `comparator` | Pass condition |
|---|---|
| `>=` | observed ≥ threshold |
| `>` | observed > threshold |
| `==` | abs(observed - threshold) < tolerance |
| `<=` | observed ≤ threshold |
| `<` | observed < threshold |

The `==` comparator's tolerance defaults to `1e-9`. Producers **MAY** override
this by setting `metric_args.tolerance`.

### 5.2 Pass/Fail Determination

A verifier **MUST**:

1. Recompute the manifest hash from `canonical_bytes` and verify it matches the
   published hash.
2. Recompute the dataset hash from the dataset content and verify it matches
   `dataset.hash`.
3. Execute the evaluation using the manifest's `metric`, `metric_args`, `seed`,
   and dataset.
4. Apply the comparator from §5.1.
5. Emit a verdict per §7.

### 5.3 Tampering Detection

If the recomputed manifest hash does not match the published hash, the verifier
**MUST** abort verification and **MUST NOT** emit a Pass or Fail verdict.
Implementations **MUST** signal tampering distinctly from evaluation failure
(see §7).

---

## 6. Amendment Protocol

PRML treats every claim as immutable once hashed. Honest revision is supported
through an explicit, append-only amendment chain.

### 6.1 Forward-Only Audit Log

A producer who needs to change any field of a previously-registered claim
**MUST** create a new manifest whose `prior_hash` field equals the manifest
hash of the previous claim. The new manifest **MUST** retain the `claim_id` of
the previous claim.

The full sequence of manifests sharing a `claim_id`, ordered by `created_at`
and verified by the `prior_hash` chain, constitutes the audit log for that
claim.

### 6.2 Amendment Semantics

- The previous manifest is **NOT** deleted, overwritten, or revoked.
- Verifiers **MUST** treat the latest manifest in the chain as the operative
  one, but **MUST** also expose the full chain when requested.
- Hash-equality of two claims with identical content but different `created_at`
  values **MUST NOT** occur; canonicalization includes the timestamp.

### 6.3 Amendment Chain Hash

An aggregate identifier for the full chain, suitable for public posting, is:

```
chain_hash = SHA-256(concat(canonical_bytes_1, canonical_bytes_2, ..., canonical_bytes_n))
```

where the manifests are concatenated in `created_at` order.

---

## 7. Exit Code Specification

Reference implementations **MUST** signal verification outcomes via the
following exit codes:

| Code | Meaning |
|---|---|
| `0` | Pass — manifest verified, evaluation satisfies comparator. |
| `10` | Fail — manifest verified, evaluation does not satisfy comparator. |
| `3` | Tampered — manifest hash mismatch, verification aborted. |
| `11` | Guard violation — manifest is well-formed but a producer-declared invariant (e.g., dataset-hash mismatch, seed out of range) failed. |
| `2` | Usage error — invalid command-line arguments or unreadable manifest. |
| `1` | Unspecified runtime error. |

Codes other than `0`, `1`, `2`, `3`, `10`, `11` are **RESERVED**.

---

## 8. Security Considerations

### 8.1 Threat Model

PRML protects against **silent post-hoc revision** of a registered claim. It
does **NOT** protect against:

- A producer who never publishes the manifest at all.
- A producer who publishes a manifest privately, runs the evaluation, then
  publishes only on Pass (selective publication).
- A producer colluding with the dataset host to alter dataset content while
  preserving its declared hash (broken hash function).
- A producer signing a manifest with a key the verifier cannot validate.

Mitigations require external mechanisms: timestamping services (RFC 3161),
public manifest registries, or signed dataset hosts.

### 8.2 Hash Algorithm Agility

This revision fixes SHA-256 as the hash algorithm. Future revisions **MAY**
introduce algorithm agility via a `hash_algorithm` field defaulting to
`sha-256`. Verifiers conforming to v0.1 **MUST** reject manifests declaring any
other algorithm.

### 8.3 Canonical Form Attacks

A producer who serializes a manifest non-canonically and publishes the
non-canonical hash is detectable: any verifier recanonicalizing the manifest
will compute a different hash and emit Tampered (exit 3). This places
canonicalization correctness on the verifier, not the trust path.

---

## 9. Compliance Mapping (Informative)

This section is non-normative.

### 9.1 EU AI Act (Regulation 2024/1689)

| Article | Obligation | PRML coverage |
|---|---|---|
| 12 | Automatic recording of events over the system's lifetime | A PRML chain is the record of evaluation events with a tamper-evident hash chain. |
| 18 | Documentation retention for 10 years post-market | PRML manifests are plain text artifacts <1 KB; retention is trivial. |
| 17 | Quality management system covering performance | Pre-registered thresholds satisfy the "objective performance metric" requirement. |
| 50 | Transparency obligations for deployers | Public manifest hashes provide the receipt deployers need. |

### 9.2 NIST AI Risk Management Framework

PRML directly supports the **MEASURE** and **MANAGE** functions: pre-registered
manifests establish the metric framework before deployment and provide the
evidence trail for ongoing monitoring.

### 9.3 ISO/IEC 42001 (AI Management System)

PRML manifests are admissible as objective evidence under §8.4 (Operational
Planning and Control) of ISO/IEC 42001:2023.

---

## 10. Reference Implementation

The [falsify](https://github.com/sk8ordie84/falsify) project provides a
reference implementation in Python. Conformance to this specification is
defined as:

1. Producing canonical bytes byte-equivalent to the falsify reference for the
   PRML test vector suite (Appendix B, forthcoming).
2. Computing manifest hashes byte-equivalent to the reference.
3. Emitting exit codes per §7 for the test vector suite.

A conformance test harness will be published with v0.2.

---

## 11. IANA Considerations

This document requests the registration of:

- File extension: `.prml`
- MIME type: `application/vnd.prml+yaml`
- Sidecar extension: `.prml.sha256`

A PRML Metric Registry will be established with v0.2.

---

## 12. References

### Normative

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", March 1997.
- [RFC 3339] Klyne, G., "Date and Time on the Internet: Timestamps", July 2002.
- [FIPS 180-4] NIST, "Secure Hash Standard", August 2015.
- [YAML 1.2] YAML Specification, October 2009.

### Informative

- [EU 2024/1689] Regulation (EU) 2024/1689 (AI Act), June 2024.
- [NIST AI RMF] NIST AI Risk Management Framework 1.0, January 2023.
- [ISO 42001] ISO/IEC 42001:2023, AI Management System.
- [Gelman 2018] Gelman, A. & Loken, E., "The garden of forking paths".
- [Ioannidis 2005] Ioannidis, J., "Why most published research findings are false".

---

## Appendix A — Minimal Example Manifest

```yaml
version: "prml/0.1"
claim_id: "01900000-0000-7000-8000-000000000000"
created_at: "2026-05-01T12:00:00Z"
metric: "accuracy"
comparator: ">="
threshold: 0.85
dataset:
  id: "imagenet-val-2012"
  hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
seed: 42
producer:
  id: "studio-11.co"
```

Canonical bytes hash (illustrative; verify with reference implementation):

```
b2c3a1f0d8e7c6b5a4938271605f4e3d2c1b0a9988776655443322110ffeeddc
```

---

## Appendix B — Test Vectors

*(To be published with v0.2. See `falsify/tests/spec_conformance/` for the
reference vector seed.)*

---

## Change Log

- **v0.1 (2026-05-01)** — Initial public draft.

---

*Editor's note: This document is intended to be readable, implementable, and
boring. Excitement is reserved for what gets built on top of it.*
