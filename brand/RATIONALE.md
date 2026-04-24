# Direction C — Chevron Monogram

**Concept.** A square containing a left-pointing chevron. The square is a container — bounded, defined, sealed. The chevron points left: back toward the claim, toward origin, toward "before the test." It is the mathematical less-than sign, and it is also a play/rewind glyph. Two geometric readings, one shape.

**Why it fires**
- Chevron inside square is one of the most legible mark archetypes at small size — used in terminal prompts, CLI tools, and devops tooling where falsify lives.
- The left-pointing direction is unusual (most chevrons or arrows point right or down) — the visual oddity creates memorability.
- Clean filled polygon at any scale: no stroke artifacts, no degradation at 16px.
- The square outline at 1.5px stroke creates a consistent visual weight family with B_sealed.

**Where it might fail**
- The `<` chevron is not inherently tied to falsify's domain without explanation — it borrows meaning from code editors and terminals rather than generating its own.
- Risk of confusion with CLI prompt glyphs (`>`, `$`, `%`) — the less-than angle may read as "less than" (comparison) rather than "back" or "origin."
- The filled chevron on dark ground at very small sizes (sub-12px) may fill in and lose definition.

**Recommended primary use:** App badge, CLI tool icon, docs sidebar mark — any context where the developer / terminal aesthetic is the primary signal and a compact square icon is required.
