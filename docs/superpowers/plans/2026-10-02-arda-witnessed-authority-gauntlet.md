# ARDA Witnessed Authority Gauntlet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a live Valinor terminal gauntlet that proves `EXECUTION DOES NOT EQUAL AUTHORITY` using live Ainur witnesses, native post-quantum cryptography, a byte-identical allow/deny experiment, safe BPF LSM strict-mode enforcement, automatic rollback, and an independently verifiable sealed receipt.

**Architecture:** A single orchestrator drives a fixed witness sequence, collects live evidence into one immutable run context, asks Aulë to synthesize and seal the authority state, then arms a current-cgroup measured-execution experiment only after a no-new-exec rollback watchdog is ready. Manwë Herald releases the experiment only after the sealed state is lawful, Tulkas reports the actual kernel verdict, Vairë closes chronology, Lórien verifies recovery, and the run ends with a concise terminal summary plus canonical signed evidence.

**Tech Stack:** Python 3.13, existing ARDA Ainur inspectors/choir, `OsEnforcementService`, Valinor BPF LSM pinned maps, TPM evidence, `QuantumSecurityService` with native `liboqs` or `pqcrypto`, SHA-256/SHA3-256, pytest.

**Spec:** `docs/superpowers/specs/2026-10-02-arda-witnessed-authority-gauntlet-design.md`

## Global Constraints

- Presentation order is always **Tolkienism first → IT translation second → plain-English consequence third**.
- Native PQC is mandatory for the sovereign live gauntlet; simulation must refuse.
- Live witness output only; no canned witness verdicts.
- Aulë synthesizes the complete witness set before Manwë Herald can release manifestation.
- Manwë Herald may say **“You may be born.”** only after a lawful/harmonic sealed authority state exists.
- Tulkas reports the kernel’s real decision; it must never fabricate a deny.
- Positive and negative probes must be byte-identical.
- Strict mode must not arm until the current cgroup is bound to the active generation, the positive probe is projected, and rollback is ready.
- Rollback watchdog must exist before strict mode and must not depend on spawning a new executable.
- Any unexpected allow of the unauthorized probe is a failed gauntlet.
- Any failed rollback makes the gauntlet incomplete.
- PCR drift must be shown honestly; current PCR1 divergence must not be reported as green trust.
- No claim that BPF, TPM, Secure Boot, measured execution, PQC, or MAC are individually novel.
- No full JSON dumps in the live terminal; machine-readable detail goes to the receipt.

## Review Focus

- **Current-cgroup drift:** if the orchestrator changes cgroup identity after projection, strict mode must refuse before arming rather than lock out the operator. Covered in Task 4.
- **Native-PQC downgrade:** if `liboqs`/`pqcrypto` disappears or service mode is `simulation`, the gauntlet must refuse before any authority mutation. Covered in Task 2.
- **Witness disagreement or stale/replayed evidence:** Aulë must return withheld/vetoed and Manwë Herald must not release the experiment. Covered in Task 3.
- **Unexpected negative-probe allow:** if the kernel returns success, result must be FAIL and rollback must still execute. Covered in Task 5.
- **Rollback/watchdog failure:** if audit restoration cannot be verified, result must be INCOMPLETE and the process must not print a success banner. Covered in Task 6.

---

## File Structure

- Create `arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py` — thin CLI entry point and terminal rendering only.
- Create `arda_os/backend/services/witnessed_authority_gauntlet.py` — orchestration state machine, live evidence flow, experiment lifecycle, result model.
- Create `arda_os/backend/services/gauntlet_receipt.py` — canonical receipt construction, serialization, digesting, native-PQC signing and detached verification metadata.
- Create `arda_os/backend/services/strict_mode_watchdog.py` — pre-fork rollback watchdog that restores the pinned enforcement mode without spawning new executables.
- Modify `arda_os/backend/services/quantum_security.py` only if needed to expose an explicit native-signing interface that cannot silently fall back to simulation.
- Modify `arda_os/backend/services/manwe_herald.py` only if needed to add a narrow gauntlet release check that consumes an already-sealed authority result rather than re-running unrelated boot flow.
- Modify `arda_os/backend/services/os_enforcement_service.py` only for narrow read/write helpers already implied by the current pinned-map API, never to bypass existing policy semantics.
- Create `arda_os/backend/tests/test_witnessed_authority_gauntlet.py` — orchestration and presentation contract tests.
- Create `arda_os/backend/tests/test_gauntlet_strict_mode_safety.py` — cgroup binding, probe projection, watchdog, rollback and negative-control tests.
- Create `arda_os/backend/tests/test_gauntlet_receipt.py` — canonicalization, native-PQC refusal, signing and tamper-verification tests.

