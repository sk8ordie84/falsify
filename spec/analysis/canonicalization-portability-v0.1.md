# PRML v0.1 — Canonicalization Portability Findings

**Question:** Is the v0.1 canonicalization implementable in a second language byte-for-byte?

**Answer:** Yes — a 400-line Node.js implementation reproduces all twelve v0.1 conformance vectors with bit-identical canonical bytes and matching SHA-256 digests. The exercise surfaced three non-obvious cross-language pitfalls that the v0.1 prose specification under-specifies. This document records them so v0.2 can address each in formal grammar form.

**Source:** [`impl/js/falsify.js`](../../impl/js/falsify.js) — single file, no external runtime deps.

**Result:** 12 / 12 vectors pass byte-for-byte.

---

## Why this matters

A specification that exists in only one implementation is indistinguishable from that implementation's bugs. v0.1 ships with twelve test vectors whose exact byte sequences are derived from PyYAML's `safe_dump`. Any second implementation that produces the same digest must produce the same canonical bytes. This is a strict constraint: a single byte difference anywhere in the output produces an entirely different SHA-256.

The Python reference implementation reaches canonical bytes by leaning on PyYAML's twenty-year-old `safe_dump` heuristics (sorted keys, plain-vs-quoted scalar decisions, float formatting). PyYAML is portable in the sense that the *parser* is portable, but the *emitter*'s output is a de-facto standard, not a de-jure one. This document is the audit of whether the emitter's behaviour is recoverable from the spec without reading PyYAML.

---

## Three findings

### Finding 1: 64-bit integer precision

**Vector affected:** TV-006 (`seed: 18446744073709551615`, the maximum unsigned 64-bit integer).

**Symptom:** A naïve JavaScript implementation that uses `JSON.parse` followed by `js-yaml`'s `dump` produces:

```
seed: 18446744073709552000
```

instead of the expected:

```
seed: 18446744073709551615
```

**Root cause:** ECMAScript's `Number` is IEEE-754 binary64. The largest safely representable integer is $2^{53}-1 \approx 9.007 \times 10^{15}$. The spec's allowed seed range is $[0, 2^{64}-1]$, which is roughly $1.8 \times 10^{19}$. Any seed above $2^{53}$ rounds during JSON parse, **before the canonicalizer ever runs**.

**Languages affected:**

| Language    | Native int range | TV-006 round-trips? |
|---          |---               |---                  |
| Python 3    | unbounded        | yes                 |
| JavaScript  | $2^{53}-1$       | **no** without BigInt |
| Go (`int64`) | $2^{63}-1$      | **no** for $> 2^{63}-1$ |
| Rust (`u64`) | $2^{64}-1$      | yes                 |
| Java (`long`) | $2^{63}-1$     | **no** for $> 2^{63}-1$ |

**Workaround in Node.js implementation:** Pre-process the JSON text with a regex that wraps any 16-or-more-digit integer in a sentinel string, parse, then unwrap to `BigInt`. This works but is a hack.

**v0.2 recommendation:** Either (a) restrict `seed` to $[0, 2^{53}-1]$ and lose nothing of practical value (no real ML benchmark uses seeds above $2^{53}$), or (b) require seed to be encoded as a quoted string in the canonical form, eliminating the parser-level precision concern entirely. Option (b) is cleaner and is the recommendation.

---

### Finding 2: Integer-valued floats lose their type

**Vector affected:** TV-008 (`threshold: 1.0`, an integer-valued float).

**Symptom:** A JS implementation that does `JSON.parse('{"threshold": 1.0}')` receives a `Number(1)`, indistinguishable at runtime from `Number(1)` produced by `JSON.parse('{"threshold": 1}')`. When that number is dumped via `js-yaml`, it emits `threshold: 1`, not `threshold: 1.0`. The Python reference, in contrast, preserves `float` vs `int` typing through PyYAML's load/dump cycle and emits `1.0`.

**Root cause:** Many languages' JSON parsers do not preserve the distinction between integer-valued floats and integers. JSON the format does not distinguish them either: `1.0` and `1` are both "numbers." The typing distinction lives in the producer's runtime, not in the wire format.

**Workaround in Node.js implementation:** A field-level hint: the canonicalizer maintains a small set, `FLOAT_FIELDS = {'threshold'}`, and forces any integer in those fields to render with a `.0` suffix. This works for v0.1 but is field-specific and not extensible.

**v0.2 recommendation:** Mark `threshold` (and any future float field) as **canonically rendered with at least one decimal place**, even when integer-valued. The canonical form for an integer-valued threshold is `1.0`, not `1`. This is a single sentence in the spec that closes the ambiguity.

---

### Finding 3: Plain-scalar quoting heuristics differ across YAML libraries

**Vector affected:** TV-008 (`comparator: ==`, unquoted plain scalar).

