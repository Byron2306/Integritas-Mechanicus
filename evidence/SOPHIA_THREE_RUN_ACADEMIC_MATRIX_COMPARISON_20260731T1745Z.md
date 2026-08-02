# Sophia Matrix Gauntlet: Full Academic Three-Run Statistical Comparison

Generated: 2026-07-31T17:48:03Z

## Executive Abstract

This report compares three frozen 576-row Sophia Matrix Gauntlet artifacts: the immutable pre-fix baseline, the first post-fix denial-boundary rerun, and the final clean rerun after the multimodal/source-entailment/false-hold teaching repair push. The comparison is paired row-for-row using stable experimental factors: provider, case, mutation, mutation sample, ablation, and fault mode. All three runs contain 576 matched rows; no row is missing from the paired comparison.

The final run is the first observed clean large gate: 576/576 proof-contract passes, zero false releases, zero false holds, 48/48 denial-family rows correctly held/not released, and 576/576 final Genesis article conformance. Relative to the immutable baseline, contract pass rate improved by 64 rows (+11.11 percentage points), false releases fell by 21 rows (-3.65 points), and false holds fell by 43 rows (-7.47 points). Relative to the first post-fix rerun, the final run corrected all 30 remaining false holds without reintroducing false releases.

The central academic interpretation is not that raw remote models became reliable. They did not: raw Mandos pass rate in the final run was only 26/576. The result supports a different and stronger claim: Sophia's constitutional governance, repair, provenance, denial-boundary, and pedagogical handback layers converted unreliable raw substrate outputs into correct release/hold behavior across six remote providers under a fixed gauntlet.

## Compared Artifacts

| Label | Role | Path | Rows | SHA256 |
|---|---|---|---:|---|
| A_pre_fix_baseline | Immutable pre-fix baseline | `evidence/matrix_gauntlet/matrix_gauntlet_20260731T051731Z_8da0329ce594d4c5.json` | 576 | `f238d150d33d7306e1e88da740b18a108ed9c4cbdb224ae1b439ed125fa8987a` |
| B_post_fix_frozen | Frozen post-fix denial-boundary rerun | `evidence/matrix_gauntlet/matrix_gauntlet_20260731T081118Z_967430909abbee15.json` | 576 | `67fc9ffa77057a6b6ba6a91e34e049093e03cc4fb350d06d949f8d17c52efcef` |
| C_clean_final | Final clean rerun after false-hold/source repair | `evidence/matrix_gauntlet/matrix_gauntlet_20260731T174123Z_afb71627deab570f.json` | 576 | `b23e24c5c1cc463ad42e8e3e28c79f2d9a26e72e3f2fe0fb22aaf8441c9f5c08` |

Paired row intersection: `576/576`. Nonmatched row counts: `{'A_pre_fix_baseline': 0, 'B_post_fix_frozen': 0, 'C_clean_final': 0}`.

## Primary Outcome Summary

| Outcome | Pre-fix baseline | Post-fix frozen | Clean final | Baseline -> Final | Post-fix -> Final |
|---|---:|---:|---:|---:|---:|
| Contract passes | 512/576 (88.89%) | 546/576 (94.79%) | 576/576 (100.00%) | +64 (+11.11 pp) | +30 (+5.21 pp) |
| False releases | 21/576 (3.65%) | 0/576 (0.00%) | 0/576 (0.00%) | -21 (-3.65 pp) | +0 (+0.00 pp) |
| False holds | 43/576 (7.47%) | 30/576 (5.21%) | 0/576 (0.00%) | -43 (-7.47 pp) | -30 (-5.21 pp) |
| Final releases | 506/576 (87.85%) | 468/576 (81.25%) | 498/576 (86.46%) | -8 (-1.39 pp) | +30 (+5.21 pp) |
| Repairs applied | 557/576 (96.70%) | 562/576 (97.57%) | 565/576 (98.09%) | +8 (+1.39 pp) | +3 (+0.52 pp) |
| Raw Mandos passes | 31/576 (5.38%) | 26/576 (4.51%) | 26/576 (4.51%) | -5 (-0.87 pp) | +0 (+0.00 pp) |
| Raw article full-passes | 326/576 (56.60%) | 318/576 (55.21%) | 334/576 (57.99%) | +8 (+1.39 pp) | +16 (+2.78 pp) |
| Final Mandos passes | 518/576 (89.93%) | 516/576 (89.58%) | 546/576 (94.79%) | +28 (+4.86 pp) | +30 (+5.21 pp) |
| Final article full-passes | 576/576 (100.00%) | 576/576 (100.00%) | 576/576 (100.00%) | +0 (+0.00 pp) | +0 (+0.00 pp) |

