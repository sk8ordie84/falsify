#!/usr/bin/env python3
"""Falsification Engine — pre-registration + CI for AI-agent claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

EXIT_PASS = 0
EXIT_FAIL = 10
EXIT_BAD_SPEC = 2
EXIT_HASH_MISMATCH = 3

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "examples" / "template.yaml"
SCHEMA_PATH = SCRIPT_DIR / "hypothesis.schema.yaml"
FALSIFY_DIR = Path(".falsify")

_FALLBACK_PLACEHOLDER_MARKERS = ("<", "TODO", "FIXME", "REPLACE_ME", "XXX")

_TYPE_CHECKERS: dict[str, Callable[[Any], bool]] = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "boolean": lambda v: isinstance(v, bool),
}


def cmd_init(args: argparse.Namespace) -> int:
    target_dir = FALSIFY_DIR / args.name
    spec_path = target_dir / "spec.yaml"

    if target_dir.exists() and not args.force:
        print(
            f"falsify init: {target_dir} already exists "
            f"(use --force to overwrite)",
            file=sys.stderr,
        )
        return 1

    if not TEMPLATE_PATH.exists():
        print(
            f"falsify init: template not found at {TEMPLATE_PATH}",
            file=sys.stderr,
        )
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(TEMPLATE_PATH.read_text())

    print(f"Created {spec_path}")
    print("Next: edit the spec, replace placeholders, then `falsify lock`.")
    return EXIT_PASS


def _stub(name: str) -> int:
    print(f"falsify {name}: not yet implemented", file=sys.stderr)
    return 1


def _load_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return yaml.safe_load(f)


def _collect_required_keys(node: dict) -> list[str]:
    top = node.get("required")
    if isinstance(top, list):
        return list(top)
    props = node.get("properties") or {}
    return [
        k for k, v in props.items()
        if isinstance(v, dict) and v.get("required") is True
    ]


def _validate_against_schema(
    value: Any,
    schema: dict,
    path: str,
    errors: list[str],
) -> None:
    ty = schema.get("type")
    if ty in _TYPE_CHECKERS and not _TYPE_CHECKERS[ty](value):
        errors.append(
            f"{path or '<root>'}: expected {ty}, got {type(value).__name__}"
        )
        return

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{path}: {value!r} not in {list(enum)}")

    pattern = schema.get("pattern")
    if pattern and isinstance(value, str) and not re.match(pattern, value):
        errors.append(f"{path}: {value!r} does not match pattern {pattern!r}")

    minimum = schema.get("minimum")
    if (
        minimum is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < minimum
    ):
        errors.append(f"{path}: must be >= {minimum} (got {value})")

    if ty == "object" and isinstance(value, dict):
        for key in _collect_required_keys(schema):
            if key not in value:
                prefix = f"{path}." if path else ""
                errors.append(f"{prefix}{key}: missing required field")
        props = schema.get("properties") or {}
        for key, sub in value.items():
            if key in props and isinstance(props[key], dict):
                sub_path = f"{path}.{key}" if path else key
                _validate_against_schema(sub, props[key], sub_path, errors)

    if ty == "array" and isinstance(value, list):
        min_items = schema.get("min_items")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(
                f"{path}: must have at least {min_items} item(s) (got {len(value)})"
            )
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _validate_against_schema(
                    item, items_schema, f"{path}[{i}]", errors
                )


def _find_placeholders(
    value: Any,
    markers: tuple[str, ...],
    path: str = "",
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            sub = f"{path}.{k}" if path else k
            found.extend(_find_placeholders(v, markers, sub))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found.extend(_find_placeholders(item, markers, f"{path}[{i}]"))
    elif isinstance(value, str):
        for marker in markers:
            if marker in value:
                found.append((path, value))
                break
    return found


def _canonicalize(spec: Any) -> str:
    """Render a YAML tree in a stable form suitable for hashing."""
    return yaml.safe_dump(
        spec,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def cmd_lock(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not spec_path.exists():
        print(
            f"falsify lock: {spec_path} not found — "
            f"run `falsify init {args.name}` first",
            file=sys.stderr,
        )
        return 1

    try:
        raw_text = spec_path.read_text()
        spec = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        print(f"falsify lock: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    if not isinstance(spec, dict):
        print(
            f"falsify lock: {spec_path} must be a YAML mapping at the top level",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    schema = _load_schema()

    markers_raw = schema.get("placeholder_markers") or _FALLBACK_PLACEHOLDER_MARKERS
    markers = tuple(str(m) for m in markers_raw)
    placeholders = _find_placeholders(spec, markers)
    if placeholders:
        print(
            f"falsify lock: {spec_path} still contains placeholder values:",
            file=sys.stderr,
        )
        for field_path, val in placeholders:
            print(f"  - {field_path}: {val!r}", file=sys.stderr)
        print(
            "Replace placeholders with real values, then re-run `falsify lock`.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    errors: list[str] = []
    _validate_against_schema(spec, schema, "", errors)
    if errors:
        print(f"falsify lock: invalid spec {spec_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return EXIT_BAD_SPEC

    canonical = _canonicalize(spec)
    spec_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    if lock_path.exists() and not args.force:
        try:
            existing = json.loads(lock_path.read_text())
        except json.JSONDecodeError:
            existing = None
        if isinstance(existing, dict):
            existing_hash = existing.get("spec_hash")
            if isinstance(existing_hash, str):
                if existing_hash == spec_hash:
                    print(
                        f"Already locked {args.name} @ {spec_hash[:12]} "
                        f"— spec unchanged."
                    )
                    return EXIT_PASS
                print(
                    f"falsify lock: {spec_path} has been modified since last lock "
                    f"(was {existing_hash[:12]}, now {spec_hash[:12]}). "
                    f"Use --force to relock.",
                    file=sys.stderr,
                )
                return EXIT_HASH_MISMATCH

    lock_data = {
        "spec_hash": spec_hash,
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "canonical_spec_yaml": canonical,
    }
    lock_path.write_text(
        json.dumps(lock_data, indent=2, sort_keys=True) + "\n"
    )

    print(f"✓ Locked {args.name} @ {spec_hash[:12]}")
    for c in spec["falsification"]["failure_criteria"]:
        print(f"  falsifies if {c['metric']} {c['direction']} {c['threshold']}")
    return EXIT_PASS


def cmd_run(args: argparse.Namespace) -> int:
    return _stub("run")


def cmd_verdict(args: argparse.Namespace) -> int:
    return _stub("verdict")


def cmd_guard(args: argparse.Namespace) -> int:
    return _stub("guard")


def cmd_list(args: argparse.Namespace) -> int:
    return _stub("list")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="falsify",
        description="Pre-registration + CI for AI-agent claims.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Scaffold a new claim spec")
    p_init.add_argument(
        "name",
        help="Claim name (used as directory under .falsify/)",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing claim directory",
    )
    p_init.set_defaults(func=cmd_init)

    p_lock = sub.add_parser("lock", help="Hash and freeze a claim (pre-register)")
    p_lock.add_argument("name", help="Claim name")
    p_lock.add_argument(
        "--force",
        action="store_true",
        help="Relock even if the spec hash has changed since last lock",
    )
    p_lock.set_defaults(func=cmd_lock)

    p_run = sub.add_parser("run", help="Evaluate a locked claim against current state")
    p_run.add_argument("name", help="Claim name")
    p_run.set_defaults(func=cmd_run)

    p_verdict = sub.add_parser("verdict", help="Report PASS/FAIL for a claim")
    p_verdict.add_argument("name", help="Claim name")
    p_verdict.set_defaults(func=cmd_verdict)

    p_guard = sub.add_parser(
        "guard",
        help="CI wrapper — exit non-zero when any locked claim is falsified",
    )
    p_guard.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command to wrap (everything after -- is passed through)",
    )
    p_guard.set_defaults(func=cmd_guard)

    p_list = sub.add_parser("list", help="List all claims with their status")
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