---

### Task 1: Terminal Grammar and Run Context

**Files:**
- Create: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Create: `arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py`
- Test: `arda_os/backend/tests/test_witnessed_authority_gauntlet.py`

**Interfaces:**
- Produces: `GauntletRunContext`, `GauntletResult`, `render_stage(title: str, technical: list[str], why: list[str]) -> str`, `main() -> int`.
- Consumes later tasks through injected service objects rather than constructing policy decisions in the renderer.

- [ ] **Step 1: Write the failing presentation-contract tests**

Add tests asserting that the opening contains `ARDA // VALINOR WITNESSED RUN`, `EXECUTION DOES NOT EQUAL AUTHORITY`, and the ASCII `witness → forge → herald → enforce` line; every witness stage renders Tolkien role/title before `TECHNICAL`, and `TECHNICAL` before `WHY IT MATTERS`.

- [ ] **Step 2: Run the focused test**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py`
Expected: FAIL because runner/context do not exist.

- [ ] **Step 3: Implement the minimal run context and renderer**

Define immutable-ish dataclasses for run identity, witness evidence digests, authority experiment state, recovery state, and final result. Keep terminal formatting in the script/renderer and policy logic in the service.

- [ ] **Step 4: Run the focused test**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py`
Expected: PASS for presentation/context tests.

- [ ] **Step 5: Commit**

```bash
git add arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_witnessed_authority_gauntlet.py
git commit -m "feat: add witnessed authority gauntlet shell"
```

---

### Task 2: Native PQC Preflight and Sealing Interface

**Files:**
- Modify: `arda_os/backend/services/quantum_security.py`
- Create: `arda_os/backend/services/gauntlet_receipt.py`
- Test: `arda_os/backend/tests/test_gauntlet_receipt.py`

**Interfaces:**
- Produces: `require_native_pqc() -> str`, `sign_native_pqc(key_id: str, payload: bytes) -> QuantumSignature`, `verify_native_pqc(public_key: str, payload: bytes, signature: str) -> bool`.
- Produces: `build_canonical_receipt(context: GauntletRunContext) -> bytes` and `seal_receipt(context, key_id) -> SealedGauntletReceipt`.

- [ ] **Step 1: Write failing tests for fail-closed PQC**

Assert that service mode `simulation` raises a sovereign refusal; `liboqs` or `pqcrypto` is accepted; receipt sealing refuses any simulated signature path; tampering with canonical receipt bytes makes verification false.

- [ ] **Step 2: Run receipt/PQC tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_receipt.py`
Expected: FAIL because native-only helpers do not exist.

- [ ] **Step 3: Add explicit native-only PQC helpers**

Expose a mode check that cannot silently fall back. Reuse the repository’s real provider path. Do not route sovereign sealing through the deterministic simulation signature helper.

- [ ] **Step 4: Implement canonical receipt sealing**

Canonicalize JSON with stable key ordering and separators, include provider/algorithm/key fingerprint, sign bytes once, and expose detached verification metadata.

- [ ] **Step 5: Run receipt/PQC tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_receipt.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/quantum_security.py \
        arda_os/backend/services/gauntlet_receipt.py \
        arda_os/backend/tests/test_gauntlet_receipt.py
git commit -m "feat: require native PQC for authority receipts"
```

---

### Task 3: Live Ainur Witness Chain, Aulë Synthesis, and Manwë Herald Gate