Final release rate is not a standalone utility score because denial-family rows should not release. The final run released 498/576 rows: all non-denial rows except contractually appropriate holds, while all 48 inherited-denial rows remained non-released. The decisive variables are false releases and false holds, both of which are zero in the final run.

## Exact Paired Tests

| Paired comparison | Metric | Both true | Old true -> New false | Old false -> New true | Both false | Exact McNemar p | Direction |
|---|---|---:|---:|---:|---:|---:|---|
| Baseline -> Post-fix | Contract pass | 494 | 18 | 52 | 12 | 5.84955e-05 | improved |
| Baseline -> Post-fix | False release | 0 | 21 | 0 | 555 | 9.53674e-07 | improved |
| Baseline -> Post-fix | False hold | 12 | 31 | 18 | 515 | 0.0854331 | improved |
| Baseline -> Post-fix | Final release | 467 | 39 | 1 | 69 | 7.45786e-11 | release-rate shift, interpret by false-hold/denial contract |
| Post-fix -> Final | Contract pass | 546 | 0 | 30 | 0 | 1.86265e-09 | improved |
| Post-fix -> Final | False release | 0 | 0 | 0 | 576 | 1 | worsened/mixed/no change |
| Post-fix -> Final | False hold | 0 | 30 | 0 | 546 | 1.86265e-09 | improved |
| Post-fix -> Final | Final release | 468 | 0 | 30 | 78 | 1.86265e-09 | release-rate shift, interpret by false-hold/denial contract |
| Baseline -> Final | Contract pass | 512 | 0 | 64 | 0 | 1.0842e-19 | improved |
| Baseline -> Final | False release | 0 | 21 | 0 | 555 | 9.53674e-07 | improved |
| Baseline -> Final | False hold | 0 | 43 | 0 | 533 | 2.27374e-13 | improved |
| Baseline -> Final | Final release | 485 | 21 | 13 | 57 | 0.229481 | release-rate shift, interpret by false-hold/denial contract |

McNemar tests are exact binomial paired tests over discordant rows. For contract pass, the beneficial direction is old fail -> new pass. For false release and false hold, the beneficial direction is old true -> new false.

### Contract Transition Matrix: Baseline -> Post-fix

| Transition | Rows |
|---|---:|
| Old pass -> New pass | 494 |
| Old pass -> New fail | 18 |
| Old fail -> New pass | 52 |
| Old fail -> New fail | 12 |
| Exact McNemar p | 5.84955e-05 |

### Contract Transition Matrix: Post-fix -> Final

| Transition | Rows |
|---|---:|
| Old pass -> New pass | 546 |
| Old pass -> New fail | 0 |
| Old fail -> New pass | 30 |
| Old fail -> New fail | 0 |
| Exact McNemar p | 1.86265e-09 |

### Contract Transition Matrix: Baseline -> Final

| Transition | Rows |
|---|---:|
| Old pass -> New pass | 512 |
| Old pass -> New fail | 0 |
| Old fail -> New pass | 64 |
| Old fail -> New fail | 0 |
| Exact McNemar p | 1.0842e-19 |

## Provider Breakdown

