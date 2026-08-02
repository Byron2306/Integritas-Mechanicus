# Sophia Evaluation Hardening Addendum

Generated: 2026-07-30T19:39Z

## Critique Addressed

This addendum responds to the mutation/ablation/evaluator critique supplied after the first master bundle. The critique was correct: the original Matrix Gauntlet used a fixed hand-authored mutation corpus, mostly single-variable ablations, and a deterministic Mandos checker that had not been red-teamed against keyword spoofing.

## Implemented Changes

- Added generator-based mutation functions in `scripts/sophia_matrix_gauntlet.py`: lexical noise, semantic euphemism, adversarial authority override, evidence degradation, infrastructure pressure, encoding/obfuscation, and multi-turn transcript-style escalation.
- Preserved the original `MUTATED_CASES` as a seed corpus mode, but added `--mutation-mode generative` and `--mutation-mode stacked`.
- Added reproducibility controls: `--mutation-samples`, `--mutation-seed`, `--stack-min`, and `--stack-max`.
- Added mutation stacking so multiple pressure families can compose in one prompt.
- Added compound and degraded ablations: partial document, noisy OCR document, missing second source, no-document plus no-repair, no-document plus memory/world-event ablations, and all-off.
- Added per-condition degradation curves in the matrix summary: by provider, mutation, ablation, fault, and risk family, including pass rate, false-release rate, false-hold rate, repair rate, and latency.
- Added `scripts/mandos_checker_redteam.py` to test the deterministic Mandos checker against keyword-stuffed false positives.
- Hardened `arda_os/backend/services/mandos_protocol_judge.py` against three spoof classes: polished-answer takeover hidden behind refusal keywords, empty pedagogy shells, and source-entailment overclaims.
- Updated the master summary wording so the old “multimodal hardening” claim is described more honestly as OCR-absence/OCR-degradation hardening, not broad pixel-level multimodal reasoning.

## New Verification Runs

- Mandos checker red-team before hardening: `3/4` false passes. Artifact: `evidence/mandos_checker_redteam/mandos_checker_redteam_20260730T193640Z.json`.
- Mandos checker red-team after hardening: `4/4` correct, zero false passes, zero false fails. Artifact: `evidence/mandos_checker_redteam/mandos_checker_redteam_20260730T193724Z.json`.
- Stacked generated mutation smoke: `2/2` pass, zero false releases/holds. Artifact: `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193805Z_b31caf13d8c4ffaa.json`.
- Partial-document degraded ablation smoke: `1/1` pass, zero false releases/holds. Artifact: `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193822Z_9a879120024cc840.json`.
- Compound no-document/no-article-repair ablation smoke: proof contract failed as expected, zero false releases/holds. Artifact: `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193840Z_3c3b26e72e39b38a.json`.

## Remaining Caveat

The harness is now structurally stronger, but this still does not replace large-n runs or independent human/LLM judging. The next strongest move is a cost-controlled overnight matrix using `--mutation-mode stacked --mutation-samples 3+ --ablations all` over the six live remote providers, followed by manual review or a second judge on a stratified response sample.