**Files:**
- Modify: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Modify: `arda_os/backend/services/manwe_herald.py` only if a narrow release hook is necessary
- Test: `arda_os/backend/tests/test_witnessed_authority_gauntlet.py`

**Interfaces:**
- Consumes existing `VardaInspector`, `VaireInspector`, `ManweInspector`, `UlmoInspector`, `MandosInspector`, `AuleInspector` and Secret Fire/Voice evidence.
- Produces: `collect_live_witnesses(context) -> list[AinurVerdict]`, `forge_authority_state(context, verdicts) -> AinurVerdict`, `herald_allowed(aule_verdict, sealed_receipt) -> bool`.

- [ ] **Step 1: Write failing witness-order and refusal tests**

Assert fixed order `varda, vaire, manwe, ulmo, mandos, aule`; missing witness causes Aulë `withheld`; stale/replayed Secret Fire causes veto; contradiction prevents herald; harmonic sealed state permits herald and renders `You may be born.`.

- [ ] **Step 2: Run witness tests**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py -k "witness or herald or aule"`
Expected: FAIL.

- [ ] **Step 3: Wire live inspector calls into the run context**

Use actual inspector outputs and evidence packets. Compute and store a digest for each witness packet. Do not substitute hard-coded verdicts.

- [ ] **Step 4: Feed the five prior verdicts into Aulë and require a sealed native-PQC state before heralding**

Preserve Aulë’s existing contradiction/freshness logic. The gauntlet layer must treat anything other than lawful/harmonic as no-release.

- [ ] **Step 5: Run witness tests**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py -k "witness or herald or aule"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/backend/services/manwe_herald.py \
        arda_os/backend/tests/test_witnessed_authority_gauntlet.py
git commit -m "feat: orchestrate live Ainur authority witnesses"
```

---

### Task 4: Safe Current-Cgroup Preparation and Byte-Identical Controls

**Files:**
- Modify: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Modify: `arda_os/backend/services/os_enforcement_service.py` only if existing helpers are insufficient
- Test: `arda_os/backend/tests/test_gauntlet_strict_mode_safety.py`

**Interfaces:**
- Produces: `prepare_authority_experiment(source_binary: str, generation: int) -> AuthorityExperiment`.
- `AuthorityExperiment` includes current cgroup ID, generation, authorized path, unauthorized path, SHA-256 values, `byte_identical`, positive projection proof and rollback snapshot.

- [ ] **Step 1: Write failing preparation tests**

Assert both probes are byte-identical, same executable mode, separate paths; current cgroup ID is captured; positive probe is staged in measured-exec state; negative probe is absent; current cgroup is bound to selected generation; any cgroup change between capture and arm causes refusal.

- [ ] **Step 2: Run safety preparation tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k prepare`
Expected: FAIL.

- [ ] **Step 3: Implement preparation using existing measured-manifest/pinned-map APIs**

Prefer established repository helpers such as staged measured-exec projection and active-generation projection. Do not directly invent a parallel authority map format.

- [ ] **Step 4: Add a final pre-arm identity recheck**

Immediately before strict-mode mutation, compare live cgroup ID to the prepared one. Refuse if changed.

- [ ] **Step 5: Run preparation tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k prepare`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/backend/services/os_enforcement_service.py \
        arda_os/backend/tests/test_gauntlet_strict_mode_safety.py
git commit -m "feat: prepare safe measured execution experiment"
```

---

### Task 5: Tulkas Ring-0 Allow/Deny Experiment

**Files:**
- Modify: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Test: `arda_os/backend/tests/test_gauntlet_strict_mode_safety.py`

**Interfaces:**
- Produces: `run_kernel_authority_experiment(experiment: AuthorityExperiment) -> KernelExperimentResult`.
- `KernelExperimentResult` records positive rc, negative rc/errno, deny reason, enforcement mode, cgroup, generation, and `kernel_veto_observed`.

- [ ] **Step 1: Write failing positive/negative-control tests**

Assert positive control must return `0`; negative control must fail with `EPERM`/`EACCES` semantics; live deny telemetry must say `fsverity_strict` and expected reason `measured_exec_miss`; any negative rc=0 yields `FAILED`.

- [ ] **Step 2: Run enforcement tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k enforcement`
Expected: FAIL.

