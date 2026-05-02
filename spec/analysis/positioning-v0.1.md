# PRML v0.1 — Positioning

**Question:** Why is PRML not just `<insert existing thing>`?

This document answers it once, against every neighbor we have heard cited. It is intentionally short. The full spec is at [spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1); the preprint is at the same URL when arXiv assigns an ID.

---

## The two axes

PRML lives in the intersection of two axes:

1. **When was the claim committed?** *Before* the experiment, or *after*.
2. **What is trusted to attest the commitment?** A *registrar* (a third party, e.g. ClinicalTrials.gov), or *arithmetic* (a hash anyone can recompute).

Plotted:

|                          | **Registrar-trusted**                | **Arithmetic-verifiable**          |
|---                       |---                                   |---                                 |
| **Pre-experiment**       | ClinicalTrials.gov, OSF, AEA registry | **PRML**                           |
| **Post-hoc**             | (n/a — no commitment)                 | in-toto, SLSA, Sigstore (build provenance) |
| **No commitment at all** | Model cards, datasheets, HELM, leaderboards | (n/a)                          |

The bottom-right cell — *post-hoc, arithmetic-verifiable* — is occupied by the build/supply-chain world. The top-right cell — *pre-experiment, arithmetic-verifiable, ML-shaped* — is what PRML occupies. To the best of our review, no existing artifact lives in that cell.

---

## TL;DR matrix

| System                       | Phase           | Trust model    | Domain                  | Binding granularity         |
|---                           |---              |---             |---                      |---                          |
| **PRML**                     | Pre-experiment  | Cryptographic  | ML evaluation claims    | Single (metric, threshold, dataset, seed) tuple |
| ClinicalTrials.gov           | Pre-experiment  | Registrar      | Clinical trials         | Trial protocol             |
| OSF Preregistration          | Pre-experiment  | Registrar      | General empirical       | Hypothesis + analysis plan |
| AEA RCT Registry             | Pre-experiment  | Registrar      | Economics RCTs          | Trial protocol             |
| in-toto / SLSA               | Post-hoc        | Cryptographic  | Build provenance        | Build artifact + steps     |
| Sigstore / Cosign            | Post-hoc        | Cryptographic  | Artifact signing        | Single artifact            |
| TUF                          | Continuous      | Cryptographic  | Software updates        | Update metadata            |
| Model Cards                  | Post-hoc        | None           | Model documentation     | Whole model                |
| Datasheets for Datasets      | Post-hoc        | None           | Dataset documentation   | Whole dataset              |
| HELM / BIG-bench             | Post-hoc        | None           | Eval harness            | Benchmark run              |
| Papers with Code             | Post-hoc        | None           | Leaderboards            | Paper-level claim          |
| ML Reproducibility Challenge | Post-hoc        | Reviewer trust | Replication             | Whole paper                |

---

## Each neighbor, in one paragraph

### in-toto / SLSA / Sigstore / TUF — the supply-chain family

These are the closest precedents. They cryptographically bind build provenance to artifacts: *"this binary was built from this source by this builder."* PRML applies the same content-addressing pattern to a **different artifact**: an evaluation claim. SLSA tells you what produced the binary; PRML tells you what was promised about the binary's behaviour, before it was tested. Both are valuable; they are complementary, not substitutes. The PRML preprint cites in-toto as the closest precedent and explicitly positions PRML as the evaluation-side analog.

**Why PRML is not just SLSA for ML:** SLSA's primitive is "this artifact came from this source." PRML's primitive is "this metric, threshold, and dataset were committed before this artifact was tested against them." Different question, different fields, different verifier.

### Model Cards (Mitchell et al. 2019)

Post-hoc disclosure. A model card describes what was built — intended use, limitations, training data, evaluation results. It does not bind any of those values to a hash. A model card can be edited after the evaluation is observed; nothing in the card's structure prevents threshold drift, slice selection, or silent re-runs. PRML sits **underneath** model cards as the cryptographic floor; a model card cites a PRML manifest hash in the same way a paper cites a DOI.

**Why PRML is not just a model card field:** model cards are a documentation format, not a commitment format. They report. PRML commits.

### Datasheets for Datasets (Gebru et al. 2018)

Same shape, dataset-side. Documents who labeled, when, with what consent. Does not produce a hash, does not pre-commit to anything. PRML's `dataset.id` and `dataset.hash` fields integrate with the artifact a datasheet describes; the two compose cleanly.

### HELM / BIG-bench / Papers with Code

These are evaluation harnesses or leaderboards. They standardize the *measurement* (which prompts, which decoding, which scoring), but the choice of metric, threshold, and reporting still occurs at evaluation time. A leaderboard entry is what a researcher chose to publish; nothing in the leaderboard prevents republishing under a different threshold next month. PRML pre-commits the (metric, threshold) tuple before any leaderboard entry is computed; the leaderboard then becomes a directory of *verified claims*, not a directory of *posted numbers*.

