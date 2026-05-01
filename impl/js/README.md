# falsify-js — PRML v0.1 second reference implementation

A single-file Node.js implementation of PRML v0.1, demonstrating that the canonicalization is implementable in a second language byte-for-byte against the v0.1 conformance vectors.

**Status:** working draft, intended as portability evidence rather than a production tool. The Python reference implementation (`falsify`, in the repo root) remains the recommended runtime.

**Result:** 12 / 12 v0.1 conformance vectors pass byte-for-byte.

---

## Run

No build step. Requires Node.js ≥ 18.

```bash
# Conformance suite
node falsify.js test-vectors ../../spec/test-vectors/v0.1/test-vectors.json

# Hash a manifest (JSON or YAML)
node falsify.js hash my-manifest.json

# Lock a manifest (writes <name>.prml.sha256 sidecar)
node falsify.js lock my-manifest.json

# Verify a manifest against its sidecar; if --observed given, evaluate predicate
node falsify.js verify my-manifest.json --observed 0.876
```

Exit codes match the spec: `0` PASS, `3` TAMPERED, `10` FAIL, `11` GUARD.

---

## What this is

About 400 lines of Node.js, zero runtime dependencies beyond the Node.js standard library (`fs`, `path`, `crypto`). Optional dependency on `js-yaml` for loading `.yaml` files; not required for `.json` input.

The canonicalizer is hand-rolled to match PyYAML's `safe_dump` output exactly. It does not use a generic YAML serializer because `js-yaml` (and other YAML libraries) make different plain-scalar quoting decisions than PyYAML, producing canonical bytes that diverge from the v0.1 vectors.

---

## What this is not

- Not a production tool. Use the Python reference implementation for running real evaluations.
- Not a complete YAML implementation. Loading `.yaml` files works only via `js-yaml`'s parser; the canonicalizer is tuned to PRML v0.1 manifest shapes, not arbitrary YAML.
- Not stable across spec versions. v0.2 will introduce a formal canonicalization grammar; this implementation will be rewritten to match the v0.2 grammar.

---

## Why it exists

To prove the v0.1 specification is implementable from a second language without reading the Python reference. The exercise surfaced three non-obvious cross-language pitfalls — uint64 precision, integer-valued float typing, plain-scalar quoting heuristics — documented in [`spec/analysis/canonicalization-portability-v0.1.md`](../../spec/analysis/canonicalization-portability-v0.1.md). Those findings motivate the v0.2 formal grammar work.

---

## Dependency note

The optional `js-yaml` dependency is present only for parsing `.yaml` input files. If you pass `.json` files (which the test vectors do), no external dependencies are required.

```bash
# Optional, only for .yaml input loading
npm install js-yaml
```

---

## License

MIT. Same as the rest of the repository.
