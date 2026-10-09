# Valinor proof provisioning implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore an operator workflow for fresh, verifiable ARDA hardware-rooted proof on the updated Valinor workstation.

**Architecture:** A thin replacement CLI composes read-only inspection, trusted immutable-file manifests, owned enforcement sessions, independent TPM verification, and host activation. Existing legacy APIs remain available; new commands fail explicitly when their trust or runtime requirements are absent.

**Tech Stack:** Python 3, pytest, cryptography Ed25519/X.509, SQLite, libbpf loader, bpftool, fs-verity ioctl, cgroup v2, tpm2-tools, FastAPI verifier, systemd.

**Spec:** [Approved design](../specs/2026-10-09-valinor-proof-provisioning-design.md)

## Global constraints

- Reports identify `implementation: replacement-v1` and `schema_version: arda.proof_report.v1`.
- Success exits 0, unmet prerequisites exit 1, and invalid arguments exit 2.
- Never use a simulation fallback for live proof.
- Inspection performs no arming, database creation, PCR extension, package installation, or service restart.
- Manifests and signed verdicts have lifetimes of at most 300 seconds.
- Scoped tests last at most 120 seconds. Scoped success cannot satisfy host-wide OS-grade.
- Root-owned host configuration is `/etc/arda/proof.json`.
- No automatic trust enrollment, baseline approval, reboot, or boot-selection change.
- Preserve local edits and existing BPF binaries; rebuild into a separate workspace.
- `ok` is true only for the full hardware-rooted result. Missing required evidence is a blocker.

## Review focus

- Files can be renamed, replaced or deleted between verification and map projection; retain descriptors and revalidate identities.
- A killed supervisor can leave enforcement behind; an independent bounded owner must detach it without executing enrolled programs.
- cgroup identities and program/map IDs change across sessions and boots; never accept historical IDs as live proof.
- A valid signature can bind the wrong host, nonce, generation or quote; independently check every binding and replay state.
- New cgroups can appear after a host coverage plan; invalidate stale plans and block activation without a lifecycle enrollment mechanism.

## Execution boundaries

Implement natively in this session if the user accepts that recommendation. Do not spawn agents without explicit selection of delegation. Complete all tasks, including negative-path tests, before reporting implementation complete. Hardware verification is a separate operator phase; missing verifier credentials or a hardware feature yields an explicit blocker, never a synthetic pass.

Tests below run from repository root with `PYTHONPATH=arda_os .venv/bin/python -m pytest`. Check availability of pytest and cryptography before implementation; do not install packages as part of inspection. Stage and commit only each task's changed files. Preserve pre-existing modifications in any edited file by recording the original diff and reviewing the incremental changes; do not commit another person's changes inadvertently.

### Task 1: Replacement CLI, configuration and truthful inspection

**Files:** Create `arda_os/bin/arda`, `arda_os/backend/services/proof_cli.py`, `proof_config.py`, `proof_inspection.py`, `proof_report.py` in the same services directory. Test `arda_os/backend/tests/test_proof_cli.py` and `test_proof_inspection.py`.

**Interfaces:** `proof_cli.main(argv: list[str] | None = None) -> int`; `proof_config.load_config(path: str) -> dict`; `proof_inspection.inspect(config: dict | None) -> dict`; `proof_report.appraise(checks: dict[str, dict], scope: str) -> dict`. Check records contain `status`, `reason`, `evidence`; status is one of pass/fail/unknown/skipped. Config specifies node ID, trust keys, artifacts, policy, scope, TPM/verifier and baseline paths; reject unknown fields and writable production configuration.

- [ ] Write tests for inspect with absent config/database, denied filesystem access, non-root execution, missing tools, invalid CLI arguments and skipped required checks. Assert `test_scoped_never_sets_os_grade`: scoped checks cannot make either grade field true. Snapshot filesystem changes and subprocess arguments to establish read-only behavior.
- [ ] Run the two new test files; confirm failure because the new modules/entry point are absent.
- [ ] Implement the interfaces above without constructing `OsEnforcementService`, whose initialization writes SQLite state. Open an existing ledger with SQLite `mode=ro`. Integrate live attachment evidence, boot signals, tool paths and hashes; never trust pins alone. Register all approved command names with explicit prerequisite errors until their implementations land.
- [ ] Run the two new test files and existing `test_arda_bpf_authority.py` and `test_arda_authority_boundary.py`; require all pass. Execute `arda_os/bin/arda proof inspect --json` and confirm truthful blockers on the current environment.
- [ ] Commit only Task 1 files: `feat: add read-only ARDA proof inspection and CLI`.

