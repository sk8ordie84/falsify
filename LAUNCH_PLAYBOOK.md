# falsify launch playbook — Day 0

**When:** The moment hackathon results are announced (April 28, ~19:45
Turkey / 12:45 EST), regardless of outcome.

**Same-day target:** 50% of this list.
**Week 1 target:** 100%.

This document is the single source of truth for the post-hackathon
execution. Claude picks it up automatically via a scheduled task; the
user can follow it manually by ticking boxes.

---

## Gate 0 — Pre-flight (30 min, before execution starts)

- [ ] Confirm result recorded somewhere (W, L, or special prize).
      This affects the PR copy in later steps, not the steps themselves.
- [ ] Confirm `git status` clean on `main`, HEAD == `origin/main`.
- [ ] Run `pytest -q` — must be `518 passed, 1 skipped`.
- [ ] Confirm `falsify_demo_final_v3.3_4k.mp4` plays (final sanity).
- [ ] Confirm YouTube link `youtu.be/vVZTNeak5PA` still live.

---

## Step 1 — Domain (USER, 10 min, $12) 🟢 **DAY 0 REQUIRED**

Register `falsify.dev` at Porkbun or Namecheap. This is a user-action
step (credit card required).

- [ ] Buy `falsify.dev` (1-year minimum, auto-renew ON)
- [ ] Set nameservers to Vercel/Cloudflare if planning landing page
- [ ] Enable WHOIS privacy

Backup names if `.dev` taken: `getfalsify.com`, `falsify.sh`,
`tryfalsify.com`.

---

## Step 2 — PyPI release (CLAUDE, 90 min, FREE) 🟢 **DAY 0 REQUIRED**

The single biggest adoption unlock. Right now `pip install falsify`
returns 404. After this step, any ML engineer can try falsify in
30 seconds.

### 2a. Bump version
```bash
# In pyproject.toml: version = "0.1.0" → "0.1.1"
# In falsify/__init__.py (or wherever __version__ lives)
```

### 2b. Test build locally
```bash
cd /Users/cuneytozturk/Desktop/falsify-hackathon
.venv/bin/python -m pip install --upgrade build twine
.venv/bin/python -m build
ls dist/  # falsify-0.1.1-py3-none-any.whl + .tar.gz
.venv/bin/twine check dist/*
```

### 2c. Upload to TestPyPI first (dry run)
```bash
.venv/bin/twine upload --repository testpypi dist/*
# Fresh venv verify:
python -m venv /tmp/tpypi && /tmp/tpypi/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  falsify
/tmp/tpypi/bin/falsify --version   # must print 0.1.1
```

### 2d. Upload to real PyPI
```bash
.venv/bin/twine upload dist/*   # needs PyPI API token
```

User action: **create PyPI account + API token** at pypi.org/manage/account/token/

### 2e. Verify public install
```bash
python -m venv /tmp/real && /tmp/real/bin/pip install falsify
/tmp/real/bin/falsify --version
```

### 2f. Update README
Replace "Installation" section with `pip install falsify`. Remove the
"clone the repo" as the primary instructions.

---

## Step 3 — GitHub Release tag (CLAUDE, 20 min) 🟢 **DAY 0 REQUIRED**

```bash
git tag -a v0.1.1 -m "First public release — pip install falsify"
git push origin v0.1.1
gh release create v0.1.1 \
  --title "v0.1.1 — First public release" \
  --notes-file docs/RELEASE_NOTES_v0.1.1.md \
  --verify-tag \
  docs/assets/v2/falsify_demo_final_v3.3_4k.mp4
```

Release notes template stored at `docs/RELEASE_NOTES_v0.1.1.md` —
Claude writes this at run time with hackathon outcome mentioned
neutrally ("shipped from the Built with Opus 4.7 hackathon").

---

## Step 4 — Landing page scaffold (CLAUDE, 90 min) 🟡 **DAY 0 NICE**

Single-page Next.js or plain HTML at `falsify.dev`. Contents:

- Hero — logo lockup + one-liner + `pip install falsify` code block + YouTube embed
- Problem section (3 paragraphs, lifted from README)
- 30-second loop GIF — lock → PASS → tamper → exit 3
- "Who's using" placeholder (fill after first pilot)
- Footer: GitHub link, Discord link (step 9), `commercial@falsify.dev`

Tech: Next.js + Tailwind, deploy to Vercel. Domain connected via
Vercel's one-click.

Reuse brand assets from `brand/` directory — colors, fonts, SVG
logos are all there.

---

## Step 5 — GitHub Action (CLAUDE, 2h) 🟡 **DAY 1**

