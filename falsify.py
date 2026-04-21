#!/usr/bin/env python3
"""Falsification Engine — pre-registration + CI for AI-agent claims."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import re
import socket
import subprocess
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
_RUN_TIMEOUT_S = 300
_EQUALS_EPSILON = 1e-9

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
        print(f"  claim: {c['metric']} {c['direction']} {c['threshold']}")
    return EXIT_PASS


def _load_locked_spec(
    claim_dir: Path,
) -> tuple[dict | None, dict | None, str]:
    """Return (spec, lock_data, error_message). On error, spec and lock are None."""
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not lock_path.exists():
        return None, None, (
            f"no locked spec at {lock_path} — "
            f"run `falsify lock {claim_dir.name}` first."
        )
    if not spec_path.exists():
        return None, None, f"{spec_path} not found."

    try:
        spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        return None, None, f"failed to parse {spec_path}: {e}"
    try:
        lock_data = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        return None, None, f"failed to parse {lock_path}: {e}"

    return spec, lock_data, ""


def _verify_lock_hash(spec: dict, lock_data: dict) -> bool:
    current_hash = hashlib.sha256(
        _canonicalize(spec).encode("utf-8")
    ).hexdigest()
    return lock_data.get("spec_hash") == current_hash


def _update_latest_pointer(claim_dir: Path, timestamp: str) -> None:
    latest = claim_dir / "latest_run"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    try:
        latest.symlink_to(Path("runs") / timestamp)
    except OSError:
        latest.write_text(timestamp + "\n")


def _resolve_latest_run(claim_dir: Path) -> Path | None:
    latest = claim_dir / "latest_run"
    if latest.is_symlink():
        target = latest.readlink()
        if target.is_absolute():
            return target
        return (claim_dir / target).resolve()
    if latest.is_file():
        ts = latest.read_text().strip()
        if ts:
            return claim_dir / "runs" / ts
    return None


def cmd_run(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec, lock_data, err = _load_locked_spec(claim_dir)
    if err:
        print(f"falsify run: {err}", file=sys.stderr)
        return EXIT_BAD_SPEC

    assert spec is not None and lock_data is not None
    if not _verify_lock_hash(spec, lock_data):
        print(
            f"falsify run: spec modified after lock. "
            f"Re-lock with `falsify lock {args.name} --force`.",
            file=sys.stderr,
        )
        return EXIT_HASH_MISMATCH

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    run_dir = claim_dir / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "spec.lock.json").write_text(
        (claim_dir / "spec.lock.json").read_text()
    )

    command = spec["experiment"]["command"]
    start = datetime.now(timezone.utc)
    timed_out = False
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=_RUN_TIMEOUT_S,
            cwd=str(Path.cwd()),
        )
        stdout, stderr, returncode = (
            result.stdout,
            result.stderr,
            result.returncode,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = (e.stderr or "") + f"\n[timeout after {_RUN_TIMEOUT_S}s]\n"
        returncode = 124
        timed_out = True
    end = datetime.now(timezone.utc)

    (run_dir / "stdout.txt").write_text(stdout)
    (run_dir / "stderr.txt").write_text(stderr)

    meta = {
        "command": command,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_s": round((end - start).total_seconds(), 6),
        "returncode": returncode,
        "timed_out": timed_out,
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
    }
    (run_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n"
    )

    _update_latest_pointer(claim_dir, timestamp)

    if returncode != 0:
        print(
            f"falsify run: command exited with code {returncode} "
            f"(run dir: {run_dir})",
            file=sys.stderr,
        )
        if stderr.strip():
            sys.stderr.write(stderr)
            if not stderr.endswith("\n"):
                sys.stderr.write("\n")
        return 1

    print(f"✓ Run {timestamp} ({meta['duration_s']:.2f}s)")
    return EXIT_PASS


def _criterion_holds(value: float, direction: str, threshold: float) -> bool:
    if direction == "above":
        return value > threshold
    if direction == "below":
        return value < threshold
    if direction == "equals":
        return abs(value - threshold) < _EQUALS_EPSILON
    raise ValueError(f"unknown direction: {direction!r}")


def cmd_verdict(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec_path = claim_dir / "spec.yaml"

    if not spec_path.exists():
        print(
            f"falsify verdict: {spec_path} not found — "
            f"run `falsify init {args.name}` first.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    run_dir = _resolve_latest_run(claim_dir)
    if run_dir is None or not run_dir.exists():
        print(
            f"falsify verdict: no runs — "
            f"run `falsify run {args.name}` first.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        print(f"falsify verdict: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    metric_fn_spec = spec["experiment"]["metric_fn"]
    if ":" not in metric_fn_spec:
        print(
            f"falsify verdict: metric_fn {metric_fn_spec!r} "
            f"must be in 'module:function' form",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    module_name, func_name = metric_fn_spec.split(":", 1)

    cwd_str = str(Path.cwd())
    if cwd_str not in sys.path:
        sys.path.insert(0, cwd_str)

    try:
        module = importlib.import_module(module_name)
        fn = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        print(
            f"falsify verdict: failed to load {metric_fn_spec}: {e}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        raw = fn(run_dir)
    except Exception as e:
        print(
            f"falsify verdict: metric_fn raised {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1

    sample_size: int | None = None
    if isinstance(raw, tuple) and len(raw) == 2:
        value_raw, sample_size = raw
    else:
        value_raw = raw
    if not isinstance(value_raw, (int, float)) or isinstance(value_raw, bool):
        print(
            f"falsify verdict: metric_fn must return a number "
            f"or (number, int). Got {type(value_raw).__name__}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    value = float(value_raw)

    min_n = spec["falsification"]["minimum_sample_size"]
    if sample_size is not None and sample_size < min_n:
        print(
            f"falsify verdict: minimum_sample_size not met "
            f"({sample_size} < {min_n})",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    criteria = spec["falsification"]["failure_criteria"]
    all_hold = True
    for c in criteria:
        if not _criterion_holds(value, c["direction"], c["threshold"]):
            all_hold = False

    head = criteria[0]
    verdict = "PASS" if all_hold else "FAIL"
    verdict_data = {
        "verdict": verdict,
        "observed_value": value,
        "threshold": head["threshold"],
        "direction": head["direction"],
        "metric": head["metric"],
        "run_ref": run_dir.name,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if sample_size is not None:
        verdict_data["sample_size"] = sample_size
    (claim_dir / "verdict.json").write_text(
        json.dumps(verdict_data, indent=2, sort_keys=True) + "\n"
    )

    print(f"Verdict: {verdict}")
    print(f"  observed {head['metric']} = {value}")
    print(f"  threshold: {head['direction']} {head['threshold']}")
    return EXIT_PASS if all_hold else EXIT_FAIL


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
