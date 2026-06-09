# MERGER V5 OMEGA Convergence Report

Generated: 2026-06-09T17:17:26.334069+00:00

## Overall

- Promotion allowed: NO
- Score: 76 / 100 (76.0%)
- Hard failures: 2
- Soft failures: 0
- Mode: static

## Checks

| ID | Title | Severity | Result | Score | Detail |
|---|---|---|---|---:|---|
| M01 | MERGER root present | hard | PASS | 5/5 | C:\Users\User\source\repos\Sophia-AI-main\MERGER_KnowEdge-main |
| M02 | State model consistency | hard | PASS | 12/12 | missing_py=[]; missing_ts=[]; playbook_emergency=True |
| M03 | Control-plane schema and gate | hard | FAIL | 0/14 | missing_tables=[]; evidence_gate_present=True; transition_guard_present=False |
| M04 | API surface and stress alignment | hard | PASS | 10/10 | missing_routes=[]; missing_stress_refs=[] |
| M05 | Decision and audit ledger integrity | hard | PASS | 10/10 | decision_ledger=True; audit_ledger=True; run_controller_decisions=True |
| M06 | Pipeline contract convergence | hard | PASS | 12/12 | missing_targets=[]; routing_delay=True; missing_stages=[]; stage_delay=True |
| M07 | Security and policy guardrails | hard | FAIL | 0/10 | strict_policy=True; injection_scanner=True; url_block=False; pii_patterns=True |
| M08 | Integrity and citation engines | hard | PASS | 9/9 | missing_integrity=[]; missing_citation=[] |
| M09 | Packaging and runtime artifacts | soft | PASS | 9/9 | missing_files=[]; compose_services_ok=True |
| M10 | Documented capability coherence | soft | PASS | 9/9 | missing_tokens=[] |
