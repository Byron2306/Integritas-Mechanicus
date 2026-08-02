# Sophia Stratified/Judge/Multimodal Push

Generated: 2026-07-30T20:20Z

## What Changed

This push targeted three methodological gaps:

- Larger stratified protocol sampling.
- Raw/repaired/released metric separation.
- Judge-panel scaffolding with inter-rater reliability.
- Native multimodal honesty through OCR-disagreement cases.

## Code Changes

### Protocol Harness

File: `scripts/sophia_protocol_harness.py`

Added:

- `stratified` suite.
- Round-robin stratification across v1.1, v1.2, pedagogy, and multimodal cases before applying `--limit`.
- Wilson 95% intervals on pass rates.
- `claim_strength` labels.
- `failure_taxonomy`.
- `stage_metrics` for raw, repair, and released stages.
- Two native-multimodal-gap cases:
  - `MM_OCR_USER_DESCRIPTION_CONFLICT`.
  - `MM_OCR_CAPTION_NUMERIC_CONFLICT`.

Important honesty note:

These are not native pixel-vision tests. They are OCR/transcript disagreement tests that prove Sophia can detect and govern conflict between inspectable OCR and unverified visual/user/caption claims.

### Presence / Mandos

Files:

- `arda_os/backend/services/presence_server.py`
- `arda_os/backend/services/mandos_protocol_judge.py`

Added:

- Bounded responses for OCR-vs-user-description disagreement.
- Bounded responses for OCR-vs-caption numeric conflict.
- Explicit native-vision/pixel-inspection limits.
- Clearer entailment phrasing: OCR conflict does not prove n=180, institution-wide success, or stronger conclusions.
- Fairer Mandos entailment triggering, so ordinary audit language does not create false `source_entailment_humility` failures.

### Judge Panel

File: `scripts/sophia_judge_panel.py`

Added:

- Blinded item IDs and prompt/response hashes.
- Four local rubric-style judges:
  - `integrity_boundary`.
  - `evidence_entailment`.
  - `pedagogy_substance`.
  - `multimodal_humility`.
- Applicability-aware ratings so task-specialist judges do not distort unrelated cases.
- External human/LLM judge JSONL import path.
- Panel/original disagreement reporting.
- Fleiss-style kappa and raw agreement.

### Audit Compiler

File: `scripts/sophia_evidence_audit.py`

Added:

- Judge-panel collection.
- Latest judge-panel summary included under Independent Evaluators.

## New Evidence

### Expanded Multimodal

Artifact:

`evidence/phase5_protocol_runs/phase5_multimodal_full_20260730T201337Z.json`

Result:

- Total: 7.
- Passes: 7.
- Pass rate: 1.0.
- 95% Wilson CI: 0.6457 to 1.0.
- Claim strength: `clean_micro_probe`.

Breakdown:

- `multimodal_hardening`: 2/2.
- `visual_evidence_reasoning`: 3/3.
- `native_multimodal_disagreement`: 2/2.

### Stratified Sample

Artifact:

`evidence/phase5_protocol_runs/phase5_stratified_full_20260730T201619Z.json`

Result:

- Total: 28.
- Passes: 28.
- Pass rate: 1.0.
- 95% Wilson CI: 0.8794 to 1.0.
- Claim strength: `clean_engineering_gate`.

Breakdown:

- `stratified_v1_1`: 7/7.
- `stratified_v1_2`: 7/7.
- `stratified_pedagogy_office_routing`: 7/7.
- `stratified_multimodal_hardening`: 2/2.
- `stratified_visual_evidence_reasoning`: 3/3.
- `stratified_native_multimodal_disagreement`: 2/2.

### Judge Panel

Artifact:

`evidence/judge_panel/sophia_judge_panel_20260730T201819Z.json`

Result:

- Items: 35.
- Judgments: 140.
- Panel passes: 35.
- Original passes: 35.
- Panel/original disagreements: 0.
- Raw agreement: 0.9714.
- Applicability-aware agreement: 0.913.

Kappa note:

Kappa remains low/unstable because almost all applicable ratings are passes. This is a known prevalence issue. For this run, raw agreement and zero panel/original disagreements are more interpretable than kappa alone.

### Refreshed Audit

Artifacts:

- `evidence/audit/sophia_evidence_audit_20260730T201857Z.json`
- `evidence/audit/sophia_evidence_audit_20260730T201857Z.md`

Audit conclusion remains appropriately cautious:

- Engineering case-study readiness: `credible_but_small_n`.
- Peer-reviewed outcomes claim: `not_ready_without_large_n_blinded_and_longitudinal_study`.

## Honest Status After This Push

Improved:

- Stratification is now real, not just sequential slicing.
- Stage metrics are separated.
- OCR/native-vision disagreement handling exists and passes.
- Judge-panel infrastructure exists and can ingest human/LLM judges.
- Audit layer now includes panel evidence.

Still not solved:

- Native pixel-level multimodal perception is not implemented.
- The stratified sample is 28 cases, not a large-N study.
- Judge panel is local deterministic unless external human/LLM JSONL is supplied.
- Kappa is not yet strong because the panel needs more balanced positive/negative cases.
- Raw model metrics remain sparse for native deterministic response paths because many paths bypass raw generation by design.

Best defensible claim:

Sophia now has a stronger methodological evidence chain: controlled protocol gates, stratified mixed sampling, OCR-disagreement multimodal governance, separated release-stage telemetry, and a blinded judge-panel scaffold. This is a credible engineering case-study foundation, not yet a final academic outcomes proof.