Separate repo: `sk8ordie84/falsify-action`. One-file action that wraps
`falsify guard --wrap -- <command>`. Publish to GitHub Actions
Marketplace.

```yaml
# Usage after shipping:
- uses: sk8ordie84/falsify-action@v1
  with:
    claim: accuracy
    fail-on-stale: true
```

This is zero-config CI integration — the single biggest adoption
lever after `pip install`.

---

## Step 6 — First 20 cold outreaches (USER, 2-4h) 🟡 **DAY 1-2**

Target segments:
- 5× ML research engineers (Anthropic, Meta FAIR, Mistral, DeepMind, OpenAI)
- 5× MLOps leads (Stripe ML, DoorDash, Netflix, Airbnb, Spotify)
- 5× AI safety orgs (METR, Apollo Research, Redwood, AISI)
- 5× academic labs (Stanford HAI, MIT CSAIL, CMU ML, Princeton CITP, ETH AI Center)

Template message drafted in `docs/OUTREACH_TEMPLATES.md` (Claude
writes this on day 0).

Hedef: 2-4 reply, 1 pilot user. O 1 pilot case study olur.

---

## Step 7 — HN / Reddit post (USER + CLAUDE, 1h) 🔴 **DAY 2-3**

**Important:** Wait 48h after PyPI release so `pip install falsify`
is battle-tested before HN traffic hits.

HN Show post:
- Title: "Show HN: Falsify — Pre-register ML accuracy claims with SHA-256"
- Body: technical problem + solution, no hackathon mention
- Timing: Tuesday 08:00-10:00 EST best traction

Reddit:
- r/MachineLearning (D flair) — "Discussion: pre-registering ML claims with cryptographic hashes"
- r/devops — CI integration angle
- r/Python — packaging angle

---

## Step 8 — Technical blog post (USER, 3-4h) 🔴 **DAY 3-4**

*"Why your 94% accuracy claim is never falsifiable"*

1,500 words. Posted at falsify.dev/blog (or Substack as fallback).
Structure:
1. The replication crisis in ML (concrete examples from 2023-2025)
2. Why pre-registration works in psychology/medicine
3. The minimum viable contract — SHA-256 on canonical YAML
4. How falsify implements it (with one code example)
5. What this means for AI safety claims

SEO: target "ML reproducibility", "AI accuracy claims", "machine
learning audit".

---

## Step 9 — Discord server (USER, 30 min) 🟡 **DAY 2**

Even if empty. Signals "community exists". 3 channels:
- #general — hangout
- #help — support
- #showcase — user projects

Invite link in README, landing page, HN post.

---

## Step 10 — Roadmap public (CLAUDE, 1h) 🔴 **DAY 5**

`ROADMAP.md` committed to repo:
- v0.2 (May): Jupyter magic `%falsify lock`, pytest plugin, diff viewer polish
- v0.3 (June): Claim templates (classification, regression, LLM eval, A/B)
- v0.4 (July): Self-hosted web dashboard
- v1.0 (Q3): REST API, Python/JS SDK, PDF audit export

Hackers contributing trust projects with visible roadmaps.

---

## Day 0 definition of done (50% target)

Same-day bare minimum to call it "launched":

1. [ ] Domain bought (step 1)
2. [ ] `pip install falsify` works for strangers (step 2)
3. [ ] GitHub release v0.1.1 tagged with video attached (step 3)
4. [ ] Landing page scaffold deployed to falsify.dev (step 4, even if
       minimal)
5. [ ] Discord server created (step 9)

Anything beyond this is a bonus. Steps 5, 6, 7, 8, 10 happen across
days 1-5.

---

## Failure modes & fallbacks

| Step fails | Fallback |
|---|---|
| `falsify.dev` taken | `getfalsify.com` or `tryfalsify.com` |
| PyPI name `falsify` taken | `falsify-cli` (still pip-installable) |
| Build errors | Downgrade pyproject to known-good spec, defer to Day 1 |
| Vercel deploy hangs | Fallback to GitHub Pages from repo (free, slower) |
| No cold-outreach replies | Post in relevant Slack/Discord (MLOps Community, LocalLLaMA) |
| HN post dies | Try again in 2 weeks with different angle |

---

## Post-mortem checklist (Day 7)

- [ ] How many PyPI downloads in week 1?
- [ ] How many GitHub stars?
- [ ] Any cold-outreach reply converted to actual trial?
- [ ] HN post comment count + sentiment
- [ ] Landing page analytics (Plausible/Vercel) — where did traffic come from?
- [ ] Any real-world issue/PR from external user?

If any of these > 0 without buying ads: keep going.
