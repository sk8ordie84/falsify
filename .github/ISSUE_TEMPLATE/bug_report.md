---
name: Bug report
about: Report a falsify CLI or skill/agent bug
title: "[BUG] "
labels: ["bug"]
---

## Version

Output of: `python3 falsify.py --version`

## What happened

A single paragraph describing the bug as it actually manifested.

## What you expected

A single paragraph describing what you thought should have happened,
and why.

## Reproduction

The minimal `spec.yaml` and the `falsify` command(s) you ran, in
order, to trigger the bug. Include any edits to the spec between
runs if drift is involved.

```yaml
# spec.yaml
```

```bash
# commands
```

## Exit code observed vs expected

| Observed | Expected |
|----------|----------|
|          |          |

## Environment

- Python version: `python3 --version`
- OS:
- In a git repo (yes/no):
- pyyaml version: `python3 -c "import yaml; print(yaml.__version__)"`

## `falsify doctor` output

Paste the output of `python3 falsify.py doctor` below so we can see
the state of your environment, hook, and specs at once:

```
```
