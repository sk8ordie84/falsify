#!/usr/bin/env python3
"""Falsification Engine — pre-registration + CI for AI-agent claims."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import html as html_module
import importlib
import json
import platform
import re
import shutil
import socket
import string
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

__version__ = "0.1.0"

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

_AFFIRMATIVE_KEYWORDS = (
    "confirmed",
    "proven",
    "validated",
    "works",
    "successful",
)

EXIT_GUARD_VIOLATION = 11

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
        "canonical_yaml": canonical,
    }
    lock_path.write_text(
        json.dumps(lock_data, indent=2, sort_keys=True) + "\n"
    )

    print(f"✓ Locked {args.name} @ {spec_hash[:12]}")
    for c in spec["falsification"]["failure_criteria"]:
        print(f"  claim: {c['metric']} {c['direction']} {c['threshold']}")
    return EXIT_PASS


def _render_unified_diff(
    a_text: str, b_text: str, label_a: str, label_b: str
) -> None:
    """Write a colored unified diff to stdout.

    ANSI escapes are emitted only when stdout is a TTY.
    """
    use_color = sys.stdout.isatty()
    for line in difflib.unified_diff(
        a_text.splitlines(keepends=True),
        b_text.splitlines(keepends=True),
        fromfile=label_a,
        tofile=label_b,
    ):
        if use_color:
            if line.startswith("+++") or line.startswith("---"):
                line = "\x1b[1m" + line + "\x1b[0m"
            elif line.startswith("+"):
                line = "\x1b[32m" + line + "\x1b[0m"
            elif line.startswith("-"):
                line = "\x1b[31m" + line + "\x1b[0m"
            elif line.startswith("@@"):
                line = "\x1b[36m" + line + "\x1b[0m"
        sys.stdout.write(line)


def _canonical_and_hash(spec: Any) -> tuple[str, str]:
    canonical = _canonicalize(spec)
    return canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _diff_file_vs_file(path_a: Path, path_b: Path) -> int:
    for p in (path_a, path_b):
        if not p.exists():
            print(f"falsify diff: {p} not found", file=sys.stderr)
            return EXIT_BAD_SPEC
    try:
        spec_a = yaml.safe_load(path_a.read_text())
        spec_b = yaml.safe_load(path_b.read_text())
    except yaml.YAMLError as e:
        print(f"falsify diff: YAML parse error: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    yaml_a, hash_a = _canonical_and_hash(spec_a)
    yaml_b, hash_b = _canonical_and_hash(spec_b)

    if yaml_a == yaml_b:
        print(f"Files are canonically identical @ {hash_a[:12]}")
        return EXIT_PASS

    _render_unified_diff(
        yaml_a, yaml_b,
        f"{path_a}@{hash_a[:12]}",
        f"{path_b}@{hash_b[:12]}",
    )
    return EXIT_HASH_MISMATCH


def _diff_lock_vs_file(name: str) -> int:
    claim_dir = FALSIFY_DIR / name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not spec_path.exists():
        print(
            f"falsify diff: {spec_path} not found — "
            f"run `falsify init {name}` first",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    if not lock_path.exists():
        print(
            f"falsify diff: no lock at {lock_path} — "
            f"run `falsify lock {name}` first",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        lock_data = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"falsify diff: failed to read {lock_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    locked_hash = lock_data.get("spec_hash") if isinstance(lock_data, dict) else None
    locked_yaml = (
        lock_data.get("canonical_yaml") if isinstance(lock_data, dict) else None
    )

    try:
        current_spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        print(f"falsify diff: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    current_yaml, current_hash = _canonical_and_hash(current_spec)

    if not isinstance(locked_yaml, str):
        if isinstance(locked_hash, str) and locked_hash == current_hash:
            print(
                f"Lock has no canonical_yaml field (legacy format). "
                f"Spec is unchanged @ {current_hash[:12]}; nothing to diff."
            )
            print(
                f"Re-lock with `falsify lock {name} --force` to populate "
                f"canonical_yaml for future diffs.",
            )
            return EXIT_PASS
        print(
            f"falsify diff: legacy lock — no canonical_yaml stored and "
            f"spec has drifted. Re-lock with "
            f"`falsify lock {name} --force` to enable diff.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    locked_short = (locked_hash or "?")[:12]
    current_short = current_hash[:12]

    if locked_yaml == current_yaml:
        print(f"Lock and current spec are identical @ {current_short}")
        return EXIT_PASS

    _render_unified_diff(
        locked_yaml,
        current_yaml,
        f"locked@{locked_short}",
        f"current@{current_short}",
    )
    return EXIT_HASH_MISMATCH


def cmd_diff(args: argparse.Namespace) -> int:
    if args.file_vs_file:
        path_a, path_b = args.file_vs_file
        return _diff_file_vs_file(Path(path_a), Path(path_b))
    if not args.name:
        print(
            "falsify diff: name is required for lock-vs-file mode "
            "(or pass --file-vs-file A B)",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    return _diff_lock_vs_file(args.name)


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
    criteria = spec["falsification"]["failure_criteria"]
    head = criteria[0]

    if sample_size is not None and sample_size < min_n:
        inconclusive = {
            "verdict": "INCONCLUSIVE",
            "reason": "minimum_sample_size_not_met",
            "observed_value": value,
            "sample_size": sample_size,
            "minimum_sample_size": min_n,
            "metric": head["metric"],
            "direction": head["direction"],
            "threshold": head["threshold"],
            "run_ref": run_dir.name,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        (claim_dir / "verdict.json").write_text(
            json.dumps(inconclusive, indent=2, sort_keys=True) + "\n"
        )
        print(
            f"falsify verdict: minimum_sample_size not met "
            f"({sample_size} < {min_n})",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    all_hold = True
    for c in criteria:
        if not _criterion_holds(value, c["direction"], c["threshold"]):
            all_hold = False

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


def _normalize_text(s: str) -> str:
    s = s.lower()
    s = s.translate(str.maketrans("", "", string.punctuation))
    return " ".join(s.split())


def _claim_text_matches(claim_norm: str, input_norm: str) -> bool:
    if not claim_norm or not input_norm:
        return False
    if claim_norm in input_norm or input_norm in claim_norm:
        return True
    claim_tokens = {w for w in claim_norm.split() if len(w) >= 5}
    input_tokens = {w for w in input_norm.split() if len(w) >= 5}
    return len(claim_tokens & input_tokens) >= 2


def _derive_claim_state(claim_dir: Path) -> tuple[str, dict | None]:
    """Return (state, verdict_data_or_None).

    States: PASS | FAIL | INCONCLUSIVE | STALE | UNRUN | UNLOCKED | UNKNOWN.
    """
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"
    verdict_path = claim_dir / "verdict.json"

    if not spec_path.exists():
        return "UNKNOWN", None
    if not lock_path.exists():
        return "UNLOCKED", None

    try:
        spec = yaml.safe_load(spec_path.read_text())
        current_hash = hashlib.sha256(
            _canonicalize(spec).encode("utf-8")
        ).hexdigest()
        lock_data = json.loads(lock_path.read_text())
    except (yaml.YAMLError, json.JSONDecodeError, OSError):
        return "UNKNOWN", None

    if lock_data.get("spec_hash") != current_hash:
        return "STALE", None

    if not verdict_path.exists():
        return "UNRUN", None

    try:
        verdict_data = json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN", None

    if not isinstance(verdict_data, dict):
        return "UNKNOWN", None

    v = verdict_data.get("verdict")
    if v in ("PASS", "FAIL", "INCONCLUSIVE"):
        return v, verdict_data
    return "UNKNOWN", verdict_data


def _read_claim_text(claim_dir: Path) -> str | None:
    spec_path = claim_dir / "spec.yaml"
    try:
        spec = yaml.safe_load(spec_path.read_text())
    except (yaml.YAMLError, OSError):
        return None
    if isinstance(spec, dict):
        claim = spec.get("claim")
        if isinstance(claim, str):
            return claim
    return None


def _iter_claim_dirs(base: Path):
    if not base.exists():
        return
    for claim_dir in sorted(base.iterdir()):
        if not claim_dir.is_dir():
            continue
        if not (claim_dir / "spec.yaml").exists():
            continue
        yield claim_dir


def _guard_text_mode(input_text: str) -> int:
    input_norm = _normalize_text(input_text)
    input_tokens = set(input_norm.split())
    if not any(kw in input_tokens for kw in _AFFIRMATIVE_KEYWORDS):
        return EXIT_PASS

    violations: list[tuple[str, str, str]] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        state, _ = _derive_claim_state(claim_dir)
        if state == "PASS":
            continue
        if state not in ("FAIL", "INCONCLUSIVE"):
            continue
        claim_text = _read_claim_text(claim_dir)
        if claim_text is None:
            continue
        if _claim_text_matches(_normalize_text(claim_text), input_norm):
            reason = state
            if state == "INCONCLUSIVE":
                reason = "INCONCLUSIVE (not yet proven)"
            violations.append((claim_dir.name, reason, claim_text))

    if not violations:
        return EXIT_PASS

    print("BLOCKED: claim contradicts logged verdict(s):", file=sys.stderr)
    for name, reason, claim_text in violations:
        print(f"  - {name}: {reason} — {claim_text}", file=sys.stderr)
    return EXIT_GUARD_VIOLATION


def _guard_scan_mode() -> int:
    problems: list[tuple[str, str]] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        state, _ = _derive_claim_state(claim_dir)
        if state in ("FAIL", "STALE"):
            problems.append((claim_dir.name, state))

    if not problems:
        return EXIT_PASS

    print("falsify guard: logged issues:", file=sys.stderr)
    for name, state in problems:
        print(f"  - {name}: {state}", file=sys.stderr)
    return EXIT_FAIL


def _guard_wrap_mode(cmd_tokens: list[str]) -> int:
    if not cmd_tokens:
        print("falsify guard: no command to wrap after `--`", file=sys.stderr)
        return 1
    try:
        result = subprocess.run(cmd_tokens)
    except FileNotFoundError as e:
        print(f"falsify guard: {e}", file=sys.stderr)
        return 127
    if result.returncode != 0:
        return result.returncode
    return _guard_scan_mode()


def cmd_guard(args: argparse.Namespace) -> int:
    tokens: list[str] = list(args.rest)
    if tokens and tokens[0] == "--":
        return _guard_wrap_mode(tokens[1:])
    if tokens:
        return _guard_text_mode(" ".join(tokens))
    return _guard_scan_mode()


def _gather_claims(base: Path) -> list[dict]:
    if not base.exists():
        return []
    claims: list[dict] = []
    for claim_dir in sorted(base.iterdir()):
        if not claim_dir.is_dir():
            continue
        if not (claim_dir / "spec.yaml").exists():
            continue

        spec_hash: str | None = None
        lock_path = claim_dir / "spec.lock.json"
        if lock_path.exists():
            try:
                lock_data = json.loads(lock_path.read_text())
                h = lock_data.get("spec_hash")
                if isinstance(h, str):
                    spec_hash = h
            except (OSError, json.JSONDecodeError):
                pass

        last_run: str | None = None
        run_dir = _resolve_latest_run(claim_dir)
        if run_dir is not None and run_dir.exists():
            last_run = run_dir.name

        verdict_str: str | None = None
        observed: float | None = None
        verdict_path = claim_dir / "verdict.json"
        if verdict_path.exists():
            try:
                v = json.loads(verdict_path.read_text())
                if isinstance(v, dict):
                    if isinstance(v.get("verdict"), str):
                        verdict_str = v["verdict"]
                    if isinstance(v.get("observed_value"), (int, float)):
                        observed = float(v["observed_value"])
            except (OSError, json.JSONDecodeError):
                pass

        claims.append({
            "name": claim_dir.name,
            "locked": spec_hash is not None,
            "spec_hash": spec_hash,
            "last_run": last_run,
            "verdict": verdict_str,
            "observed_value": observed,
        })
    return claims


_STATS_STALE_DAYS = 7


def _read_metric_name_from_spec(claim_dir: Path) -> str | None:
    try:
        spec = yaml.safe_load((claim_dir / "spec.yaml").read_text())
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(spec, dict):
        return None
    criteria = spec.get("falsification", {}).get("failure_criteria") or []
    if criteria and isinstance(criteria[0], dict):
        m = criteria[0].get("metric")
        if isinstance(m, str):
            return m
    return None


def _gather_stats_rows(base: Path, name_filter: str | None) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for claim_dir in _iter_claim_dirs(base):
        if name_filter and name_filter not in claim_dir.name:
            continue

        state, verdict_data = _derive_claim_state(claim_dir)

        metric: str | None = None
        value: float | None = None
        threshold: float | None = None
        n: int | None = None
        last_run_iso: str | None = None
        age_days: int | None = None

        if isinstance(verdict_data, dict):
            v_metric = verdict_data.get("metric")
            if isinstance(v_metric, str):
                metric = v_metric
            v_value = verdict_data.get("observed_value")
            if isinstance(v_value, (int, float)) and not isinstance(v_value, bool):
                value = float(v_value)
            v_threshold = verdict_data.get("threshold")
            if isinstance(v_threshold, (int, float)) and not isinstance(
                v_threshold, bool
            ):
                threshold = float(v_threshold)
            v_n = verdict_data.get("sample_size")
            if isinstance(v_n, int) and not isinstance(v_n, bool):
                n = v_n
            checked_at = verdict_data.get("checked_at")
            if isinstance(checked_at, str):
                last_run_iso = checked_at
                try:
                    t = datetime.fromisoformat(checked_at)
                    age_days = (now - t).days
                except ValueError:
                    pass

        if metric is None:
            metric = _read_metric_name_from_spec(claim_dir)

        if (
            state in ("PASS", "FAIL", "INCONCLUSIVE")
            and age_days is not None
            and age_days > _STATS_STALE_DAYS
        ):
            state = "STALE"

        rows.append({
            "name": claim_dir.name,
            "state": state,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "n": n,
            "last_run_iso": last_run_iso,
            "age_days": age_days,
        })
    return rows


_HTML_STATS_STYLE = """\
* { box-sizing: border-box; }
:root {
  --bg: #ffffff;
  --surface: #f6f8fa;
  --fg: #1f2328;
  --muted: #656d76;
  --border: #d1d9e0;
  --pass: #2ea043;
  --fail: #da3633;
  --inconclusive: #d29922;
  --stale: #6e7681;
  --unrun: #8b949e;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --fg: #e6edf3;
    --muted: #8b949e;
    --border: #30363d;
  }
}
body {
  margin: 0;
  padding: 2rem;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  line-height: 1.5;
}
header.page, section.summary, section.cards, footer.page {
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}
header.page { margin-bottom: 1.5rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.5rem; }
.subtitle { color: var(--muted); margin: 0; font-size: 0.9rem; }
section.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.pill {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  background: var(--surface);
  border: 1px solid var(--border);
  font-size: 0.85rem;
  font-weight: 500;
}
.pill.state-PASS { border-color: var(--pass); color: var(--pass); }
.pill.state-FAIL { border-color: var(--fail); color: var(--fail); }
.pill.state-INCONCLUSIVE { border-color: var(--inconclusive); color: var(--inconclusive); }
.pill.state-STALE { border-color: var(--stale); color: var(--stale); }
.pill.state-UNRUN { border-color: var(--unrun); color: var(--unrun); }
section.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
article.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 6px;
  padding: 1rem;
}
article.card.state-PASS { border-left-color: var(--pass); }
article.card.state-FAIL { border-left-color: var(--fail); }
article.card.state-INCONCLUSIVE { border-left-color: var(--inconclusive); }
article.card.state-STALE { border-left-color: var(--stale); }
article.card.state-UNRUN { border-left-color: var(--unrun); }
article.card > header.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
article.card h2 { margin: 0; font-size: 1.05rem; word-break: break-word; }
.badge {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  color: #ffffff;
  white-space: nowrap;
}
.badge.state-PASS { background: var(--pass); }
.badge.state-FAIL { background: var(--fail); }
.badge.state-INCONCLUSIVE { background: var(--inconclusive); }
.badge.state-STALE { background: var(--stale); }
.badge.state-UNRUN { background: var(--unrun); }
p.claim {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0.25rem 0 0.75rem;
}
dl {
  margin: 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 0.75rem;
  row-gap: 0.2rem;
  font-size: 0.85rem;
}
dt { color: var(--muted); }
dd { margin: 0; overflow-wrap: anywhere; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85em;
}
footer.page {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
footer.page a { color: inherit; }
.empty {
  color: var(--muted);
  font-style: italic;
}
"""


def _truncate_claim(s: str, limit: int = 200) -> str:
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + "…"


def _age_phrase(age_days: int | None) -> str:
    if age_days is None:
        return "—"
    if age_days <= 0:
        return "today"
    if age_days == 1:
        return "1 day ago"
    return f"{age_days} days ago"


def _enrich_html_row(row: dict, base: Path) -> dict:
    name = row["name"]
    claim_dir = base / name
    claim_text = _read_claim_text(claim_dir) or ""

    spec_hash = ""
    lock_path = claim_dir / "spec.lock.json"
    if lock_path.exists():
        try:
            lock_data = json.loads(lock_path.read_text())
            h = lock_data.get("spec_hash")
            if isinstance(h, str):
                spec_hash = h
        except (OSError, json.JSONDecodeError):
            pass

    direction: str | None = None
    verdict_path = claim_dir / "verdict.json"
    if verdict_path.exists():
        try:
            vd = json.loads(verdict_path.read_text())
            if isinstance(vd, dict):
                d = vd.get("direction")
                if isinstance(d, str):
                    direction = d
        except (OSError, json.JSONDecodeError):
            pass

    return {
        **row,
        "claim_text": claim_text,
        "spec_hash": spec_hash,
        "direction": direction,
    }


def _render_stats_html(rows: list[dict], generated_at_iso: str) -> str:
    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        state = r["state"]
        key = state if state in counts else "UNRUN"
        counts[key] += 1

    pills_html = "".join(
        f'      <span class="pill state-{state}">{state}: {count}</span>\n'
        for state, count in counts.items()
    )

    def _cell(value: Any, *, mono: bool = True) -> str:
        if value is None or value == "":
            return "—"
        escaped = html_module.escape(str(value))
        return f"<code>{escaped}</code>" if mono else escaped

    if not rows:
        cards_body = '      <p class="empty">No specs yet — run `falsify init &lt;name&gt;` to start.</p>\n'
    else:
        card_parts = []
        for r in rows:
            name_esc = html_module.escape(r["name"])
            state = r["state"]
            state_esc = html_module.escape(state)
            claim_esc = html_module.escape(_truncate_claim(r.get("claim_text") or ""))
            metric_cell = _cell(r.get("metric"))
            value_cell = _cell(r.get("value"))
            threshold = r.get("threshold")
            direction = r.get("direction")
            if threshold is not None and direction:
                threshold_cell = _cell(f"{direction} {threshold}")
            elif threshold is not None:
                threshold_cell = _cell(threshold)
            else:
                threshold_cell = "—"
            n_cell = _cell(r.get("n"))
            last_run_cell = _cell(r.get("last_run_iso"), mono=False)
            age_cell = html_module.escape(_age_phrase(r.get("age_days")))
            hash_short = (r.get("spec_hash") or "")[:8]
            hash_cell = _cell(hash_short) if hash_short else "—"

            card_parts.append(
                f'      <article class="card state-{state_esc}">\n'
                f'        <header class="card-head">\n'
                f'          <h2>{name_esc}</h2>\n'
                f'          <span class="badge state-{state_esc}">{state_esc}</span>\n'
                f'        </header>\n'
                f'        <p class="claim">{claim_esc if claim_esc else "—"}</p>\n'
                f'        <dl>\n'
                f'          <dt>metric</dt><dd>{metric_cell}</dd>\n'
                f'          <dt>observed</dt><dd>{value_cell}</dd>\n'
                f'          <dt>threshold</dt><dd>{threshold_cell}</dd>\n'
                f'          <dt>n</dt><dd>{n_cell}</dd>\n'
                f'          <dt>last run</dt><dd>{last_run_cell} ({age_cell})</dd>\n'
                f'          <dt>hash</dt><dd>{hash_cell}</dd>\n'
                f'        </dl>\n'
                f'      </article>\n'
            )
        cards_body = "".join(card_parts)

    total = len(rows)
    generated_esc = html_module.escape(generated_at_iso)

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Falsification Engine — Verdict Dashboard</title>\n'
        f'<style>\n{_HTML_STATS_STYLE}</style>\n'
        '</head>\n'
        '<body>\n'
        '  <header class="page">\n'
        '    <h1>Falsification Engine — Verdict Dashboard</h1>\n'
        f'    <p class="subtitle">{total} spec(s) · Generated {generated_esc}</p>\n'
        '  </header>\n'
        '  <section class="summary">\n'
        f'{pills_html}'
        '  </section>\n'
        '  <section class="cards">\n'
        f'{cards_body}'
        '  </section>\n'
        '  <footer class="page">\n'
        '    <p>Generated by <code>falsify stats --html</code> · '
        '<a href="https://github.com/&lt;USER&gt;/falsify-hackathon">falsify-hackathon</a></p>\n'
        '  </footer>\n'
        '</body>\n'
        '</html>\n'
    )


def _write_stats_output(text: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(text)
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def cmd_stats(args: argparse.Namespace) -> int:
    rows = _gather_stats_rows(FALSIFY_DIR, args.name)

    if getattr(args, "html", False):
        enriched = [_enrich_html_row(r, FALSIFY_DIR) for r in rows]
        html_text = _render_stats_html(
            enriched, datetime.now(timezone.utc).isoformat()
        )
        _write_stats_output(html_text, getattr(args, "output", None))
        return EXIT_PASS

    if args.json:
        payload = json.dumps(rows, indent=2, sort_keys=True)
        _write_stats_output(payload, getattr(args, "output", None))
        return EXIT_PASS

    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        s = r["state"]
        if s in counts:
            counts[s] += 1
        else:
            counts["UNRUN"] += 1

    lines: list[str] = []
    if rows:
        headers = ["NAME", "STATE", "METRIC", "VALUE", "THRESHOLD", "N", "AGE(d)"]
        table: list[list[str]] = [headers]
        for r in rows:
            table.append([
                r["name"],
                r["state"],
                r["metric"] or "-",
                f"{r['value']}" if r["value"] is not None else "-",
                f"{r['threshold']}" if r["threshold"] is not None else "-",
                f"{r['n']}" if r["n"] is not None else "-",
                f"{r['age_days']}" if r["age_days"] is not None else "-",
            ])
        widths = [max(len(row[i]) for row in table) for i in range(len(headers))]
        for row in table:
            lines.append(
                "  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip()
            )
        lines.append("")

    lines.append(
        f"{len(rows)} specs: "
        f"{counts['PASS']} PASS, "
        f"{counts['FAIL']} FAIL, "
        f"{counts['INCONCLUSIVE']} INCONCLUSIVE, "
        f"{counts['STALE']} STALE, "
        f"{counts['UNRUN']} UNRUN"
    )
    output_path = getattr(args, "output", None)
    if output_path:
        Path(output_path).write_text("\n".join(lines) + "\n")
    else:
        for line in lines:
            print(line)
    return EXIT_PASS


def cmd_list(args: argparse.Namespace) -> int:
    claims = _gather_claims(FALSIFY_DIR)

    if args.json:
        print(json.dumps(claims, indent=2, sort_keys=True))
        return EXIT_PASS

    if not claims:
        print("No hypotheses yet. Run `falsify init <name>` to create one.")
        return EXIT_PASS

    headers = ["NAME", "LOCKED", "LAST RUN", "VERDICT", "OBSERVED"]
    rows: list[list[str]] = [headers]
    for c in claims:
        rows.append([
            c["name"],
            c["spec_hash"][:12] if c["spec_hash"] else "-",
            c["last_run"] or "-",
            c["verdict"] or "-",
            f"{c['observed_value']}" if c["observed_value"] is not None else "-",
        ])

    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip())

    return EXIT_PASS


def _git_repo_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hook_install(args: argparse.Namespace) -> int:
    repo_root = _git_repo_root()
    if repo_root is None:
        print(
            "falsify hook install: not in a git repository (or git is "
            "not installed)",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    source = repo_root / "hooks" / "commit-msg"
    if not source.exists():
        print(
            f"falsify hook install: source hook missing at {source}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "commit-msg"

    if target.exists() or target.is_symlink():
        if target.exists() and _sha256_file(target) == _sha256_file(source):
            print(f"Already installed at {target} (no change)")
            return EXIT_PASS
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = hooks_dir / f"commit-msg.bak.{ts}"
        shutil.move(str(target), str(backup))
        print(f"Backed up existing hook to {backup}")

    shutil.copy2(str(source), str(target))
    target.chmod(0o755)
    print(f"Installed commit-msg guard at {target}")
    return EXIT_PASS


def _hook_uninstall(args: argparse.Namespace) -> int:
    repo_root = _git_repo_root()
    if repo_root is None:
        print(
            "falsify hook uninstall: not in a git repository",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    hooks_dir = repo_root / ".git" / "hooks"
    target = hooks_dir / "commit-msg"
    source = repo_root / "hooks" / "commit-msg"

    if not target.exists():
        print(f"Nothing to uninstall — no hook at {target}")
        return EXIT_PASS

    matches_ours = (
        source.exists() and _sha256_file(target) == _sha256_file(source)
    )
    if matches_ours:
        target.unlink()
        print(f"Removed {target}")
    else:
        print(
            f"Hook at {target} does not match ours — leaving it in place "
            f"(it may be user-authored).",
            file=sys.stderr,
        )

    backups = sorted(
        hooks_dir.glob("commit-msg.bak.*"), reverse=True
    )
    if backups and matches_ours:
        latest = backups[0]
        if args.force:
            shutil.move(str(latest), str(target))
            target.chmod(0o755)
            print(f"Restored previous hook from {latest.name}")
        else:
            print(
                f"Backup found at {latest}. "
                f"Re-run with --force to restore it."
            )

    return EXIT_PASS


def _export_records_for_spec(
    claim_dir: Path, include_runs: bool
) -> list[dict]:
    records: list[dict] = []
    name = claim_dir.name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"
    verdict_path = claim_dir / "verdict.json"

    locked_hash = ""
    if lock_path.exists() and spec_path.exists():
        try:
            lock_data = json.loads(lock_path.read_text())
            spec = yaml.safe_load(spec_path.read_text())
        except (yaml.YAMLError, OSError, json.JSONDecodeError):
            spec = None
            lock_data = None

        if isinstance(lock_data, dict) and isinstance(spec, dict):
            h = lock_data.get("spec_hash")
            if isinstance(h, str):
                locked_hash = h
            locked_at = lock_data.get("locked_at")

            snippet: dict = {}
            claim = spec.get("claim")
            if isinstance(claim, str):
                snippet["claim"] = _truncate_claim(claim)
            criteria = (
                spec.get("falsification", {}).get("failure_criteria") or []
            )
            if criteria and isinstance(criteria[0], dict):
                first = criteria[0]
                for k in ("metric", "direction", "threshold"):
                    if k in first:
                        snippet[k] = first[k]

            if isinstance(locked_at, str) and locked_at:
                records.append({
                    "type": "lock",
                    "schema_version": 1,
                    "name": name,
                    "ts": locked_at,
                    "canonical_hash": locked_hash,
                    "spec_snippet": snippet,
                })

    if include_runs:
        runs_dir = claim_dir / "runs"
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                meta_path = run_dir / "run_meta.json"
                if not meta_path.exists():
                    continue
                try:
                    meta = json.loads(meta_path.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                stdout_path = run_dir / "stdout.txt"
                stdout_sha256 = ""
                stdout_sample = ""
                if stdout_path.exists():
                    try:
                        raw = stdout_path.read_bytes()
                        stdout_sha256 = hashlib.sha256(raw).hexdigest()
                        stdout_sample = raw.decode("utf-8", errors="replace")[:200]
                    except OSError:
                        pass
                ts = meta.get("start")
                if not isinstance(ts, str):
                    continue
                records.append({
                    "type": "run",
                    "schema_version": 1,
                    "name": name,
                    "ts": ts,
                    "duration_s": meta.get("duration_s"),
                    "exit_code": meta.get("returncode"),
                    "stdout_sha256": stdout_sha256,
                    "stdout_sample": stdout_sample,
                })

    if verdict_path.exists():
        try:
            vd = json.loads(verdict_path.read_text())
        except (OSError, json.JSONDecodeError):
            vd = None
        if isinstance(vd, dict):
            ts = vd.get("checked_at")
            if isinstance(ts, str) and ts:
                records.append({
                    "type": "verdict",
                    "schema_version": 1,
                    "name": name,
                    "ts": ts,
                    "state": vd.get("verdict", ""),
                    "metric_value": vd.get("observed_value"),
                    "threshold": vd.get("threshold"),
                    "direction": vd.get("direction", ""),
                    "n": vd.get("sample_size"),
                    "locked_hash": locked_hash,
                })

    return records


def cmd_export(args: argparse.Namespace) -> int:
    all_records: list[dict] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        if args.name and args.name not in claim_dir.name:
            continue
        all_records.extend(
            _export_records_for_spec(claim_dir, args.include_runs)
        )

    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
        except ValueError:
            print(
                f"falsify export: bad --since value {args.since!r} — "
                f"expected ISO 8601 (YYYY-MM-DD or ...Thh:mm:ss+00:00)",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        filtered: list[dict] = []
        for r in all_records:
            ts_raw = r.get("ts", "")
            if not isinstance(ts_raw, str) or not ts_raw:
                continue
            try:
                rts = datetime.fromisoformat(ts_raw)
            except ValueError:
                continue
            if rts.tzinfo is None:
                rts = rts.replace(tzinfo=timezone.utc)
            if rts >= since_dt:
                filtered.append(r)
        all_records = filtered

    all_records.sort(
        key=lambda r: (r.get("ts", ""), r.get("type", ""), r.get("name", ""))
    )

    lines = [json.dumps(r, sort_keys=True) for r in all_records]
    output_text = ("\n".join(lines) + "\n") if lines else ""

    if args.output:
        Path(args.output).write_text(output_text)
    else:
        sys.stdout.write(output_text)
    return EXIT_PASS


_VERIFY_REQUIRED: dict[str, set[str]] = {
    "lock": {"name", "ts", "canonical_hash"},
    "run": {"name", "ts", "stdout_sha256"},
    "verdict": {"name", "ts", "state", "locked_hash"},
}


def _verify_collect_findings(
    records: list[tuple[int, dict]],
) -> list[dict]:
    findings: list[dict] = []

    for line_no, r in records:
        t = r.get("type")
        if t not in _VERIFY_REQUIRED:
            findings.append({
                "level": "FAIL",
                "message": f"unknown record type: {t!r}",
                "line": line_no,
            })
            continue
        sv = r.get("schema_version")
        if sv != 1:
            findings.append({
                "level": "WARN",
                "message": f"unknown schema_version: {sv!r}",
                "line": line_no,
            })
        missing = _VERIFY_REQUIRED[t] - set(r.keys())
        if missing:
            findings.append({
                "level": "FAIL",
                "message": f"{t} missing required fields: {sorted(missing)}",
                "line": line_no,
            })

    by_name: dict[str, list[tuple[int, dict]]] = {}
    for line_no, r in records:
        name = r.get("name")
        if not isinstance(name, str):
            continue
        by_name.setdefault(name, []).append((line_no, r))

    for name, group in by_name.items():
        prev_ts: str | None = None
        for line_no, r in group:
            ts = r.get("ts")
            if isinstance(ts, str) and prev_ts is not None and ts < prev_ts:
                findings.append({
                    "level": "FAIL",
                    "message": (
                        f"{name}: timestamp regression "
                        f"({ts!r} < {prev_ts!r})"
                    ),
                    "line": line_no,
                })
            if isinstance(ts, str):
                prev_ts = ts

        seen: set[tuple] = set()
        for line_no, r in group:
            key = (r.get("type"), r.get("ts"))
            if key in seen:
                findings.append({
                    "level": "FAIL",
                    "message": f"{name}: duplicate ({key[0]}, {key[1]})",
                    "line": line_no,
                })
            seen.add(key)

        current_lock_hash: str | None = None
        for line_no, r in group:
            t = r.get("type")
            if t == "lock":
                ch = r.get("canonical_hash")
                if isinstance(ch, str):
                    current_lock_hash = ch
            elif t == "run":
                if current_lock_hash is None:
                    findings.append({
                        "level": "FAIL",
                        "message": f"{name}: run before any lock",
                        "line": line_no,
                    })
            elif t == "verdict":
                lh = r.get("locked_hash")
                if current_lock_hash is None:
                    findings.append({
                        "level": "FAIL",
                        "message": f"{name}: verdict before any lock",
                        "line": line_no,
                    })
                elif lh != current_lock_hash:
                    findings.append({
                        "level": "FAIL",
                        "message": (
                            f"{name}: verdict locked_hash does not match "
                            f"preceding lock canonical_hash "
                            f"({lh!r} vs {current_lock_hash!r})"
                        ),
                        "line": line_no,
                    })

    return findings


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.jsonl_path)
    if not path.exists():
        print(
            f"falsify verify: file not found: {path}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    try:
        content = path.read_text()
    except OSError as e:
        print(f"falsify verify: cannot read {path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    records: list[tuple[int, dict]] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(
                f"falsify verify: line {idx}: invalid JSON — {e}",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        if not isinstance(obj, dict):
            print(
                f"falsify verify: line {idx}: expected object, got "
                f"{type(obj).__name__}",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        records.append((idx, obj))

    findings = _verify_collect_findings(records)

    if content and not content.endswith("\n"):
        findings.append({
            "level": "WARN",
            "message": "file does not end with a newline",
            "line": len(content.splitlines()),
        })

    by_name: dict[str, dict] = {}
    line_to_name: dict[int, str] = {}
    for line_no, r in records:
        name = r.get("name")
        if not isinstance(name, str):
            continue
        line_to_name[line_no] = name
        spec = by_name.setdefault(
            name,
            {
                "name": name,
                "records": 0,
                "lock": 0,
                "run": 0,
                "verdict": 0,
                "findings": [],
            },
        )
        spec["records"] += 1
        t = r.get("type")
        if t in ("lock", "run", "verdict"):
            spec[t] += 1

    for f in findings:
        name = line_to_name.get(f.get("line"))
        if name and name in by_name:
            by_name[name]["findings"].append(f)

    for spec in by_name.values():
        levels = {x["level"] for x in spec["findings"]}
        if "FAIL" in levels:
            spec["status"] = "FAIL"
        elif "WARN" in levels:
            spec["status"] = "WARN"
        else:
            spec["status"] = "OK"

    has_fail = any(f["level"] == "FAIL" for f in findings)
    has_warn = any(f["level"] == "WARN" for f in findings)
    treat_warn_as_fail = args.strict and has_warn
    invalid = has_fail or treat_warn_as_fail
    verdict_label = "INVALID" if invalid else "VALID"

    spec_list = sorted(by_name.values(), key=lambda s: s["name"])
    summary = {
        "ok": sum(1 for s in spec_list if s["status"] == "OK"),
        "warn": sum(1 for s in spec_list if s["status"] == "WARN"),
        "fail": sum(1 for s in spec_list if s["status"] == "FAIL"),
    }

    if args.json:
        payload = {
            "verdict": verdict_label,
            "summary": summary,
            "specs": [
                {
                    "name": s["name"],
                    "status": s["status"],
                    "records": s["records"],
                    "findings": s["findings"],
                }
                for s in spec_list
            ],
            "findings": findings,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"verify {path}: {verdict_label}")
        for s in spec_list:
            print(
                f"  {s['name']}: {s['status']} "
                f"({s['lock']} lock, {s['run']} run, {s['verdict']} verdict)"
            )
            for f in s["findings"]:
                print(f"    [{f['level']}] line {f['line']}: {f['message']}")
        orphan = [f for f in findings if line_to_name.get(f.get("line")) is None]
        for f in orphan:
            print(f"  [{f['level']}] line {f.get('line', '?')}: {f['message']}")
        print(
            f"Summary: {summary['ok']} OK, {summary['warn']} WARN, "
            f"{summary['fail']} FAIL → {verdict_label}"
        )

    return EXIT_FAIL if invalid else EXIT_PASS


def cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps({"name": "falsify", "version": __version__}))
    else:
        print(f"falsify {__version__}")
    return EXIT_PASS


def _doctor_env_checks() -> list[dict]:
    out: list[dict] = []

    pyver = sys.version_info
    pv_str = platform.python_version()
    if (pyver.major, pyver.minor) >= (3, 11):
        out.append({
            "level": "OK",
            "message": f"Python version: {pv_str}",
            "detail": None,
        })
    else:
        out.append({
            "level": "WARN",
            "message": f"Python version: {pv_str} (project targets 3.11+)",
            "detail": None,
        })

    out.append({
        "level": "OK",
        "message": f"pyyaml importable: {yaml.__version__}",
        "detail": None,
    })

    repo_root = _git_repo_root()
    if repo_root is None:
        out.append({
            "level": "WARN",
            "message": "Not in a git repository (or git not installed)",
            "detail": None,
        })
        return out

    out.append({
        "level": "OK",
        "message": f"Git repo: {repo_root}",
        "detail": None,
    })

    source_hook = repo_root / "hooks" / "commit-msg"
    if source_hook.exists():
        out.append({
            "level": "OK",
            "message": "hooks/commit-msg source present",
            "detail": None,
        })
    else:
        out.append({
            "level": "WARN",
            "message": f"hooks/commit-msg missing at {source_hook}",
            "detail": None,
        })

    installed = repo_root / ".git" / "hooks" / "commit-msg"
    if not installed.exists():
        out.append({
            "level": "INFO",
            "message": "commit-msg hook not installed",
            "detail": "run `falsify hook install` to enable the guard",
        })
    elif source_hook.exists():
        if _sha256_file(installed) == _sha256_file(source_hook):
            out.append({
                "level": "OK",
                "message": "commit-msg hook installed and matches source",
                "detail": None,
            })
        else:
            out.append({
                "level": "WARN",
                "message": "Hook installed but hash mismatch with hooks/commit-msg",
                "detail": "re-run `falsify hook install` to refresh",
            })
    else:
        out.append({
            "level": "INFO",
            "message": "commit-msg hook installed; source missing, can't verify",
            "detail": None,
        })
    return out


def _doctor_spec_checks() -> list[dict]:
    out: list[dict] = []
    try:
        schema = _load_schema()
    except (yaml.YAMLError, OSError, FileNotFoundError):
        schema = None

    now = datetime.now(timezone.utc)
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        name = claim_dir.name
        spec_path = claim_dir / "spec.yaml"
        lock_path = claim_dir / "spec.lock.json"
        verdict_path = claim_dir / "verdict.json"

        try:
            spec = yaml.safe_load(spec_path.read_text())
        except (yaml.YAMLError, OSError) as e:
            out.append({
                "level": "FAIL",
                "message": f"{name}: spec.yaml failed to parse",
                "detail": str(e),
            })
            continue

        if schema is not None:
            errors: list[str] = []
            _validate_against_schema(spec, schema, "", errors)
            if errors:
                out.append({
                    "level": "FAIL",
                    "message": f"{name}: spec.yaml failed schema validation",
                    "detail": errors[0],
                })
                continue

        out.append({
            "level": "OK",
            "message": f"{name}: spec.yaml valid",
            "detail": None,
        })

        if not lock_path.exists():
            out.append({
                "level": "INFO",
                "message": f"{name}: not locked yet",
                "detail": None,
            })
            continue

        if not verdict_path.exists():
            out.append({
                "level": "INFO",
                "message": f"{name}: locked but not run",
                "detail": None,
            })
            continue

        try:
            verdict_data = json.loads(verdict_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            out.append({
                "level": "WARN",
                "message": f"{name}: verdict.json unreadable",
                "detail": str(e),
            })
            continue

        state = verdict_data.get("verdict", "UNKNOWN")
        out.append({
            "level": "OK" if state == "PASS" else "INFO",
            "message": f"{name}: last verdict {state}",
            "detail": None,
        })

        checked_at = verdict_data.get("checked_at")
        if isinstance(checked_at, str):
            try:
                t = datetime.fromisoformat(checked_at)
                age_days = (now - t).days
                if age_days > 7:
                    out.append({
                        "level": "WARN",
                        "message": f"{name}: last run is {age_days} days old (stale)",
                        "detail": None,
                    })
            except ValueError:
                pass

    return out


def _doctor_workflow_check() -> list[dict]:
    workflow = Path(".github/workflows/falsify.yml")
    if not workflow.exists():
        return [{
            "level": "INFO",
            "message": "No CI workflow at .github/workflows/falsify.yml",
            "detail": None,
        }]
    try:
        yaml.safe_load(workflow.read_text())
    except yaml.YAMLError as e:
        return [{
            "level": "WARN",
            "message": "CI workflow present but not valid YAML",
            "detail": str(e),
        }]
    return [{
        "level": "OK",
        "message": "CI workflow parses",
        "detail": None,
    }]


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: list[dict] = []
    if not args.specs_only:
        checks.extend(_doctor_env_checks())
    checks.extend(_doctor_spec_checks())
    if not args.specs_only:
        checks.extend(_doctor_workflow_check())

    summary = {"ok": 0, "warn": 0, "fail": 0, "info": 0}
    for c in checks:
        summary[c["level"].lower()] = summary.get(c["level"].lower(), 0) + 1

    if args.json:
        print(json.dumps(
            {"checks": checks, "summary": summary},
            indent=2,
            sort_keys=True,
        ))
    else:
        for c in checks:
            print(f"[{c['level']}] {c['message']}")
            if c.get("detail"):
                print(f"       {c['detail']}")
        print()
        print(
            f"Summary: {summary['ok']} OK, {summary['warn']} WARN, "
            f"{summary['fail']} FAIL, {summary['info']} INFO"
        )

    return EXIT_BAD_SPEC if summary["fail"] > 0 else EXIT_PASS


def cmd_hook(args: argparse.Namespace) -> int:
    if args.action == "install":
        return _hook_install(args)
    if args.action == "uninstall":
        return _hook_uninstall(args)
    print(f"falsify hook: unknown action {args.action!r}", file=sys.stderr)
    return EXIT_BAD_SPEC


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="falsify",
        description="Pre-registration + CI for AI-agent claims.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"falsify {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="Print the version")
    p_version.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON: {name, version}",
    )
    p_version.set_defaults(func=cmd_version)

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

    p_diff = sub.add_parser(
        "diff",
        help="Unified diff between a locked spec's canonical YAML and the current spec.yaml",
    )
    p_diff.add_argument(
        "name",
        nargs="?",
        help="Claim name (required unless --file-vs-file is given)",
    )
    p_diff_modes = p_diff.add_mutually_exclusive_group()
    p_diff_modes.add_argument(
        "--lock-vs-file",
        action="store_true",
        help="Compare the claim's locked canonical YAML against its current spec.yaml (default)",
    )
    p_diff_modes.add_argument(
        "--file-vs-file",
        nargs=2,
        metavar=("A", "B"),
        help="Canonical diff between two arbitrary YAML files",
    )
    p_diff.set_defaults(func=cmd_diff)

    p_verdict = sub.add_parser("verdict", help="Report PASS/FAIL for a claim")
    p_verdict.add_argument("name", help="Claim name")
    p_verdict.set_defaults(func=cmd_verdict)

    p_guard = sub.add_parser(
        "guard",
        help="CI wrapper — text-match, scan, or wrap modes",
        description=(
            "Three modes:\n"
            "  falsify guard              scan for FAIL/STALE claims (exit 10 on hit)\n"
            "  falsify guard \"text\"       block affirmative claims vs logged FAIL/INCONCLUSIVE (exit 11)\n"
            "  falsify guard -- <cmd>    run <cmd>; on success, also scan"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_guard.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="Claim text, or `-- cmd args...` for wrap mode",
    )
    p_guard.set_defaults(func=cmd_guard)

    p_verify = sub.add_parser(
        "verify",
        help="Audit a JSONL export for chain integrity and ordering",
    )
    p_verify.add_argument(
        "jsonl_path",
        help="Path to the JSONL file produced by `falsify export`",
    )
    p_verify.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN findings as FAIL (exit 10)",
    )
    p_verify.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report",
    )
    p_verify.set_defaults(func=cmd_verify)

    p_export = sub.add_parser(
        "export",
        help="Write the verdict history as JSONL (audit trail, read-only)",
    )
    p_export.add_argument(
        "--output", help="Write to PATH instead of stdout",
    )
    p_export.add_argument(
        "--name", help="Filter by claim-name substring",
    )
    p_export.add_argument(
        "--since",
        help="Emit only records with ts >= this ISO 8601 date",
    )
    p_export.add_argument(
        "--include-runs",
        action="store_true",
        help="Include run records with stdout SHA-256 and a 200-char sample",
    )
    p_export.set_defaults(func=cmd_export)

    p_doctor = sub.add_parser(
        "doctor",
        help="Self-diagnostic: environment + repo + per-spec checks",
    )
    p_doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    p_doctor.add_argument(
        "--specs-only",
        action="store_true",
        help="Run only per-spec checks (skip environment and CI checks)",
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_hook = sub.add_parser(
        "hook",
        help="Install or uninstall the commit-msg guard hook",
    )
    hook_sub = p_hook.add_subparsers(dest="action", required=True)
    p_hook_install = hook_sub.add_parser(
        "install",
        help="Copy hooks/commit-msg into .git/hooks/, backing up any existing hook",
    )
    p_hook_install.add_argument(
        "--force",
        action="store_true",
        help="Reserved for install — currently unused, accepted for symmetry",
    )
    p_hook_install.set_defaults(func=cmd_hook)

    p_hook_uninstall = hook_sub.add_parser(
        "uninstall",
        help="Remove the installed commit-msg hook (restore .bak with --force)",
    )
    p_hook_uninstall.add_argument(
        "--force",
        action="store_true",
        help="Restore the most recent .bak backup without prompting",
    )
    p_hook_uninstall.set_defaults(func=cmd_hook)

    p_list = sub.add_parser("list", help="List all claims with their status")
    p_list.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser(
        "stats",
        help="Aggregate dashboard across all locked verdicts (informational)",
    )
    stats_mode = p_stats.add_mutually_exclusive_group()
    stats_mode.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    stats_mode.add_argument(
        "--html",
        action="store_true",
        help="Emit a self-contained HTML dashboard (inline CSS, zero deps)",
    )
    p_stats.add_argument(
        "--output",
        help="Write output to PATH instead of stdout",
    )
    p_stats.add_argument(
        "--name",
        help="Filter to claim names containing this substring",
    )
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