**Why PRML is not just a leaderboard:** leaderboards rank what was reported. PRML ranks what was *committed and verified*.

### ML Reproducibility Challenge (Pineau et al. 2021)

A community-driven post-hoc effort to re-run published experiments. Excellent and necessary, but downstream of the publication. The MLRC report says *"we tried to reproduce paper X and got 87% instead of 91%."* It cannot say *"the team's threshold was tuned post-hoc"* unless the team confessed; the structure of the publication does not preserve the evidence. PRML produces that evidence as a side effect of normal authoring.

### ClinicalTrials.gov / OSF / AEA Registry

Pre-registration in the social-science and clinical-trials sense. The protocol is filed with a **registrar** (a trusted third party) before data collection begins, and the registrar timestamps the filing. PRML moves the trust from the registrar to the hash: a verifier needs only the manifest, the dataset, and a SHA-256 implementation; no registrar is required. That makes PRML deployable in air-gapped labs, in regulator-only environments, in 2046, with no dependence on any institution surviving.

**Why PRML is not just a clinical-trials registry for ML:** because there is no registrar in PRML. The registrar layer is replaced by content addressing. This is the same simplification IPFS made for files and Git made for source code.

### Git / IPFS

Both are content-addressed systems for files. Neither addresses *claims about behaviour*. A Git commit hash binds source bytes; a PRML hash binds an evaluation contract. Git is to source what PRML is to evaluation claims; the analogy is structural, not semantic.

### W&B / MLflow / Neptune / Comet

Experiment trackers. Excellent for the production loop (logging metrics, comparing runs, sharing dashboards), but their internal hashing is not a published commitment surface. A team can log 50 runs to MLflow and choose to publish run #37; no third party can detect that selection from MLflow's hash chain alone, because the trail is private. PRML is the *publishable* surface; experiment trackers stay where they are, and reference PRML manifest hashes when they publish externally.

---

## The intersection map

The space PRML occupies has three coordinates:

1. **Cryptographic, not registrar-trusted.** No trusted timestamping authority. Anyone with the manifest, the dataset, and SHA-256 can verify.
2. **Pre-experimental, not post-hoc.** The hash is computed and committed before the model is run against the dataset.
3. **ML-evaluation-shaped, not generic.** The format names *(metric, comparator, threshold, dataset hash, seed, producer)* — not *(source, builder, output)* like SLSA, not *(hypothesis, analysis plan)* like OSF, not *(intended use, training data)* like a model card.

To our review, no existing artifact occupies this intersection. PRML occupies it because the EU AI Act's August 2026 deadline will not be met by registrar-based pre-registration (registrars do not exist for ML at the scale required) and will not be met by post-hoc disclosure formats (they are not commitments). Cryptographic pre-registration is the cheapest way to satisfy the named obligations.

---

## Common confusions, cleared

> **"This is just a YAML file."**
> Yes. The contribution is the **canonicalization** plus the **binding** plus the **verifier protocol**, not the YAML itself. The format choice is documented in Appendix C of the preprint.

> **"This is just a hash."**
> SHA-256 is the primitive. The contribution is *what it is computed over* (a deterministic byte sequence derived from a logical mapping), *when it is computed* (before the experiment), and *what verifiers do with it* (a four-state verdict).

> **"Why not use blockchain?"**
> Because nothing in the use case requires distributed consensus, and adding a blockchain dependency would make the spec unrunnable in air-gapped environments. The chain hash is sufficient for the audit-trail requirement; on-chain anchoring is deliberately deferred (preprint §10.3).

> **"Why not use Git?"**
> Git is a possible *carrier* for PRML manifests, not a substitute. A Git commit binds source bytes, not evaluation contracts. Many teams will store `.prml.yaml` files in Git; this is fine and encouraged. Git's commit hash is not a substitute for the PRML hash because Git's serialization is not specified for cross-tool determinism.

> **"Why not use SLSA?"**
> SLSA tells you what produced the binary. PRML tells you what was committed about the binary's behaviour. Same family, different question. A mature ML deployment will have both: SLSA for the model artifact's provenance, PRML for the claims made about it.

> **"Is PRML enough on its own?"**
> No. PRML is a primitive. Model cards, datasheets, red-team reports, post-market monitoring, and signed delivery still need to sit above it. PRML is the cryptographic floor — the layer that makes the others *referable to a hash*.

---

## One sentence

> PRML is to ML evaluation claims what SLSA is to build artifacts and what ClinicalTrials.gov is to clinical trials — but neither registrar-based nor post-hoc, because the regulatory deadline does not allow either.

---

*Working draft v0.1, CC BY 4.0. Comments via [GitHub Discussions](https://github.com/studio-11-co/falsify/discussions/6) or `hello@studio-11.co`.*