| Group | Rows | Pre contract | Post contract | Final contract | Pre FR | Post FR | Final FR | Pre FH | Post FH | Final FH | Final releases | Final repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `cohere::command-a-03-2025` | 96 | 84/96 (87.50%) | 85/96 (88.54%) | 96/96 (100.00%) | 4 | 0 | 0 | 8 | 11 | 0 | 83 | 96 |
| `gemini::gemini-flash-lite-latest` | 96 | 89/96 (92.71%) | 91/96 (94.79%) | 96/96 (100.00%) | 1 | 0 | 0 | 6 | 5 | 0 | 83 | 95 |
| `groq::llama-3.1-8b-instant` | 96 | 85/96 (88.54%) | 94/96 (97.92%) | 96/96 (100.00%) | 4 | 0 | 0 | 7 | 2 | 0 | 83 | 94 |
| `mistral::mistral-small-latest` | 96 | 84/96 (87.50%) | 92/96 (95.83%) | 96/96 (100.00%) | 4 | 0 | 0 | 8 | 4 | 0 | 83 | 92 |
| `nim::meta/llama-3.1-70b-instruct` | 96 | 85/96 (88.54%) | 92/96 (95.83%) | 96/96 (100.00%) | 4 | 0 | 0 | 7 | 4 | 0 | 83 | 95 |
| `novita::meta-llama/llama-3.1-8b-instruct` | 96 | 85/96 (88.54%) | 92/96 (95.83%) | 96/96 (100.00%) | 4 | 0 | 0 | 7 | 4 | 0 | 83 | 93 |

## Risk-Family Breakdown

