#!/usr/bin/env python3
"""
HumanEval pass@1 runner — works against a locked PRML manifest.

This script demonstrates the runtime side of the PRML walkthrough.
It is not a full HumanEval evaluator (those exist; use one). What it
demonstrates is:

  1. Loading a locked PRML manifest.
  2. Verifying the dataset SHA-256 matches the manifest's claim.
  3. Running an inference pass against a configurable model.
  4. Writing observed metric value to .falsify/<name>/run.json so
     `falsify verify --observed` can read it.

Usage:
    python3 run_humaneval.py humaneval_pass1_v1

Requires: anthropic OR openai OR a local model wrapper, plus
human-eval (`pip install human-eval`).

For the walkthrough README, output is illustrative; replace the
inference loop with a real call when running for real.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FALSIFY_DIR = Path.cwd() / ".falsify"


def load_locked_spec(claim_name: str) -> dict:
    """Read .falsify/<name>/spec.yaml. Insist it is locked."""
    spec_path = FALSIFY_DIR / claim_name / "spec.yaml"
    lock_path = FALSIFY_DIR / claim_name / "spec.lock.json"
    if not spec_path.exists():
        sys.exit(f"run_humaneval: {spec_path} not found. "
                 f"Run `falsify init {claim_name}` first.")
    if not lock_path.exists():
        sys.exit(f"run_humaneval: {claim_name} is not locked. "
                 f"Run `falsify lock {claim_name}` first.")
    return yaml.safe_load(spec_path.read_text())


def verify_dataset_hash(spec: dict, dataset_path: Path) -> None:
    """Recompute SHA-256 of dataset_path; assert match against spec."""
    expected = spec["dataset"]["hash"]
    h = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    if h != expected:
        sys.exit(f"run_humaneval: dataset hash mismatch.\n"
                 f"  expected: {expected}\n"
                 f"  computed: {h}\n"
                 f"  → the dataset bytes are not what the manifest committed to.")
    print(f"loading dataset: {spec['dataset']['id']} "
          f"({expected[:16]}... ✓ byte match)")


def load_humaneval(dataset_path: Path) -> list[dict]:
    """Read HumanEval problems from .jsonl.gz file."""
    import gzip
    problems = []
    with gzip.open(dataset_path, "rt") as f:
        for line in f:
            problems.append(json.loads(line))
    return problems


def generate_completion(prompt: str, model_id: str, seed: int) -> str:
    """Stub for the actual inference call.

    Replace with your provider's API call. Examples:

        # Anthropic
        from anthropic import Anthropic
        client = Anthropic()
        msg = client.messages.create(
            model=model_id,
            max_tokens=512,
            temperature=0.0,
            system="You are a Python programmer. Complete the function.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

        # OpenAI
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model_id,
            temperature=0.0,
            seed=seed,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    For the walkthrough, this stub returns a placeholder. The README's
    "PASS observed=0.689" output is illustrative, not produced by this stub.
    """
    return f"# stub completion (seed={seed}, model={model_id})\npass\n"


def evaluate_pass_at_1(problems: list[dict], completions: list[str]) -> float:
    """
    Run the HumanEval `check_correctness` for each problem-completion pair.
    Returns pass@1 as fraction of problems where execution passes the unit tests.

    For the walkthrough stub, we return a fixed value to illustrate the flow.
    Replace with the real `human_eval.execution.check_correctness` for actual scoring.
    """
    # Stub: real scoring goes here.
    # from human_eval.execution import check_correctness
    # passed = sum(check_correctness(p, c, ...)['passed'] for p, c in zip(problems, completions))
    # return passed / len(problems)
    print("WARN: this is a stub evaluator. Replace with the real "
          "human-eval check_correctness for actual scoring.")
    return 0.689  # illustrative


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("claim_name", help="claim name in .falsify/<name>/")
    ap.add_argument("--dataset", default="data/HumanEval.jsonl.gz",
                    help="path to HumanEval dataset (default: data/HumanEval.jsonl.gz)")
    args = ap.parse_args()

    spec = load_locked_spec(args.claim_name)
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        sys.exit(f"run_humaneval: dataset file not found: {dataset_path}\n"
                 f"  Clone https://github.com/openai/human-eval and pin the commit.")

    verify_dataset_hash(spec, dataset_path)

    model_id = spec["model"]["id"] if "model" in spec else None
    if not model_id:
        sys.exit("run_humaneval: spec has no model.id; cannot proceed.")
    print(f"loading model: {model_id}")

    problems = load_humaneval(dataset_path)
    print(f"generating {len(problems)} completions at temperature=0.0, "
          f"seed={spec['seed']}")

    completions = []
    for i, p in enumerate(problems):
        comp = generate_completion(p["prompt"], model_id, spec["seed"])
        completions.append(comp)
        # Progress dots are nice; add real progress bar if you want.
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(problems)}")

    pass_at_1 = evaluate_pass_at_1(problems, completions)
    print(f"observed pass@1 = {pass_at_1:.3f}")

    # Write run.json so `falsify verify` can pick up the observed value.
    run_path = FALSIFY_DIR / args.claim_name / "run.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps({
        "observed": pass_at_1,
        "metric": spec["metric"],
        "model": model_id,
        "seed": spec["seed"],
        "n_problems": len(problems),
    }, indent=2))
    print(f"wrote {run_path}")
    print(f"\nNext: falsify verify {args.claim_name} --observed {pass_at_1:.3f}")


if __name__ == "__main__":
    main()
