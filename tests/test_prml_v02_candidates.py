"""Conformance tests for PRML v0.2 candidate test vectors (TV-013 → TV-018).

These vectors live at `spec/v0.2/test-vectors-candidates.json` and exercise
edge cases not covered in the normative v0.1 suite (CJK Unicode, long notes,
all-optional-fields, 3-link amendment chain, strict-less-than comparator,
small-magnitude float). They are *candidates* for promotion to v0.2 normative
status when the spec freeze lands on 2026-05-22.

Because the candidate vectors use the v0.1 grammar (PyYAML safe_dump
canonicalization), the Python reference implementation must reproduce all six
byte-for-byte. Cross-implementation tests (JS, Go) live in their respective
`impl/<lang>/` directories and are run via the test-vectors subcommand.

If any test here fails, either:
  (a) the canonicalizer in falsify._canonicalize has changed in a way that
      breaks v0.1 contract for these edge cases — investigate, then either
      revert or update the candidate vectors via
      `python3 spec/v0.2/generate-candidates.py` (the latter is appropriate
      ONLY if the change is intended for v0.2), OR
  (b) the candidate vector definitions in `spec/v0.2/generate-candidates.py`
      have drifted from the JSON output — re-run the generator.

Note: TV-018 surfaces a documented cross-implementation divergence in
small-magnitude float rendering (Finding 4 in the portability analysis).
The Python reference passes 6/6 here; JS and Go pass 5/6 against the same
file. That asymmetry is by design; TV-018 will be re-shaped or replaced
when v0.2 grammar lands always-quoted-numbers (RFC-Q-04).
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_PATH = REPO_ROOT / "spec" / "v0.2" / "test-vectors-candidates.json"

sys.path.insert(0, str(REPO_ROOT))
import falsify  # noqa: E402


def _load_candidates():
    if not CANDIDATES_PATH.exists():
        return None
    return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))


CANDIDATES = _load_candidates() or []
EXPECTED_VECTOR_COUNT = 6
EXPECTED_IDS = {f"TV-{i:03d}" for i in range(13, 19)}  # TV-013 .. TV-018


class PRMLv02CandidateTests(unittest.TestCase):
    """Dynamically populated per vector — see bottom of file."""

    @classmethod
    def setUpClass(cls):
        if not CANDIDATES:
            raise unittest.SkipTest(
                f"v0.2 candidate vectors not generated yet at {CANDIDATES_PATH}. "
                f"Run `python3 spec/v0.2/generate-candidates.py` to produce them."
            )

    def test_candidate_count(self):
        """v0.2 candidate suite ships exactly 6 vectors (TV-013 → TV-018)."""
        self.assertEqual(
            len(CANDIDATES),
            EXPECTED_VECTOR_COUNT,
            f"Expected {EXPECTED_VECTOR_COUNT} v0.2 candidates, got {len(CANDIDATES)}",
        )

    def test_candidate_ids_match(self):
        """The candidate IDs MUST be exactly TV-013 through TV-018."""
        actual_ids = {v["id"] for v in CANDIDATES}
        self.assertEqual(
            actual_ids,
            EXPECTED_IDS,
            f"Candidate ID mismatch. Expected {sorted(EXPECTED_IDS)}, "
            f"got {sorted(actual_ids)}",
        )

    def test_chain_linkage_tv016(self):
        """TV-016's prior_hash MUST equal the documented intermediate amendment_1 hash."""
        by_id = {v["id"]: v for v in CANDIDATES}
        tv016 = by_id["TV-016"]
        self.assertIn(
            "intermediate_amendment_1",
            tv016,
            "TV-016 must document its intermediate amendment_1 (the chain link "
            "between TV-001 and itself).",
        )
        intermediate = tv016["intermediate_amendment_1"]
        self.assertEqual(
            tv016["input"]["prior_hash"],
            intermediate["hash"],
            "TV-016.input.prior_hash MUST equal the intermediate amendment_1 "
            "hash (chain length 3: TV-001 → amendment_1 → TV-016).",
        )

    def test_strict_less_than_coverage(self):
        """TV-017 fills the comparator coverage gap — < operator is exercised."""
        by_id = {v["id"]: v for v in CANDIDATES}
        self.assertEqual(
            by_id["TV-017"]["input"]["comparator"],
            "<",
            "TV-017 must use strict-less-than (<) — fills the coverage gap "
            "left by the v0.1 normative suite (which uses >=, ==, >, <=).",
        )

    def test_cjk_unicode_distinct_from_tv005(self):
        """TV-013 producer.id is CJK; v0.1 TV-005 producer.id is Latin Extended."""
        by_id = {v["id"]: v for v in CANDIDATES}
        producer_id = by_id["TV-013"]["input"]["producer"]["id"]
        # CJK code points are >= 0x4E00. Quick test: at least one char
        # in producer.id is in the CJK range.
        self.assertTrue(
            any(ord(c) >= 0x4E00 for c in producer_id),
            f"TV-013 producer.id ({producer_id!r}) should contain CJK "
            "characters to distinguish from v0.1 TV-005 (Latin Extended).",
        )


def _make_canonical_test(vector):
    def test(self):
        produced = falsify._canonicalize(vector["input"])
        self.assertEqual(
            produced,
            vector["canonical"],
            f"{vector['id']} canonical bytes diverged from generated form.\n"
            f"  Expected length: {len(vector['canonical'])} chars\n"
            f"  Produced length: {len(produced)} chars\n"
            f"  Either the Python canonicalizer has drifted, or the candidate "
            f"vectors must be regenerated.",
        )

    test.__doc__ = f"{vector['id']}: canonical bytes match generated form"
    return test


def _make_hash_test(vector):
    def test(self):
        canonical = falsify._canonicalize(vector["input"])
        produced_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(
            produced_hash,
            vector["hash"],
            f"{vector['id']} hash mismatch.\n"
            f"  Expected: {vector['hash']}\n"
            f"  Produced: {produced_hash}\n"
            f"  This indicates either a canonicalizer drift or stale vectors.",
        )

    test.__doc__ = f"{vector['id']}: SHA-256 of canonical bytes matches generated form"
    return test


# Dynamically attach one canonical-bytes test and one hash test per vector
for _v in CANDIDATES:
    _vid = _v["id"].replace("-", "_").lower()
    setattr(
        PRMLv02CandidateTests,
        f"test_canonical_bytes_{_vid}",
        _make_canonical_test(_v),
    )
    setattr(
        PRMLv02CandidateTests,
        f"test_hash_{_vid}",
        _make_hash_test(_v),
    )


if __name__ == "__main__":
    unittest.main()
