---
name: Feature request
about: Propose a new CLI flag, skill, agent, or behavior
title: "[FEATURE] "
labels: ["enhancement"]
---

## Problem

What claim or workflow can't be expressed today? Describe the gap
in concrete terms — what did you try, where did it fall short?

## Proposal

What CLI command, flag, skill, or subagent would address it? Be
specific about the argv shape or frontmatter keys.

## Alternatives considered

What else could work? Why is your proposal preferable? If there's
an existing workaround, note it.

## Impact on determinism

Does this proposal risk the exit-code contract (`0`, `10`, `2`,
`3`, `11`), the canonical-YAML hash guarantee, or the pre-
registration semantics? Explain why it's safe — or what safeguard
is needed — before we merge.