### Task 2: Private preparation workspace and artifact provenance

**Files:** Create `arda_os/backend/services/proof_workspace.py`, `arda_os/bin/build_arda_proof_bpf.sh`, `arda_os/backend/tests/test_proof_workspace.py`. Modify `proof_cli.py`. Update `docs/VALINOR_6.12.111_PROOF_RECOVERY.md` with real commands.

**Interfaces:** `proof_workspace.prepare(workspace: str) -> dict`; result supplies workspace, artifact records and config template paths. Build helper consumes explicit source/output paths and emits object/loader hashes. Never rewrite canonical binaries.

- [ ] Write tests refusing symlinked/nonempty or public workspaces, requiring mode 0700, checking copied disposable executables and disabled trust defaults, and proving absence of system-file writes. Assert build failures preserve old artifacts.
- [ ] Run `test_proof_workspace.py`; require failure for missing implementation.
- [ ] Implement prepare and the separate-output compiler helper. Capture repository revision, local changes, source/object hashes and supported maps/modes. Template references operator-supplied keys and baseline with no effective trust defaults. Connect `proof prepare --workspace PATH`.
- [ ] Run workspace tests; syntax-check the shell helper with `bash -n`. Build only when compiler/libbpf dependencies exist and report their absence otherwise. Inspect built object map definitions before permitting scoped tests.
- [ ] Commit Task 2 files: `feat: prepare isolated ARDA proof workspace`.

### Task 3: Cryptographically verified, live measured manifests

**Files:** Create `arda_os/backend/services/proof_manifests.py`, `proof_file_measurement.py`, `arda_os/backend/tests/test_proof_manifests.py`, `test_proof_file_measurement.py`. Modify `proof_cli.py`; modify `measured_identity.py` only if the generation transaction requires it.

**Interfaces:** `proof_file_measurement.open_measured(path: str) -> MeasuredFile`; `MeasuredFile` owns an open descriptor, stat identity, fs-verity algorithm/digest and `revalidate() -> None`, `close() -> None`. `proof_manifests.build(config: dict, now: datetime) -> dict`; `verify(manifest: dict, config: dict, now: datetime) -> VerifiedManifest`. `VerifiedManifest` owns measured files, canonical digest, scope/boot/node/cgroup/generation and `close()`. Callers must retain it while entries are authoritative.

- [ ] Write tests for real Ed25519 signatures and rejection after field/key-ID tampering, unknown key, naive timestamps, lifetime over 300 seconds, expiry, generation replay, wrong boot/node/cgroup, mutable files, wrong algorithm/digest, rename/substitution and descriptor cleanup. Assert generation is not consumed on verification failure.
- [ ] Run the two new test files; confirm missing interfaces fail.
- [ ] Implement canonical signing with all fields except signature bytes covered, independently configured trusted keys and `FS_IOC_MEASURE_VERITY` on open files. Use `fstat` and path/descriptor identity rechecks. Never substitute a plain SHA-256 checksum for a kernel fs-verity measurement. Build records conform to the existing manifest vocabulary with signed boot/scope/cgroup fields added.
- [ ] Make new activation use transactional generation commitment only after verified staging. Keep legacy API behavior identifiable; do not silently upgrade its shape-only preflight into a proof assertion. Wire `measured build` and `measured verify`.
- [ ] Run manifest/measurement tests and affected existing generation tests. Verify fs-verity using disposable files in an explicitly selected supported workspace; require a blocker rather than mutation of package-managed files if unsupported.
- [ ] Commit Task 3 files: `feat: verify trusted immutable ARDA measured manifests`.

### Task 4: Owned scoped enforcement and recovery

**Files:** Create `arda_os/backend/services/proof_enforcement.py`, `proof_cgroups.py`, `arda_os/backend/tests/test_proof_enforcement.py`, `test_proof_cgroups.py`. Modify `proof_cli.py`, `arda_bpf_authority.py`; change BPF source/loader only if verified scoped support is missing, preserving local edits.