- [ ] **Step 3: Implement strict-mode execution with no policy fabrication**

Switch mode through the established service API only after Task 4 preflight passes. Execute both probes and read `get_last_deny_event()` for the negative result.

- [ ] **Step 4: Render Tulkas stage from observed results**

Only print `KERNEL SAYS NO` when the kernel veto is actually observed and telemetry is coherent.

- [ ] **Step 5: Run enforcement tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k enforcement`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_gauntlet_strict_mode_safety.py
git commit -m "feat: prove kernel authority with controlled probes"
```

---

### Task 6: Lórien No-New-Exec Watchdog and Verified Rollback

**Files:**
- Create: `arda_os/backend/services/strict_mode_watchdog.py`
- Modify: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Test: `arda_os/backend/tests/test_gauntlet_strict_mode_safety.py`

**Interfaces:**
- Produces: `StrictModeWatchdog.start(rollback_snapshot) -> WatchdogHandle`, `WatchdogHandle.mark_safe()`, `WatchdogHandle.wait_verified(timeout_s: float) -> bool`.
- Watchdog child must restore prior pinned enforcement mode using inherited Python state/file descriptors or direct pinned-map access, never by spawning `sudo`, `bpftool`, shell, or another executable.

- [ ] **Step 1: Write failing watchdog tests**

Assert watchdog is ready before strict mode, parent exception triggers audit restoration, Ctrl-C path triggers restoration, unexpected negative-control allow still restores, and failed restoration returns `INCOMPLETE` rather than success.

- [ ] **Step 2: Run watchdog tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k "watchdog or rollback"`
Expected: FAIL.

- [ ] **Step 3: Implement forked rollback watchdog**

Capture previous enforcement mode and required pinned-map identifiers before fork. Child blocks on a pipe/event and restores if parent disappears or signals failure.

- [ ] **Step 4: Wrap strict-mode phase in `try/finally` and require restoration verification**

Parent restores normally in `finally`; watchdog independently confirms mode is back to `audit` before result can become complete.

- [ ] **Step 5: Run watchdog tests**

Run: `pytest -q arda_os/backend/tests/test_gauntlet_strict_mode_safety.py -k "watchdog or rollback"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/strict_mode_watchdog.py \
        arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_gauntlet_strict_mode_safety.py
git commit -m "feat: add Lorien strict-mode recovery watchdog"
```

---

### Task 7: Final Receipt, Vairë Closeout, and “SO WHAT?” Terminal Act

**Files:**
- Modify: `arda_os/backend/services/witnessed_authority_gauntlet.py`
- Modify: `arda_os/backend/services/gauntlet_receipt.py`
- Modify: `arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py`
- Test: `arda_os/backend/tests/test_witnessed_authority_gauntlet.py`
- Test: `arda_os/backend/tests/test_gauntlet_receipt.py`

**Interfaces:**
- Produces final `SealedGauntletReceipt` containing run/platform/witness/Aulë/experiment/kernel/recovery/result sections.
- CLI writes machine-readable receipt and detached verification metadata to a run directory and prints concise human summary.

- [ ] **Step 1: Write failing final-output tests**

Assert receipt includes run ID, timestamp, host, kernel, git commit, Secure Boot/lockdown/BPF state, TPM summary, PCR 0/1/7/11 and baseline comparisons, all five witness digests, Aulë state, Secret Fire freshness/replay, PQC provider/algorithm/key fingerprint/signature, probe hashes, authority states, kernel deny telemetry, rollback verification and final result.

Assert terminal includes `SO WHAT?`, `ARDA separates cognition from authority`, `The AI may advise. The substrate decides.`, and the final plain-English comparison without claiming primitive novelty.

- [ ] **Step 2: Run final-output tests**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py arda_os/backend/tests/test_gauntlet_receipt.py`
Expected: FAIL until closeout/receipt wiring exists.

- [ ] **Step 3: Implement Vairë closeout and canonical final receipt**

Close chronology only after kernel experiment and rollback are known. Seal the final canonical receipt after recovery, not before.

