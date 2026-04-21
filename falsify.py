#!/usr/bin/env python3
"""Falsification Engine — pre-registration + CI for AI-agent claims."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXIT_PASS = 0
EXIT_FAIL = 10
EXIT_BAD_SPEC = 2
EXIT_HASH_MISMATCH = 3

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "examples" / "template.yaml"
FALSIFY_DIR = Path(".falsify")


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


def cmd_lock(args: argparse.Namespace) -> int:
    return _stub("lock")


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