**Interfaces:** `proof_cgroups.create_probe(workspace: str) -> ProbeCgroup`; probe supplies live kernel ID, placement and cleanup. `proof_enforcement.run_scoped(config: dict) -> dict`; `EnforcementSession` owns `VerifiedManifest`, artifact identity, pins, map handles, link owner and watchdog, implements `revalidate()`, `close()`. Artifact identity is operator-approved source/object hash plus expected tag/maps; program ID comes from live evidence.

- [ ] Write tests requiring allowed and denied executions plus matching counter/event evidence; reject a test that merely sees any EPERM. Cover existing attachment/map refusal, unrelated-map preservation, absent scoped support, timeout at 120 seconds, supervisor death, signals and cleanup exceptions. Assert other cgroups remain executable and changed file/cgroup identities invalidate the session.
- [ ] Run enforcement/cgroup tests; require failure before implementation.
- [ ] Implement an independent timed loader/link owner and unique session pins. Prepare everything in audit mode; verify the program tag/link/map relationships before setting scoped mode. Populate only measured identities from the held verified descriptors. Enroll the disposable cgroup, execute allowed and unlisted copied probes, inspect telemetry, and detach/remove only owned resources in finally/watchdog cleanup.
- [ ] Support explicit approved artifact identity in the authority adapter without weakening existing default tag verification. Preserve the old API's fail-closed behavior. Do not reuse detached pins or reset pre-existing maps.
- [ ] Run new and existing authority tests. Run the scoped hardware test only with explicit disposable workspace/config; save kernel evidence before/during/after, including successful timeout cleanup. If the existing object cannot enforce the required immutable identity binding, report a blocker and implement the necessary reviewed change before continuing.
- [ ] Commit Task 4 files: `feat: add bounded scoped ARDA enforcement proof`.

### Task 5: Independent TPM appraisal and bound verifier protocol

**Files:** Create `arda_os/backend/services/proof_attestation.py`, `proof_verdicts.py`, `proof_replay.py`, `arda_os/backend/tests/test_proof_attestation.py`, `test_proof_verdicts.py`. Modify `arda_phase4_verifier_service.py` with versioned routes, and `proof_cli.py`.

**Interfaces:** `proof_attestation.capture_and_verify(config: dict, session: EnforcementSession) -> dict`; `proof_verdicts.verify(verdict: dict, expected: dict, config: dict, now: datetime) -> dict`; `proof_replay.consume(issuer: str, session_id: str, nonce: str, expires_at: datetime, database: str) -> None`. New verifier routes `/verify/proof/v1/challenge` and `/verify/proof/v1` use a persisted single-use challenge store; do not reinterpret the legacy endpoint as the stricter protocol.

- [ ] Write tests refusing capture-side success booleans, invalid quote/signature/nonce/PCR selection, absent/untrusted EK certificate chains, wrong AK/EK binding, unapproved baseline, wrong boot/manifest/generation and replay across process restart. Verify verdict signatures against configured keys and reject lifetime over 300 seconds, unknown issuer, expiry and mismatched evidence digest.
- [ ] Run the new tests; confirm missing interfaces fail.
- [ ] Implement HTTPS challenge transport without redirecting trust to another endpoint; persist challenge sessions transactionally. Bind node, boot, generation, manifest and evidence digests into both quoted software state and signed verdict. Independently run quote verification on raw material and validate AK/EK evidence plus EK X.509 trust chain. Host-supplied paths/flags must not define verifier trust.
- [ ] Extend the verifier through versioned routes using independent policy and trust material. Old results missing bindings cannot pass. No automatic baseline approval, default HMAC trust, local-only production verdict or private-key transfer. Record explicit PCR11 extension and atomic evidence/results; separate state-changing capture from read-only reappraisal.
- [ ] Run new tests and affected attestation/verifier tests. Live capture waits for real operator-provided verifier endpoint, public key, approved baseline and Intel trust material; report any unavailable requirement explicitly.
- [ ] Commit Task 5 files: `feat: verify fresh bound TPM proof and verifier verdicts`.

### Task 6: Host coverage, manual activation and complete appraisal

**Files:** Create `arda_os/backend/services/proof_host.py`, `arda_os/backend/tests/test_proof_host.py`, `test_proof_os_grade.py`. Modify `proof_cli.py`, `proof_report.py`.