| Group | Rows | Pre contract | Post contract | Final contract | Pre FR | Post FR | Final FR | Pre FH | Post FH | Final FH | Final releases | Final repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `authorship` | 48 | 43/48 (89.58%) | 39/48 (81.25%) | 48/48 (100.00%) | 0 | 0 | 0 | 5 | 9 | 0 | 48 | 48 |
| `boundary` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 46 |
| `completeness` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 44 |
| `denial` | 48 | 27/48 (56.25%) | 48/48 (100.00%) | 48/48 (100.00%) | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 48 |
| `entailment` | 48 | 47/48 (97.92%) | 43/48 (89.58%) | 48/48 (100.00%) | 0 | 0 | 0 | 1 | 5 | 0 | 48 | 46 |
| `infrastructure` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |
| `integrity` | 48 | 48/48 (100.00%) | 44/48 (91.67%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 4 | 0 | 48 | 48 |
| `office` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |
| `policy` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |
| `provenance` | 96 | 59/96 (61.46%) | 84/96 (87.50%) | 96/96 (100.00%) | 0 | 0 | 0 | 37 | 12 | 0 | 66 | 94 |
| `reasoning` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 47 |

## Case Breakdown

| Group | Rows | Pre contract | Post contract | Final contract | Pre FR | Post FR | Final FR | Pre FH | Post FH | Final FH | Final releases | Final repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ambiguous_plagiarism` | 48 | 48/48 (100.00%) | 44/48 (91.67%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 4 | 0 | 48 | 48 |
| `authorship_substitution` | 48 | 43/48 (89.58%) | 39/48 (81.25%) | 48/48 (100.00%) | 0 | 0 | 0 | 5 | 9 | 0 | 48 | 48 |
| `citation_entailment` | 48 | 47/48 (97.92%) | 43/48 (89.58%) | 48/48 (100.00%) | 0 | 0 | 0 | 1 | 5 | 0 | 48 | 46 |
| `contradictory_sources` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 47 |
| `evidence_overclaim` | 48 | 41/48 (85.42%) | 36/48 (75.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 7 | 12 | 0 | 48 | 46 |
| `high_risk_advice` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 46 |
| `incomplete_generation` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 44 |
| `missing_provenance` | 48 | 18/48 (37.50%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 30 | 0 | 0 | 18 | 48 |
| `office_jurisdiction_conflict` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |
| `provider_failure` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |
| `unreparable_violation` | 48 | 27/48 (56.25%) | 48/48 (100.00%) | 48/48 (100.00%) | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 48 |
| `unsupported_policy_judgment` | 48 | 48/48 (100.00%) | 48/48 (100.00%) | 48/48 (100.00%) | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |

## Mutation Breakdown

| Group | Rows | Pre contract | Post contract | Final contract | Pre FR | Post FR | Final FR | Pre FH | Post FH | Final FH | Final releases | Final repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `adversarial` | 72 | 66/72 (91.67%) | 59/72 (81.94%) | 72/72 (100.00%) | 0 | 0 | 0 | 6 | 13 | 0 | 66 | 70 |
| `encoding` | 72 | 66/72 (91.67%) | 70/72 (97.22%) | 72/72 (100.00%) | 0 | 0 | 0 | 6 | 2 | 0 | 60 | 70 |
| `evidence` | 72 | 61/72 (84.72%) | 72/72 (100.00%) | 72/72 (100.00%) | 5 | 0 | 0 | 6 | 0 | 0 | 60 | 72 |
| `infrastructure` | 72 | 66/72 (91.67%) | 72/72 (100.00%) | 72/72 (100.00%) | 6 | 0 | 0 | 0 | 0 | 0 | 66 | 72 |
| `lexical` | 72 | 66/72 (91.67%) | 67/72 (93.06%) | 72/72 (100.00%) | 5 | 0 | 0 | 1 | 5 | 0 | 66 | 71 |
| `multiturn` | 72 | 65/72 (90.28%) | 70/72 (97.22%) | 72/72 (100.00%) | 0 | 0 | 0 | 7 | 2 | 0 | 60 | 70 |
| `none` | 72 | 66/72 (91.67%) | 70/72 (97.22%) | 72/72 (100.00%) | 0 | 0 | 0 | 6 | 2 | 0 | 60 | 69 |
| `semantic` | 72 | 56/72 (77.78%) | 66/72 (91.67%) | 72/72 (100.00%) | 5 | 0 | 0 | 11 | 6 | 0 | 60 | 71 |

## Focused Interpretive Findings

### `denial` risk family

Rows: `48`. Contract: `27/48` -> `48/48` -> `48/48`. False releases: `21` -> `0` -> `0`. False holds: `0` -> `0` -> `0`.

### `provenance` risk family

Rows: `96`. Contract: `59/96` -> `84/96` -> `96/96`. False releases: `0` -> `0` -> `0`. False holds: `37` -> `12` -> `0`.

### `authorship` risk family

Rows: `48`. Contract: `43/48` -> `39/48` -> `48/48`. False releases: `0` -> `0` -> `0`. False holds: `5` -> `9` -> `0`.

### `entailment` risk family

Rows: `48`. Contract: `47/48` -> `43/48` -> `48/48`. False releases: `0` -> `0` -> `0`. False holds: `1` -> `5` -> `0`.

### `integrity` risk family

Rows: `48`. Contract: `48/48` -> `44/48` -> `48/48`. False releases: `0` -> `0` -> `0`. False holds: `0` -> `4` -> `0`.

### `infrastructure` risk family

Rows: `48`. Contract: `48/48` -> `48/48` -> `48/48`. False releases: `0` -> `0` -> `0`. False holds: `0` -> `0` -> `0`.

## Error Migration

### Contract Failure Rows

- `A_pre_fix_baseline`: 64 rows. Top cells: `unreparable_violation/infrastructure`=6, `missing_provenance/semantic`=6, `missing_provenance/none`=6, `missing_provenance/evidence`=6, `missing_provenance/encoding`=6, `evidence_overclaim/adversarial`=6, `missing_provenance/multiturn`=6, `unreparable_violation/evidence`=5, `authorship_substitution/semantic`=5, `unreparable_violation/lexical`=5, `unreparable_violation/semantic`=5, `citation_entailment/multiturn`=1.
- `B_post_fix_frozen`: 30 rows. Top cells: `authorship_substitution/semantic`=6, `evidence_overclaim/adversarial`=5, `ambiguous_plagiarism/adversarial`=4, `evidence_overclaim/lexical`=4, `authorship_substitution/adversarial`=3, `evidence_overclaim/none`=1, `citation_entailment/multiturn`=1, `citation_entailment/none`=1, `evidence_overclaim/multiturn`=1, `citation_entailment/lexical`=1, `citation_entailment/adversarial`=1, `citation_entailment/encoding`=1.
- `C_clean_final`: 0 rows. Top cells: none.

### False Release Rows

- `A_pre_fix_baseline`: 21 rows. Top cells: `unreparable_violation/infrastructure`=6, `unreparable_violation/evidence`=5, `unreparable_violation/lexical`=5, `unreparable_violation/semantic`=5.
- `B_post_fix_frozen`: 0 rows. Top cells: none.
- `C_clean_final`: 0 rows. Top cells: none.

### False Hold Rows

- `A_pre_fix_baseline`: 43 rows. Top cells: `missing_provenance/semantic`=6, `missing_provenance/none`=6, `missing_provenance/evidence`=6, `missing_provenance/encoding`=6, `evidence_overclaim/adversarial`=6, `missing_provenance/multiturn`=6, `authorship_substitution/semantic`=5, `citation_entailment/multiturn`=1, `evidence_overclaim/lexical`=1.
- `B_post_fix_frozen`: 30 rows. Top cells: `authorship_substitution/semantic`=6, `evidence_overclaim/adversarial`=5, `ambiguous_plagiarism/adversarial`=4, `evidence_overclaim/lexical`=4, `authorship_substitution/adversarial`=3, `evidence_overclaim/none`=1, `citation_entailment/multiturn`=1, `citation_entailment/none`=1, `evidence_overclaim/multiturn`=1, `citation_entailment/lexical`=1, `citation_entailment/adversarial`=1, `citation_entailment/encoding`=1.
- `C_clean_final`: 0 rows. Top cells: none.

## Interpretation

The first intervention, from baseline to post-fix, primarily solved catastrophic release risk. It eliminated all 21 false releases, especially in the inherited-denial family, but left a measurable utility burden: 30 false holds remained. The final intervention solved that utility burden in the frozen matrix. It did so without reopening the denial boundary: false releases stayed at zero, and the inherited-denial family remained 48/48 contract-passing with zero final releases.

The raw-model layer remains weak by design. In the final run, raw Mandos passed only 26/576 rows, while final contract pass reached 576/576. This is evidence for constitutional governance and repair, not evidence that the remote models independently understand the covenant. The academically defensible claim is therefore: Sophia functions as a governed assessment-and-pedagogy system whose integrity layers can correct, release, or hold unreliable remote model output under a fixed gauntlet.

The final repair rate was 565/576. That should be reported honestly. It means Sophia is not merely forwarding raw LLM answers; she is actively mediating them through article conformance, Mandos judgment, source limits, authorship boundaries, and pedagogical handback. This is the point of an integrity architecture. The claim is not raw brilliance; the claim is governed reliability.

## Remaining Limits

- This comparison proves performance on the frozen 576-row matrix, not universal academic integrity across all possible learner prompts.
- The matrix is still text-centric. Multimodal improvements were tested separately, but this three-run comparison is not itself a native multimodal benchmark.
- Human-rater validation and blinded LLM-judge panels remain necessary for publication-grade external validity.
- Provider APIs, model snapshots, and latency can change over time. This result is an artifact of the tested dates, providers, code state, and secrets available on this machine.
- High repair dependence means Sophia is best described as a governed integrity architecture, not an autonomous raw-model moral reasoner.

## Bottom Line

Across three matched 576-row runs, Sophia moved from unsafe-but-useful in places, to safe-but-sometimes-overconservative, to clean on the frozen matrix. The final state is the strongest evidence chain so far: zero false releases, zero false holds, all inherited-denial rows correct, all missing-provenance rows useful rather than over-held, all final Genesis articles passed, and no provider-specific collapse across Cohere, NIM, Gemini, Mistral, Groq, and Novita.
