#!/usr/bin/env python3
"""Pre-release validator — 12 gates, stdlib only.

Runs the twelve release-readiness gates and prints one line per
gate in the form:

    <label>  PASS|WARN|FAIL  <message>

Exit codes:
    0 — every gate is PASS or WARN (safe to tag).
    1 — at least one gate is FAIL (do not tag).

Usage: python3 scripts/release_check.py [--all] [--json] [--quiet]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent.parent

URL_TOKENS = ("<USER>", "<REPO>", "<VIDEO_URL>")
STRONG_TOKENS = ("XXX", "FIXME", "{REPLACE_ME}")
TOKEN_EXEMPT_FILES = {
    "falsify.py",
    "hypothesis.schema.yaml",
    "scripts/release_check.py",
    "examples/template.yaml",
}
PLACEHOLDER_WARN_ONLY = {"SUBMISSION.md", "docs/DEMO_SCRIPT.md"}

REQUIRED_DOCS = [
    "README.md", "TUTORIAL.md", "DEMO.md", "CHANGELOG.md",
    "CONTRIBUTING.md", "CLAUDE.md", "SUBMISSION.md",
    "CODE_OF_CONDUCT.md", "ROADMAP.md",
    "docs/ARCHITECTURE.md", "docs/ADVERSARIAL.md", "docs/FAQ.md",
    "docs/COMPARISON.md", "docs/EXAMPLES.md", "docs/PR_REVIEW.md",
    "docs/MANAGED_AGENTS.md", "docs/DEMO_SCRIPT.md",
]


def g1_version():
    text = (REPO_ROOT / "falsify.py").read_text()
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        return "FAIL", "falsify.__version__ not found"
    fv = m.group(1)
    if tomllib is None:
        return "WARN", f"tomllib unavailable; falsify={fv}"
    pv = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    m = re.search(r"(?m)^## \[(\d+\.\d+\.\d+)\]", cl)
    cv = m.group(1) if m else None
    if fv == pv == cv:
        return "PASS", fv
    return "FAIL", f"falsify={fv} pyproject={pv} changelog={cv}"


def g2_changelog():
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    m = re.search(r"(?ms)^## \[Unreleased\]\s*\n(.*?)(?=\n## |\Z)", cl)
    if not m:
        return "FAIL", "no [Unreleased] section"
    entries = re.findall(r"(?m)^- ", m.group(1))
    if not entries:
        return "FAIL", "[Unreleased] is empty"
    return "PASS", f"{len(entries)} entries"


def g3_placeholders():
    r = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "FAIL", "git ls-files failed"
    url_re = re.compile("|".join(re.escape(t) for t in URL_TOKENS))
    strong_re = re.compile("|".join(re.escape(t) for t in STRONG_TOKENS))
    warns = defaultdict(set)
    fails = []
    for f in r.stdout.splitlines():
        if f in TOKEN_EXEMPT_FILES or f.startswith("tests/"):
            continue
        p = REPO_ROOT / f
        if not p.is_file():
            continue
        try:
            text = p.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue
        soft = f in PLACEHOLDER_WARN_ONLY
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in url_re.finditer(line):
                warns[f].add(m.group(0))
            for m in strong_re.finditer(line):
                if soft:
                    warns[f].add(m.group(0))
                else:
                    fails.append(f"{f}:{lineno} {m.group(0)}")
    if fails:
        head = "; ".join(fails[:3])
        return "FAIL", head + (f" +{len(fails)-3}" if len(fails) > 3 else "")
    if warns:
        summary = "; ".join(
            f"{k}:{','.join(sorted(v))}" for k, v in sorted(warns.items())
        )
        return "WARN", summary
    return "PASS", "no placeholders"


def g4_legal():
    missing = []
    for rel in ("LICENSE", "CODE_OF_CONDUCT.md", ".github/SECURITY.md"):
        if not (REPO_ROOT / rel).exists():
            missing.append(rel)
    if missing:
        return "FAIL", "missing: " + ", ".join(missing)
    return "PASS", "LICENSE + COC + SECURITY.md present"


def g5_tests():
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        return "FAIL", f"unittest exit {r.returncode}"
    m = re.search(r"Ran (\d+) tests", r.stderr)
    if not m:
        return "WARN", "could not parse test count"
    n = int(m.group(1))
    if n < 400:
        return "FAIL", f"only {n} tests (< 400)"
    return "PASS", f"{n} tests"


def g6_smoke():
    r = subprocess.run(
        ["bash", "tests/smoke_test.sh"], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        return "FAIL", f"smoke exit {r.returncode}"
    return "PASS", "smoke_test.sh green"


def g7_dogfood():
    r = subprocess.run(
        ["make", "dogfood"], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        return "FAIL", f"make dogfood exit {r.returncode}"
    passes = r.stdout.count("Verdict: PASS")
    return "PASS", f"{passes} self-claim PASS"


def g8_docs():
    problems = []
    for rel in REQUIRED_DOCS:
        p = REPO_ROOT / rel
        if not p.exists():
            problems.append(rel)
        elif len(p.read_text().splitlines()) < 20:
            problems.append(f"{rel} (<20 lines)")
    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", f"{len(REQUIRED_DOCS)} docs OK"


def g9_claude_surface():
    cd = REPO_ROOT / ".claude"
    skills = list(cd.glob("skills/*/SKILL.md"))
    agents = list(cd.glob("agents/*.md"))
    commands = list(cd.glob("commands/*.md"))
    problems = []
    if len(skills) < 4:
        problems.append(f"skills={len(skills)}<4")
    if len(agents) < 2:
        problems.append(f"agents={len(agents)}<2")
    if len(commands) < 3:
        problems.append(f"commands={len(commands)}<3")
    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", f"{len(skills)} skills, {len(agents)} agents, {len(commands)} commands"


def g10_pyproject():
    if tomllib is None:
        try:
            import tomli as _tom  # type: ignore
        except ImportError:
            return "WARN", "no tomllib/tomli; skipped"
        d = _tom.loads((REPO_ROOT / "pyproject.toml").read_text())
    else:
        d = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    if d.get("project", {}).get("name") != "falsify":
        return "FAIL", "project.name != 'falsify'"
    if "falsify" not in d.get("project", {}).get("scripts", {}):
        return "FAIL", "[project.scripts] missing 'falsify'"
    return "PASS", "pyproject parses; name=falsify; entry point OK"


def g11_git_clean():
    r = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "FAIL", "git status failed"
    if r.stdout.strip():
        n = len(r.stdout.strip().splitlines())
        return "WARN", f"{n} uncommitted change(s)"
    return "PASS", "working tree clean"


def g12_self_integrity():
    claims_dir = REPO_ROOT / "claims" / "self"
    if not claims_dir.is_dir():
        return "WARN", "no claims/self/ directory"
    claims = sorted(p.name for p in claims_dir.iterdir() if p.is_dir())
    if not claims:
        return "WARN", "no self-claims found"
    probe = (
        "import yaml, hashlib, sys\n"
        "spec = yaml.safe_load(open(sys.argv[1]).read())\n"
        "canon = yaml.safe_dump(spec, sort_keys=True,\n"
        "    default_flow_style=False, allow_unicode=True, width=4096)\n"
        "print(hashlib.sha256(canon.encode('utf-8')).hexdigest())\n"
    )
    problems = []
    for name in claims:
        lock_p = REPO_ROOT / ".falsify" / name / "spec.lock.json"
        spec_p = REPO_ROOT / ".falsify" / name / "spec.yaml"
        if not lock_p.exists():
            problems.append(f"{name}: no lock")
            continue
        try:
            stored = json.loads(lock_p.read_text()).get("spec_hash", "")
        except Exception:
            problems.append(f"{name}: lock parse error")
            continue
        r = subprocess.run(
            [sys.executable, "-c", probe, str(spec_p)],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or r.stdout.strip() != stored:
            problems.append(f"{name}: hash mismatch")
    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", f"{len(claims)} self-claim(s) OK"


GATES = [
    ("GATE 1: version consistency",    g1_version),
    ("GATE 2: CHANGELOG [Unreleased]", g2_changelog),
    ("GATE 3: placeholder scan",       g3_placeholders),
    ("GATE 4: license and legal",      g4_legal),
    ("GATE 5: test suite",             g5_tests),
    ("GATE 6: smoke test",             g6_smoke),
    ("GATE 7: dogfood",                g7_dogfood),
    ("GATE 8: docs sanity",            g8_docs),
    ("GATE 9: claude surface",         g9_claude_surface),
    ("GATE 10: pyproject parseable",   g10_pyproject),
    ("GATE 11: git cleanliness",       g11_git_clean),
    ("GATE 12: self-integrity",        g12_self_integrity),
]


def main():
    ap = argparse.ArgumentParser(description="Pre-release 12-gate validator")
    ap.add_argument("--all", action="store_true",
                    help="run every gate even after a FAIL")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress PASS lines")
    args = ap.parse_args()

    results = []
    any_fail = False
    for label, fn in GATES:
        try:
            status, msg = fn()
        except subprocess.TimeoutExpired:
            status, msg = "FAIL", "timed out"
        except Exception as e:
            status, msg = "FAIL", f"{type(e).__name__}: {e}"
        results.append({"label": label, "status": status, "message": msg})
        if status == "FAIL":
            any_fail = True
            if not args.all:
                break

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        counts[r["status"]] += 1

    if args.json:
        print(json.dumps({"results": results, "counts": counts}, indent=2))
    else:
        for r in results:
            if args.quiet and r["status"] == "PASS":
                continue
            print(f"{r['label']}  {r['status']}  {r['message']}")
        print(f"Summary: {counts['PASS']} PASS, "
              f"{counts['WARN']} WARN, {counts['FAIL']} FAIL")
        if not any_fail:
            print("Ready to tag and push.")

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
