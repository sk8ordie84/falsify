# pre-commit integration

Falsification Engine plays two roles with the
[pre-commit](https://pre-commit.com) framework: it is both a *hook
source* other repos can consume, and a *hook consumer* for its own
working tree.

## Using falsify as a hook in your repo

Add to your repo's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/sk8ordie84/falsify
    rev: v0.1.0
    hooks:
      - id: falsify-guard
      - id: falsify-doctor
```

Then wire both the pre-commit and commit-msg stages:

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

## What each hook does

- **`falsify-guard`** — runs on the `commit-msg` stage. Blocks
  commits whose message contradicts any locked verdict. Exit 11
  on violation.
- **`falsify-doctor`** — runs on `pre-commit`. Invokes
  `falsify doctor --specs-only` to validate every `spec.yaml` and
  check that locks are consistent. Exit 2 on schema or lock
  problems.
- **`falsify-stats`** — informational. Prints a one-line summary
  of verdict states on every commit. Never blocks.

## Our own repo

This repo also uses pre-commit — see
[`.pre-commit-config.yaml`](../.pre-commit-config.yaml). It
combines the standard
[pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks)
hygiene hooks (trailing whitespace, EOF fixer, check-yaml,
check-json, merge-conflict, large-file guard) with three local
hooks pulled straight from the working tree:

- `falsify-guard-local` — same as the consumer hook but uses
  `python3 falsify.py` directly (no install required).
- `falsify-doctor-local` — same for `doctor --specs-only`.
- `unittest-fast` — runs a subset of the unittest suite
  (`test_lock`, `test_run`, `test_verdict`) on every commit.

Maintainers should run `pre-commit install` once after cloning.

## Why the two YAML files

- **`.pre-commit-hooks.yaml`** is the *manifest* consumed by other
  repos that point at us as a hook source. It declares the
  language, entry point, stage, and arguments for each exported
  hook id.
- **`.pre-commit-config.yaml`** is *our own* repo's pre-commit
  configuration, including third-party hooks and our local
  overrides.

Don't confuse them — the manifest is the product we ship; the
config is our internal discipline.