**Symptom:** `js-yaml` dumps the comparator string `==` as `comparator: '=='` (single-quoted). PyYAML emits the same value as `comparator: ==` (plain). For other comparators (`>=`, `<=`, `>`, `<`), both libraries quote: PyYAML because `>` is a YAML indicator character, `js-yaml` for the same reason.

**Root cause:** YAML 1.1/1.2 specifies a class of "plain scalars" that need not be quoted. The decision of *whether a particular string can be a plain scalar* is a complex predicate involving leading character (must not be a YAML indicator), middle content (no `: ` mapping ambiguity, no ` #` comment ambiguity), and resolution rules (must not look like a number, boolean, null, or timestamp). PyYAML and `js-yaml` implement this predicate with subtle differences. The `==` case is one of them: PyYAML accepts it as plain because no character in `==` is a YAML indicator and no resolution rule fires; `js-yaml` quotes defensively.

**Workaround in Node.js implementation:** Re-implement the plain-scalar predicate from scratch, matching PyYAML's behaviour. The implementation is in `needsQuoting(s)` and is approximately fifty lines of JavaScript. It checks: indicator-prefix, leading/trailing whitespace, colon-space and hash-space ambiguity, number-resolution regex, boolean/null set, timestamp regex, and control-character escape. With this hand-rolled predicate, TV-008 reproduces.

**v0.2 recommendation:** Adopt the path the v0.1 paper already names in §10 (limitations): publish a **formal canonicalization grammar in BNF or ABNF**. The grammar should include the plain-scalar predicate as a positive rule (`plain := first-char *plain-char ; first-char excludes [...]; plain-char excludes [...]`) rather than as a negative reference to a parent YAML spec. With a positive grammar, any second implementation can match without reverse-engineering an emitter's heuristics.

A simpler, more aggressive alternative: **always quote string scalars** in the canonical form. This eliminates the predicate entirely. Cost: ~10% larger canonical bytes for the typical PRML manifest. Benefit: zero ambiguity. We recommend this for v0.2 unless a strong reason emerges to keep the plain-scalar form.

---

## Empirical conformance result

The Node.js implementation runs against the v0.1 conformance suite as follows:

```bash
$ node impl/js/falsify.js test-vectors spec/test-vectors/v0.1/test-vectors.json
PASS  TV-001  Minimal valid manifest
PASS  TV-002  Key ordering — random insertion order
PASS  TV-003  Threshold mutation — single field change
PASS  TV-004  Optional fields — model and dataset.uri populated
PASS  TV-005  Unicode in producer.id
PASS  TV-006  Maximum seed value
PASS  TV-007  Minimum seed value
PASS  TV-008  Equality comparator
PASS  TV-009  Amendment manifest with prior_hash
PASS  TV-010  pass@k metric for code generation
PASS  TV-011  AUROC with low threshold
PASS  TV-012  MAE for regression

Result: 12/12 vectors passed.
```

This demonstrates the format is implementable in a second language, byte-for-byte. The implementation uses approximately 400 lines of Node.js with no runtime dependencies beyond the standard library.

The implementation is provided as evidence of portability, not as a production tool. Production users should continue to use the Python reference implementation (`falsify`) at this stage. The Node.js implementation will be promoted to a first-class artifact once v0.2 lands with the formal grammar that closes the three findings above.

---

## Action items for v0.2

1. **Restrict seed range or quote it.** Either cap at $[0, 2^{53}-1]$ or render as a quoted string. Recommendation: render as quoted string.
2. **Always render floats with at least one decimal place.** `threshold: 1.0`, never `threshold: 1`.
3. **Publish a formal canonicalization grammar.** Either an ABNF for a tight strict subset, or — preferred — a rule that all string scalars are always single-quoted in canonical form, eliminating the plain-scalar predicate.

These three actions together reduce the spec's portability surface from "depends on PyYAML's emitter heuristics" to "depends only on the formal grammar in §3." Any conformant second implementation can then be built from the specification text alone, without reading any reference implementation source.

---

## What this exercise does *not* prove

- It does not prove that **all** PyYAML edge cases are covered. The Node.js implementation matches the twelve current vectors, which exercise specific cases. Adding new vectors (Unicode normalisation, control characters, very long strings, line-folding edge cases) may reveal further divergences.
- It does not prove that **all language YAML libraries** agree with PyYAML. We tested Node.js + `js-yaml`. Go's `gopkg.in/yaml.v3`, Rust's `serde_yaml`, and Java's SnakeYAML each have their own quirks. The findings above are likely a subset of the full surface.
- It does not prove that **future PyYAML versions** will preserve current behaviour. PyYAML's emitter is deliberately stable but not formally specified. A version bump could in principle change a quoting decision.

The right response to all three is the same: replace dependence on a reference *implementation* with dependence on a specification *grammar*. v0.2.

---

*Working draft v0.1, CC BY 4.0. Comments via [GitHub Discussions](https://github.com/sk8ordie84/falsify/discussions/6) or `hello@studio-11.co`.*