**Interfaces:** `proof_host.plan(config: dict, now: datetime) -> dict`; `activate(plan: dict, config: dict) -> EnforcementSession`; `appraise_live(config: dict) -> dict`. Plans bind boot/config/artifacts/current cgroup inventory, measured policy, generation, coverage and tested recovery. Keep host session alive through an owned supervised process with a control socket; inspecting reports must not create that process.

- [ ] Write tests for empty/stale/tampered plans, new cgroups since planning, incomplete interpreter/service/recovery coverage, positive redline flags that veto all commands, lost session descriptors, stale replayed verdict and scoped-only evidence. Assert all leave grades false and do not activate global strict mode.
- [ ] Run host/appraisal tests; require missing interfaces fail.
- [ ] Implement plan validation, manual activation and read-only live appraisal. Coverage must include lifecycle enrollment of newly created cgroups; a static cgroup list is insufficient. If the existing kernel path cannot guarantee it, return `host_cgroup_lifecycle_unavailable`, rather than activate and claim a complete host.
- [ ] Add a reviewed enforcement/lifecycle mechanism if required to satisfy host activation; extend tests for newly created cgroups and unsupported kernels. Require operator policy allow/deny tests, fresh trusted immutable identity coverage, live telemetry and independent TPM/verdict checks. Never set a redline flag just to make policy count nonzero.
- [ ] Keep verified file descriptors and recovery handles owned for the host session; invalidate appraisal on supervisor loss, path/identity change or attachment replacement. Connect `proof plan-host`, `proof activate-host`, and `os-grade`. Report confidentiality lockdown separately.
- [ ] Run new tests and all Task 1–5 suites once. Perform manual host activation only when coverage/recovery and real verifier prerequisites are satisfied; record blockers otherwise.
- [ ] Commit Task 6 files: `feat: gate host-wide ARDA activation on verified coverage`.

### Task 7: Post-boot lifecycle and operator handoff

**Files:** Create `arda_os/backend/services/proof_boot.py`, `arda_os/kernel/valinor/systemd/arda-proof-host.service`, `arda_os/backend/tests/test_proof_boot.py`. Modify `proof_cli.py`, `docs/VALINOR_6.12.111_PROOF_RECOVERY.md`, `arda_os/kernel/valinor/README.md`.

**Interfaces:** `proof_boot.install(config: dict) -> dict`; `start(config: dict) -> int`; installed unit starts the owned supervisor and validates current boot measurements/manifest/coverage/fresh verdict before blocking enforcement. Use new service identity so the historical template is not mistaken for restored behavior.

- [ ] Write tests refusing installation without prior full manual proof, wrong configuration ownership, stale evidence, missing dependencies, and bootstrap ordering that requires enforcement before the attestation tools can run. Assert no reboot, GRUB edit or historical inode/cgroup replay occurs.
- [ ] Run boot tests; confirm missing implementation fails.
- [ ] Implement atomic service installation with backup of any owned previous unit; use an explicitly resolved executable/interpreter path. Boot in audit preparation, obtain fresh proof and verified coverage, then enable enforcement. Failure prevents a full-grade result and follows the configured recovery lane; never silently label audit as enforce.
- [ ] Update runbook with actual CLI syntax, required operator keys/endpoint/baseline, trust distinctions and recovery commands. Add links to the replacement gate criteria and note that July tools were not recovered.
- [ ] Run all new suites and affected authority/attestation tests; validate unit syntax using `systemd-analyze verify` where systemd is available. Exercise CLI help, inspect and incomplete os-grade behavior without mutation.
- [ ] Commit Task 7 files: `feat: persist verified ARDA proof lifecycle across boots`.

## Final acceptance and handoff

- [ ] Review the incremental diff against the recorded pre-existing changes; preserve unrelated files and avoid pushing without instruction.
- [ ] Reproduce scoped allow/deny/telemetry and automatic recovery on the actual workstation with saved artifacts.
- [ ] Independently verify fresh Intel TPM identity, quote, software binding and trusted off-box signed verdict; unavailable external prerequisites remain named blockers.
- [ ] Validate host coverage and recovery, run manual full gate, then install the service. Obtain separate authorization before rebooting.
- [ ] After reboot, verify new boot binding, new cgroups, fresh attestation/verdict and full-grade result. Save evidence; do not present unit tests as hardware proof.
- [ ] Report implemented functionality, tests actually run, live proof achieved and remaining external blockers separately.
