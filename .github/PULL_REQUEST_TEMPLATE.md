## Summary

One or two sentences describing what this PR changes and why.

## Checklist

- [ ] Tests added / updated
- [ ] `python3 -m unittest discover tests -v` passes
- [ ] `bash tests/smoke_test.sh` passes
- [ ] No new dependencies beyond `pyyaml`
- [ ] `DEMO.md` and `docs/ARCHITECTURE.md` updated if behavior changed
- [ ] `README.md` updated if a user-facing command changed
- [ ] `CHANGELOG.md` `[Unreleased]` section has a line for this change

## Determinism notes

Does this change affect hashing, exit codes, or the canonical form
of a locked spec? If yes, explain why it's safe — what invariant is
preserved, and how the existing tests cover it.

## Related issue

Closes #...
