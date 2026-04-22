"""Claude integration surface count: skills + subagents + slash commands.

Stdlib only. Counts artifacts under `.claude/skills/*/SKILL.md`,
`.claude/agents/*.md`, and `.claude/commands/*.md`.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = REPO_ROOT / ".claude"


def count_claude_artifacts(_run_dir) -> tuple[int, int]:
    """Return (total_artifact_count, n_kinds_present)."""
    skills = list(CLAUDE_DIR.glob("skills/*/SKILL.md"))
    agents = list(CLAUDE_DIR.glob("agents/*.md"))
    commands = list(CLAUDE_DIR.glob("commands/*.md"))
    total = len(skills) + len(agents) + len(commands)
    kinds = sum(1 for bucket in (skills, agents, commands) if bucket)
    return total, kinds


if __name__ == "__main__":
    total, kinds = count_claude_artifacts(None)
    print(f"total={total} kinds={kinds}")
