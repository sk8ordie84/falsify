# claude_surface — falsify self-claim

Asserts the Claude integration surface ships more than 8
artifacts across `.claude/skills/`, `.claude/agents/`, and
`.claude/commands/` — a minimum of 4 skills + 2 subagents + 3
slash commands.

**Why the threshold matters.** The Claude footprint is a
load-bearing part of the pitch. Silently deleting a skill or
subagent file would invalidate the "Opus 4.7 layers" claim in
README and SUBMISSION. The lock forces any removal to be a
visible hash change with a re-lock ceremony.

**How the metric is computed.** `metric.py` globs
`.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, and
`.claude/commands/*.md`, sums the counts, and returns
`(total, n_kinds_present)`. Stdlib only.