- [ ] **Step 4: Implement final terminal act**

Keep ASCII restrained. Print mythic line first, exact technical result second, plain-English consequence third. No large JSON.

- [ ] **Step 5: Run final-output tests**

Run: `pytest -q arda_os/backend/tests/test_witnessed_authority_gauntlet.py arda_os/backend/tests/test_gauntlet_receipt.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add arda_os/backend/services/witnessed_authority_gauntlet.py \
        arda_os/backend/services/gauntlet_receipt.py \
        arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_gauntlet_receipt.py
git commit -m "feat: seal witnessed authority gauntlet receipt"
```

---

### Task 8: Full Test Gauntlet and Live Preflight Mode

**Files:**
- Modify: `arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py`
- Test: all three new test files plus directly affected existing enforcement/PQC tests

**Interfaces:**
- Produces CLI modes: `--preflight` and default live run.
- `--preflight` performs no authority mutation and reports whether a live sovereign run is safe to attempt.

- [ ] **Step 1: Add failing tests for `--preflight` no-mutation guarantee**

Assert preflight checks native PQC, authoritative BPF, current mode, current cgroup, generation, witness availability and recovery prerequisites without changing enforcement mode or pinned authority state.

- [ ] **Step 2: Run the new suite**

Run:
```bash
pytest -q \
  arda_os/backend/tests/test_witnessed_authority_gauntlet.py \
  arda_os/backend/tests/test_gauntlet_strict_mode_safety.py \
  arda_os/backend/tests/test_gauntlet_receipt.py
```
Expected: FAIL until preflight is wired.

- [ ] **Step 3: Implement `--preflight`**

Return `0` only when the system is ready for a live run; otherwise return non-zero with precise refusal reason and no policy mutation.

- [ ] **Step 4: Run affected existing tests**

Run the repository’s existing quantum-security, OS-enforcement, Ainur choir/Aulë, Manwë Herald and Valinor postboot tests identified by `pytest --collect-only`/path search.
Expected: PASS.

- [ ] **Step 5: Run the complete focused suite**

Run:
```bash
pytest -q \
  arda_os/backend/tests/test_witnessed_authority_gauntlet.py \
  arda_os/backend/tests/test_gauntlet_strict_mode_safety.py \
  arda_os/backend/tests/test_gauntlet_receipt.py
```
Expected: PASS.

- [ ] **Step 6: Run a real-host preflight only**

Run:
```bash
sudo env \
  ARDA_SOVEREIGN_MODE=1 \
  ARDA_REQUIRE_NATIVE_PQC=1 \
  PYTHONPATH="$PWD/arda_os" \
  python3 arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py --preflight
```
Expected: either a clean READY result or a precise fail-closed blocker. No enforcement mode change.

- [ ] **Step 7: Commit**

```bash
git add arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_witnessed_authority_gauntlet.py \
        arda_os/backend/tests/test_gauntlet_strict_mode_safety.py \
        arda_os/backend/tests/test_gauntlet_receipt.py
git commit -m "test: verify witnessed authority gauntlet end to end"
```

---

## Live Meeting Run Contract

Only after all focused tests pass and `--preflight` reports READY should the live command be used:

```bash
sudo env \
  ARDA_SOVEREIGN_MODE=1 \
  ARDA_REQUIRE_NATIVE_PQC=1 \
  PYTHONPATH="$PWD/arda_os" \
  python3 arda_os/kernel/valinor/scripts/arda_witnessed_authority_gauntlet.py
```

The live run must pause once, immediately before strict enforcement, after printing both byte-identical probe hashes and the authority distinction. The operator presses Enter only after the witnesses can see that the independent variable is authority.

Expected final state after any run path: `enforcement_mode = audit`.

Expected successful experimental conclusion:

```text
AUTHORIZED PROBE ............... ALLOW
UNAUTHORIZED PROBE ............. DENY / EPERM
DENY REASON .................... measured_exec_miss
RECOVERY ....................... VERIFIED / audit

EXECUTION DOES NOT EQUAL AUTHORITY
```
