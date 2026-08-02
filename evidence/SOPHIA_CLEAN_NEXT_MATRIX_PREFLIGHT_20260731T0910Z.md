# Sophia Clean Next Matrix Preflight

Created: 2026-07-31T09:10Z

## Purpose

This pass fixed remaining multimodal/article-surface gaps and the last known false-hold dialect before the next larger matrix run.

The goal was not to broaden the matrix or change the contract. The goal was to remove known defects that would contaminate the next run:

- Multimodal responses needed explicit OCR/transcription/native-vision limits.
- Source-only document responses needed compact evidence-limit statements.
- Quote-only answers needed learner handback without losing exact quote anchoring.
- Mandos needed to recognize Sophia's actual override-refusal language.

## Code Changes

### `arda_os/backend/services/presence_server.py`

Hardened visual/document synthesis:

- Visual chart, caption-conflict, and diagram responses now state that Sophia is using OCR/transcription rather than independent native pixel vision.
- Source-only summaries now include an evidence-limit sentence even when the source mentions attendance or causality terms.
- Exact quote responses now include a compact limit plus learner-owned next move.
- Feedback-only revision help now explicitly states that Sophia can suggest a revision target/evidence check, but final wording remains human-owned.

### `arda_os/backend/services/mandos_protocol_judge.py`

Hardened refusal recognition:

- Added refusal markers for `refusing system override`, `override is denied`, and `system override is denied`.
- This fixes the observed false hold where Sophia safely refused a fake override but Mandos did not count the phrasing as a refusal.

## Verification

### Compile Check

Command:

```bash
python3 -m py_compile arda_os/backend/services/presence_server.py arda_os/backend/services/mandos_protocol_judge.py scripts/sophia_protocol_harness.py scripts/sophia_matrix_gauntlet.py
```

Result: passed.

### Multimodal Full Protocol

Artifact:

`evidence/phase5_protocol_runs/phase5_multimodal_full_20260731T085932Z.json`

Result:

| Metric | Result |
|---|---:|
| Protocol rows | 7/7 |
| Mandos released-stage passes | 7/7 |
| Article released-stage passes | 7/7 |
| Document grounded | 7/7 |

Interpretation:

The previous multimodal article gap is closed. OCR/native-vision disagreement rows remain clean.

### Stratified Smoke Gate

Artifact:

`evidence/phase5_protocol_runs/phase5_stratified_full_20260731T090206Z.json`

Result:

| Metric | Result |
|---|---:|
| Protocol rows | 20/20 |
| Mandos released-stage passes | 20/20 |
| Article released-stage passes | 20/20 |
| Document grounded | 20/20 |

Interpretation:

The previous article-surface misses in source summaries, exact quotes, and feedback-only rows are closed.

### Compact Gemini Matrix Preflight

Provider:

`gemini::gemini-flash-lite-latest`

Configuration:

- Mutations: all
- Ablation: `A0_full`
- Fault: `none`

Artifacts:

- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090311Z_181a302d9c13ac98.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090502Z_a122c72a4e02828c.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090558Z_cc9682c696f3ac99.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090654Z_81462cee3239c1fa.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090750Z_6bda238e90e228fd.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260731T090912Z_a6ef1715b97da6f0.json`

Results by family:

| Family | Rows | Contract Passes | False Releases | False Holds | Final Articles |
|---|---:|---:|---:|---:|---:|
| ambiguous_plagiarism | 8 | 8 | 0 | 0 | 8 |
| evidence_overclaim | 8 | 8 | 0 | 0 | 8 |
| citation_entailment | 8 | 8 | 0 | 0 | 8 |
| missing_provenance | 8 | 8 | 0 | 0 | 8 |
| unreparable_violation | 8 | 8 | 0 | 0 | 8 |
| authorship_substitution rerun | 8 | 8 | 0 | 0 | 8 |

Combined compact preflight:

| Metric | Result |
|---|---:|
| Rows | 48 |
| Contract passes | 48/48 |
| False releases | 0 |
| False holds | 0 |
| Final article full passes | 48/48 |

Important nuance:

`missing_provenance` remained contract-clean but conservative: some rows were not finally released because Sophia correctly held unresolved provenance. This is not scored as false hold under the current contract, but it should be watched in the full matrix because auditors may distinguish safe source-finding scaffolds from unresolved-provenance holds.

## Readiness Assessment

For the next full matrix, Sophia is now materially cleaner than before this push:

- Multimodal article gap closed.
- Stratified article gap closed.
- Known authorship-adversarial false hold closed.
- Denial boundary remained clean.
- Compact six-family Gemini preflight is 48/48 with zero false releases and zero false holds.

Remaining risk before the big run:

- Remote providers may phrase refusal/limits differently, so Mandos dialect coverage is still a live risk.
- NIM latency can still hold shards hostage unless sharding/checkpointing is used.
- Missing-provenance remains conservative by design; this is safe but may reduce final release rate.
- Raw model Mandos pass rates remain low in several families; Sophia's runtime governance is still doing most of the integrity work.

Verdict:

Sophia is ready for the next matrix rerun as a clean preflight state.
