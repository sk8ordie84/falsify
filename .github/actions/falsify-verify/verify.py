#!/usr/bin/env python3
"""falsify-verify — GitHub Action entrypoint.

Walks the repository for PRML manifests matching MANIFEST_GLOB, verifies
each one's hash against its sidecar `.prml.sha256`, and writes summary
counts to GITHUB_OUTPUT and a job summary to GITHUB_STEP_SUMMARY.

Exit codes:
  0 — all manifests verified PASS, no tampering detected
  1 — at least one TAMPERED or FAIL detected (subject to fail-on-* inputs)

Inputs come from environment variables:
  MANIFEST_GLOB   — glob pattern (default '**/*.prml.yaml')
  FAIL_TAMPERED   — 'true'/'false' — exit 1 on hash mismatch
  FAIL_FALSIFIED  — 'true'/'false' — exit 1 on claim FAIL

This script does not import falsify; it independently recomputes the
canonical bytes + SHA-256 to keep the action lightweight. The
canonicalization is byte-equivalent to falsify._canonicalize.
"""
from __future__ import annotations

import glob
import hashlib
import os
import sys
from pathlib import Path

import yaml


def canonicalize(spec) -> str:
    """Reproduce falsify._canonicalize byte-for-byte."""
    return yaml.safe_dump(
        spec,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_output(key: str, value) -> None:
    """Write to GITHUB_OUTPUT for downstream steps."""
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def write_summary(lines: list[str]) -> None:
    """Append to GITHUB_STEP_SUMMARY for the job summary panel."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    pattern = os.environ.get("MANIFEST_GLOB", "**/*.prml.yaml")
    fail_tampered = os.environ.get("FAIL_TAMPERED", "true").lower() == "true"
    fail_falsified = os.environ.get("FAIL_FALSIFIED", "true").lower() == "true"

    repo_root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()

    manifests = sorted(repo_root.glob(pattern))
    if not manifests:
        print(f"falsify-verify: no manifests matched pattern '{pattern}' under {repo_root}")
        write_output("manifests-checked", 0)
        write_output("tampered-count", 0)
        write_output("falsified-count", 0)
        write_output("pass-count", 0)
        write_summary([
            "## falsify-verify",
            "",
            f"No PRML manifests found matching `{pattern}`.",
            "",
            "If you expected manifests to be checked, verify the `manifest-glob` input.",
        ])
        return 0

    tampered: list[tuple[Path, str, str]] = []
    falsified: list[Path] = []
    passed: list[Path] = []
    no_sidecar: list[Path] = []

    for manifest_path in manifests:
        rel = manifest_path.relative_to(repo_root)
        sidecar_path = manifest_path.with_suffix(".sha256")
        # sidecar convention: foo.prml.yaml -> foo.prml.sha256
        if not sidecar_path.exists():
            sidecar_path = manifest_path.parent / (manifest_path.stem + ".sha256")

        try:
            spec = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"::error file={rel}::Failed to parse YAML: {e}")
            tampered.append((manifest_path, "<parse-error>", "<parse-error>"))
            continue

        if not isinstance(spec, dict):
            print(f"::error file={rel}::Top-level YAML must be a mapping")
            tampered.append((manifest_path, "<not-a-mapping>", "<not-a-mapping>"))
            continue

        canonical = canonicalize(spec)
        recomputed = sha256_hex(canonical)

        if not sidecar_path.exists():
            print(f"::warning file={rel}::No sidecar hash found at {sidecar_path.name}; "
                  f"recorded hash for review: {recomputed[:16]}…")
            no_sidecar.append(manifest_path)
            continue

        sidecar_hash = sidecar_path.read_text(encoding="utf-8").strip().lower()

        if recomputed != sidecar_hash:
            print(f"::error file={rel}::TAMPERED — sidecar={sidecar_hash[:16]}… recomputed={recomputed[:16]}…")
            tampered.append((manifest_path, sidecar_hash, recomputed))
            continue

        # Hash matches — for v0.1 the action does not execute the claim itself,
        # only verifies hash integrity. Claim execution requires the dataset
        # and model, which are not in the manifest. v0.2 will add an optional
        # "execute" mode that calls falsify verify.
        passed.append(manifest_path)

    pass_count = len(passed)
    tampered_count = len(tampered)
    falsified_count = len(falsified)
    no_sidecar_count = len(no_sidecar)
    checked = len(manifests)

    write_output("manifests-checked", checked)
    write_output("tampered-count", tampered_count)
    write_output("falsified-count", falsified_count)
    write_output("pass-count", pass_count)

    summary = [
        "## falsify-verify",
        "",
        f"**Manifests checked:** {checked}",
        f"- ✅ Hash verified: {pass_count}",
        f"- ❌ Tampered: {tampered_count}",
        f"- ⚠️ Missing sidecar: {no_sidecar_count}",
        "",
    ]

    if tampered:
        summary.append("### Tampered manifests")
        summary.append("")
        summary.append("| Manifest | Sidecar hash (first 16) | Recomputed hash (first 16) |")
        summary.append("|---|---|---|")
        for m, sh, rh in tampered:
            summary.append(f"| `{m.relative_to(repo_root)}` | `{sh[:16]}` | `{rh[:16]}` |")
        summary.append("")

    if no_sidecar:
        summary.append("### Missing sidecar files")
        summary.append("")
        for m in no_sidecar:
            summary.append(f"- `{m.relative_to(repo_root)}` — no `.prml.sha256` companion file found")
        summary.append("")

    summary.append("---")
    summary.append("")
    summary.append("Verified against PRML v0.1 — https://spec.falsify.dev/v0.1")
    write_summary(summary)

    print("=" * 60)
    print(f"falsify-verify summary")
    print(f"  manifests checked: {checked}")
    print(f"  hash verified:     {pass_count}")
    print(f"  TAMPERED:          {tampered_count}")
    print(f"  missing sidecar:   {no_sidecar_count}")
    print("=" * 60)

    if fail_tampered and tampered_count > 0:
        return 1
    if fail_falsified and falsified_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
