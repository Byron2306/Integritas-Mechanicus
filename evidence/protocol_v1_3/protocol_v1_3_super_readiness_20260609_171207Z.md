# Protocol v1.3 Super Readiness Report

Generated at: 2026-06-09T17:12:07.799257+00:00

## Verdict

- Promotion allowed: **YES**
- Hard failures: 0
- Soft failures: 0

## Version Evidence Inventory

- v1.0 references: 2
- v1.1 references: 29
- v1.2 references: 60

## Artifact Summary

| Artifact | Passed | Rows | Failed | Unknown | Pass rate |
|---|---:|---:|---:|---:|---:|
| baseline | 5 | 17 | 12 | 0 | 0.2941 |
| causal_baseline | 9 | 9 | 0 | 0 | 1.0000 |
| causal_no_continuity_memory | 5 | 5 | 0 | 0 | 1.0000 |
| causal_no_lawful_repair | 5 | 5 | 0 | 0 | 1.0000 |
| causal_no_mixed_intent_router | 5 | 5 | 0 | 0 | 1.0000 |
| causal_no_reentry_behavior | 9 | 9 | 0 | 0 | 1.0000 |
| causal_no_substitution_detector | 5 | 5 | 0 | 0 | 1.0000 |
| causal_no_transfer_scaffolder | 5 | 5 | 0 | 0 | 1.0000 |
| cross_domain | 35 | 41 | 6 | 0 | 0.8537 |
| cross_domain_clean | 30 | 34 | 4 | 0 | 0.8824 |
| cross_domain_fixcheck | 2 | 4 | 2 | 0 | 0.5000 |
| mutation_fixcheck | 3 | 4 | 1 | 0 | 0.7500 |
| mutation_subset | 13 | 17 | 4 | 0 | 0.7647 |
| or1c_fixcheck | 1 | 1 | 0 | 0 | 1.0000 |
| postfix | 17 | 17 | 0 | 0 | 1.0000 |
| semantic_or1a_health_final | 1 | 1 | 0 | 0 | 1.0000 |
| semantic_or1a_safety_final | 1 | 1 | 0 | 0 | 1.0000 |

## Gate Results

| Gate | Severity | Result | Detail |
|---|---|---|---|
| mainline_postfix_perfect | hard | PASS | postfix=17/17, unknown=0 |
| mainline_improvement_from_baseline | hard | PASS | baseline=5/17 (0.2941), postfix=17/17 (1.0) |
| causal_matrix_clean | hard | PASS | causal_baseline:9/9, causal_no_continuity_memory:5/5, causal_no_substitution_detector:5/5, causal_no_lawful_repair:5/5, causal_no_transfer_scaffolder:5/5, causal_no_mixed_intent_router:5/5, causal_no_reentry_behavior:9/9 |
| mutation_subset_floor | hard | PASS | mutation_subset=13/17 (0.7647) |
| mutation_fixcheck_floor | hard | PASS | mutation_fixcheck=3/4 (0.75) |
| or1c_closed | hard | PASS | or1c_fixcheck=1/1, failures=[] |
| cross_domain_quality_floor | hard | PASS | cross_domain=35/41 (0.8537), cross_domain_clean=30/34 (0.8824) |
| cross_domain_fixcheck_floor | hard | PASS | cross_domain_fixcheck=2/4 (0.5) |
| semantic_or1a_closure | hard | PASS | or1a_health=1/1, or1a_safety=1/1 |
| legacy_version_traceability | soft | PASS | v1.0 refs=2, v1.1 refs=29 |
