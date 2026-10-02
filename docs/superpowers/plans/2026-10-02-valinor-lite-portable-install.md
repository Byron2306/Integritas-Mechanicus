# Valinor Lite Portable Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable, rollback-safe Valinor Lite installer that deploys Linux 6.12.96-valinor, preserves ARDA's boot identity, truthfully degrades TPM-backed attestation on no-TPM systems, and retains Debian/Windows bootability.

**Architecture:** Keep the proven 6.12.96-valinor kernel unchanged. Add an explicit FULL/LITE attestation profile above the existing Phase 4 attestation services, derive a clean identity payload from the preserved historical snapshot, and install both through one preflight-first transactional installer. Installation defaults to audit mode and records enough state for deterministic verification and rollback.

**Tech Stack:** Python 3.13+, Bash, pytest, Debian GRUB2, Plymouth, systemd, BPF LSM, fs-verity/IMA/EVM, liboqs ML-DSA, zstd, SHA-256.

**Spec:** `docs/superpowers/specs/2026-10-02-valinor-lite-portable-install-design.md`

## Global Constraints

- Kernel release is exactly `6.12.96-valinor`.
- Kernel SHA-256 is `875117b4148753e407725a3d3d838d8f40db95111c88eabd329f9d229414a527`.
- Preserved initramfs SHA-256 is `e1c9cd2c1694b28761d486a3662ec8e32803871bd7bd8de11d382824c382c7ec`.
- Awakening WAV SHA-256 is `90f0e19a8b9318ac6472caa28f85894aebaaae69113cc69a45b9e88cfa0bbc`.
- First Lite release does not rebuild the kernel.
- TPM absence must never be represented as TPM success.
- `hardware_rooted=false` when TPM-backed evidence is unavailable.
- Secure Boot alone never implies `hardware_rooted=true`.
- TPM absence must not disable BPF LSM enforcement.
- Native PQC simulation must not satisfy a native-PQC-required gate.
- Initial enforcement mode is `audit`.
- Installer must not format, resize, or repartition disks.
- Installer must not delete Windows EFI loaders.
- Installer must retain at least one Debian distribution kernel.
- Installer must not enable global `fsverity_strict` during installation.
- Historical `valinor-boot-snapshot.tar.zst` remains immutable.
- The Lite identity payload contains only ARDA assets required for installation, not unrelated Debian stock themes.
- Awakening audio failure is non-fatal and separate from security status.
- All boot mutations require a backup created first.
- Rollback must not depend on Valinor strict-mode execution.

## Review Focus

- Machine has no TPM device and no `tpm2_*` tools: Lite must succeed with an explicit software-rooted state while Full refuses.
- Existing Windows EFI loader is present but `os-prober` is disabled: installer must preserve the loader and must not claim a generated Windows menu entry exists unless verified.
- A kernel or identity artifact hash does not match the release manifest: installation must refuse before modifying boot state.
- Installation is interrupted after backup but before `update-grub`: rerun must be idempotent and rollback must still resolve the recorded backup.
- `/boot` or EFI partition lacks sufficient space: preflight must refuse before copying kernel/initramfs or changing GRUB.

---

### Task 1: Explicit FULL and LITE Attestation Profiles

**Files:**
- Create: `arda_os/backend/services/attestation_profile.py`
- Modify: `arda_os/backend/services/phase4_live_attestation.py`
- Modify: `arda_os/backend/services/phase4_attestation_gate.py`
- Create: `arda_os/backend/tests/test_attestation_profile.py`
- Modify: `arda_os/backend/tests/test_phase4_attestation_gate.py`

**Interfaces:**
- Produces: `AttestationProfile`, `resolve_attestation_profile(value: str | None) -> AttestationProfile`
- Produces: explicit `full` and `lite` policy semantics consumed by later installer/verifier tasks.
- Existing Phase 4 APIs remain backwards compatible when profile is omitted.

- [ ] **Step 1: Write failing profile tests**

Add tests asserting:

```python
def test_full_profile_requires_tpm():
    profile = resolve_attestation_profile("full")
    assert profile.name == "full"
    assert profile.require_tpm is True

def test_lite_profile_does_not_require_tpm():
    profile = resolve_attestation_profile("lite")
    assert profile.name == "lite"
    assert profile.require_tpm is False

def test_unknown_profile_refuses():
    with pytest.raises(ValueError):
        resolve_attestation_profile("banana")
```

- [ ] **Step 2: Run the profile tests**

Run:

```bash
/usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_attestation_profile.py
```

Expected: FAIL because `attestation_profile.py` does not exist.

- [ ] **Step 3: Implement profile model**

Implement in `attestation_profile.py`:

```python
@dataclass(frozen=True)
class AttestationProfile:
    name: Literal["full", "lite"]
    require_tpm: bool
    permit_software_root: bool

def resolve_attestation_profile(value: str | None) -> AttestationProfile:
    ...
```

Default omitted profile to `full`.

- [ ] **Step 4: Add failing no-TPM gate tests**

Pin these behaviors:

- FULL + TPM absent => REFUSE/failure.
- LITE + TPM absent => no fabricated TPM evidence.
- LITE result contains `hardware_rooted=False`.
- LITE result contains `tpm_available=False`.
- LITE result can become `software_rooted=True` only after required software evidence passes.
- Missing `tpm2_checkquote` does not fail Lite merely because TPM is absent.
- Secure Boot alone never produces `hardware_rooted=True`.

- [ ] **Step 5: Run those tests**

Run the exact affected Phase 4 test module.

Expected: FAIL on current TPM assumptions.

- [ ] **Step 6: Thread profile through Phase 4 services**

Modify the existing Phase 4 services so:

- FULL retains existing strict TPM behavior.
- LITE bypasses TPM capture only when TPM is genuinely absent.
- No placeholder PCR/quote/identity objects are fabricated.
- Existing quote verification remains unchanged when TPM evidence exists.
- Trust result explicitly distinguishes `hardware_rooted`, `software_rooted`, and `tpm_available`.

- [ ] **Step 7: Run Phase 4 tests**

Run:

```bash
/usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_attestation_profile.py \
arda_os/backend/tests/test_phase4_attestation_gate.py
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add -f \
arda_os/backend/services/attestation_profile.py \
arda_os/backend/services/phase4_live_attestation.py \
arda_os/backend/services/phase4_attestation_gate.py \
arda_os/backend/tests/test_attestation_profile.py \
arda_os/backend/tests/test_phase4_attestation_gate.py

git commit -m \
"feat: add truthful Valinor Lite attestation profile"
```

---

### Task 2: Software-Rooted Lite Evidence

**Files:**
- Create: `arda_os/backend/services/valinor_lite_evidence.py`
- Create: `arda_os/backend/tests/test_valinor_lite_evidence.py`
- Reuse: existing BPF enforcement and native PQC services.

**Interfaces:**
- Consumes: `AttestationProfile` from Task 1.
- Produces:

```python
@dataclass(frozen=True)
class LiteEvidence:
    kernel_sha256: str
    initramfs_sha256: str
    kernel_identity_verified: bool
    bpf_lsm_available: bool
    measured_maps_available: bool
    pqc_native_verified: bool
    secure_boot_state: str
    software_rooted: bool

def collect_lite_evidence(...) -> LiteEvidence:
    ...
```

- [ ] **Step 1: Write failing evidence tests**

Pin:

- canonical kernel hash passes;
- wrong kernel hash fails;
- canonical initramfs hash passes;
- absent BPF LSM prevents `software_rooted=True`;
- absent measured maps prevents `software_rooted=True`;
- failed native PQC prevents `software_rooted=True` when PQC is required;
- Secure Boot may be `enabled`, `disabled`, or `unknown` without altering the TPM truth flag.

- [ ] **Step 2: Run tests and confirm failure**

```bash
/usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_valinor_lite_evidence.py
```

Expected: FAIL because collector does not exist.

- [ ] **Step 3: Implement evidence collector**

Use injected paths/status probes for tests rather than hard-coding the live host.

Canonical values:

```text
kernel = 875117b4148753e407725a3d3d838d8f40db95111c88eabd329f9d229414a527
initramfs = e1c9cd2c1694b28761d486a3662ec8e32803871bd7bd8de11d382824c382c7ec
```

Do not create hardware-root claims here.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f \
arda_os/backend/services/valinor_lite_evidence.py \
arda_os/backend/tests/test_valinor_lite_evidence.py

git commit -m \
"feat: verify Valinor Lite software-rooted evidence"
```

---

### Task 3: Derive the Canonical Portable ARDA Identity Payload

**Files:**
- Create: `arda_os/kernel/valinor/lite/identity/manifest.json`
- Create: `arda_os/kernel/valinor/lite/identity/grub/arda-sovereign/`
- Create: `arda_os/kernel/valinor/lite/identity/plymouth/arda-sovereign/`
- Create: `arda_os/kernel/valinor/lite/identity/plymouth/arda-mirror-gate/`
- Create: `arda_os/kernel/valinor/lite/identity/audio/arda-awakening.wav`
- Create: `arda_os/backend/tests/test_valinor_lite_identity.py`

**Interfaces:**
- Consumes: immutable historical snapshot assets.
- Produces: installable identity tree plus SHA-256 manifest.
- Later installer consumes this tree only, never the whole historical snapshot.

- [ ] **Step 1: Write failing identity manifest tests**

Tests assert:

- `arda-sovereign` GRUB identity exists;
- both ARDA Plymouth themes exist;
- `arda-awakening.wav` exists;
- WAV hash is exactly `90f0e19a8b9318ac6472caa28f85894aebaaae69113cc69a45b9e88cfa0bbc`;
- manifest contains no stock `ceratopsian`, `moonlight`, `emerald`, `homeworld`, `spacefun`, or other Debian theme payloads;
- all manifest hashes verify.

- [ ] **Step 2: Run tests**

Expected: FAIL because portable identity payload does not exist.

- [ ] **Step 3: Copy only canonical ARDA assets from the historical snapshot**

Source from `~/valinor-boot-snapshot` during implementation.

Preserve:

- actual ARDA GRUB theme files;
- `arda-sovereign` Plymouth assets;
- `arda-mirror-gate` Plymouth assets;
- `arda-awakening.wav`.

Do not import unrelated stock Plymouth themes.

- [ ] **Step 4: Generate `manifest.json`**

Manifest records:

- schema version;
- logical role;
- relative path;
- SHA-256;
- required/optional status.

- [ ] **Step 5: Run identity tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -f arda_os/kernel/valinor/lite/identity \
arda_os/backend/tests/test_valinor_lite_identity.py

git commit -m \
"feat: package canonical Valinor Lite boot identity"
```

---

### Task 4: Installer Preflight and Immutable Release Manifest

**Files:**
- Create: `arda_os/kernel/valinor/lite/installer/preflight.py`
- Create: `arda_os/kernel/valinor/lite/installer/release_manifest.json`
- Create: `arda_os/backend/tests/test_valinor_lite_preflight.py`

**Interfaces:**
- Consumes: Tasks 1-3 artifacts.
- Produces:

```python
@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    architecture: str
    debian: bool
    boot_mode: str
    tpm_available: bool
    secure_boot_state: str
    windows_efi_entries: tuple[str, ...]
    fallback_kernels: tuple[str, ...]
    boot_free_bytes: int
    failures: tuple[str, ...]

def run_preflight(...) -> PreflightReport:
    ...
```

- [ ] **Step 1: Write failing preflight tests**

Cover:

- non-x86_64 refuses;
- non-Debian refuses;
- no TPM is allowed;
- missing fallback Debian kernel refuses;
- insufficient `/boot` space refuses;
- Windows EFI entry is detected and recorded;
- `os-prober` disabled does not erase knowledge of an EFI Windows loader;
- bad release hash refuses;
- successful no-TPM Debian host returns `ok=True`.

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement manifest**

Manifest pins:

- kernel release;
- kernel SHA-256;
- preserved initramfs SHA-256;
- identity manifest path;
- supported architecture `x86_64`.

- [ ] **Step 4: Implement preflight**

Use injectable command/file probes so unit tests never inspect or mutate the developer workstation.

- [ ] **Step 5: Run tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/installer/preflight.py \
arda_os/kernel/valinor/lite/installer/release_manifest.json \
arda_os/backend/tests/test_valinor_lite_preflight.py

git commit -m \
"feat: add Valinor Lite installation preflight"
```

---

### Task 5: Transactional Installer and Boot Identity Installation

**Files:**
- Create: `arda_os/kernel/valinor/lite/installer/install.py`
- Create: `arda_os/kernel/valinor/lite/install-valinor-lite`
- Create: `arda_os/backend/tests/test_valinor_lite_installer.py`

**Interfaces:**
- Consumes: `run_preflight()` from Task 4 and canonical identity payload from Task 3.
- Produces:

```python
@dataclass(frozen=True)
class InstallResult:
    success: bool
    backup_id: str
    installed_kernel: str
    profile: str
    grub_verified: bool
    fallback_verified: bool
    windows_preserved: bool
    plymouth_theme: str
    audio_installed: bool

def install_valinor_lite(...) -> InstallResult:
    ...
```

- [ ] **Step 1: Write failing transaction tests**

Pin ordering and refusal behavior:

- no filesystem mutation before successful preflight;
- backup occurs before first boot-file modification;
- hash failure performs zero boot mutations;
- kernel/module payload is installed under expected locations;
- ARDA identity goes to deterministic destinations;
- existing Windows EFI files are never deleted;
- fallback Debian kernel remains;
- initial enforcement profile is `audit`;
- running installer twice does not duplicate configuration;
- awakening audio installation failure is reported but does not mark security installation failed.

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement transaction model**

Installer phases:

```text
PREFLIGHT
BACKUP
VERIFY_ARTIFACTS
INSTALL_KERNEL
INSTALL_PROFILE
INSTALL_IDENTITY
CONFIGURE_PLYMOUTH
CONFIGURE_GRUB
GENERATE_BOOT_MENU
VERIFY
COMMIT_INSTALL_STATE
```

Persist transaction state before each mutating phase.

- [ ] **Step 4: Implement shell entry point**

`install-valinor-lite` invokes Python installer and requires root only for the mutation phase.

Support:

```text
--preflight
--install
--dry-run
--rollback
--verify
```

Default invocation without a mode prints help rather than mutating the system.

- [ ] **Step 5: Run installer tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/installer/install.py \
arda_os/kernel/valinor/lite/install-valinor-lite \
arda_os/backend/tests/test_valinor_lite_installer.py

git commit -m \
"feat: install Valinor Lite transactionally"
```

---

### Task 6: Deterministic Rollback

**Files:**
- Create: `arda_os/kernel/valinor/lite/installer/rollback.py`
- Modify: `arda_os/kernel/valinor/lite/install-valinor-lite`
- Create: `arda_os/backend/tests/test_valinor_lite_rollback.py`

**Interfaces:**
- Consumes: installer backup/transaction records from Task 5.
- Produces:

```python
@dataclass(frozen=True)
class RollbackResult:
    success: bool
    restored_backup_id: str
    grub_restored: bool
    plymouth_restored: bool
    windows_preserved: bool

def rollback_valinor_lite(...) -> RollbackResult:
    ...
```

- [ ] **Step 1: Write failing rollback tests**

Cover:

- exact backup selected by install-state record;
- interrupted install can roll back;
- missing backup refuses rather than guessing;
- GRUB config restored;
- Plymouth config restored;
- Windows EFI files untouched;
- rollback does not require network;
- rollback never activates strict mode;
- repeated rollback is safe/idempotent.

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement rollback**

Rollback restores only files recorded as modified by installer transaction metadata.

It does not repartition, delete user data, or delete unrelated kernels.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/installer/rollback.py \
arda_os/kernel/valinor/lite/install-valinor-lite \
arda_os/backend/tests/test_valinor_lite_rollback.py

git commit -m \
"feat: add deterministic Valinor Lite rollback"
```

---

### Task 7: First-Boot Verifier and Truthful Trust Report

**Files:**
- Create: `arda_os/kernel/valinor/lite/verify/verify_valinor_lite.py`
- Create: `arda_os/kernel/valinor/lite/verify-valinor-lite`
- Create: `arda_os/backend/tests/test_verify_valinor_lite.py`

**Interfaces:**
- Consumes: Task 1 profile and Task 2 evidence.
- Produces human-readable and JSON reports.
- Must not mutate BPF enforcement state.

- [ ] **Step 1: Write failing verifier tests**

Pin exact no-TPM semantics:

```text
TRUST PROFILE .............. VALINOR_LITE
TPM ......................... ABSENT
HARDWARE ROOT ............... UNAVAILABLE
SOFTWARE ROOT ............... VERIFIED
KERNEL IDENTITY ............. VERIFIED
BPF LSM ..................... VERIFIED
PQC ......................... VERIFIED
ENFORCEMENT MODE ............ AUDIT
```

Also test degraded states independently:

- wrong kernel => kernel identity failed;
- BPF unavailable => software root not verified;
- native PQC unavailable => PQC failed;
- TPM present does not automatically make Lite hardware-rooted;
- verifier never changes `audit` to `fsverity_strict`.

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement verifier**

Support:

```text
verify-valinor-lite
verify-valinor-lite --json
```

Exit nonzero when required Lite evidence fails.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/verify \
arda_os/kernel/valinor/lite/verify-valinor-lite \
arda_os/backend/tests/test_verify_valinor_lite.py

git commit -m \
"feat: verify Valinor Lite first-boot trust"
```

---

### Task 8: Build Portable Release Bundle

**Files:**
- Create: `arda_os/kernel/valinor/lite/build_release.py`
- Create: `arda_os/backend/tests/test_valinor_lite_release.py`
- Produce outside Git history: `valinor-lite-6.12.96.tar.zst`

**Interfaces:**
- Consumes: kernel release archive, Tasks 3-7 install payloads.
- Produces one offline-installable `.tar.zst` and SHA-256 sidecar.

- [ ] **Step 1: Write failing release tests**

Assert generated release contains:

```text
install-valinor-lite
manifest/
kernel/valinor-kernel-6.12.96.tar.zst
identity/
profile/
verify/
```

Also assert:

- all manifest hashes pass;
- no historical stock-theme clutter enters bundle;
- installer works without Git checkout;
- kernel archive is not committed as an ordinary Git blob;
- release bundle can be verified offline.

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement deterministic release builder**

Builder stages into a temporary directory, verifies source hashes, emits manifest, creates zstd archive, then emits archive SHA-256.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Build candidate artifact**

Run builder using the preserved release kernel archive and canonical identity payload.

- [ ] **Step 6: Verify candidate**

Extract into a temporary directory and run offline manifest verification.

Expected: all hashes PASS.

- [ ] **Step 7: Commit builder and tests only**

```bash
git add -f \
arda_os/kernel/valinor/lite/build_release.py \
arda_os/backend/tests/test_valinor_lite_release.py

git commit -m \
"feat: build portable Valinor Lite release"
```

Do not put the generated large release archive into ordinary Git history.

---

### Task 9: Safe Installation Gauntlet

**Files:**
- Create: `arda_os/backend/tests/test_valinor_lite_install_gauntlet.py`
- Create: `arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md`

**Interfaces:**
- Consumes all prior tasks.
- Produces a deterministic acceptance report for a simulated filesystem first and then a real no-TPM Debian target.

- [ ] **Step 1: Write complete simulated-host gauntlet**

Scenario contains:

- x86_64 Debian;
- no `/dev/tpm0`;
- no `/dev/tpmrm0`;
- Windows EFI loader present;
- one Debian fallback kernel;
- sufficient `/boot` space;
- valid Valinor artifacts;
- valid ARDA identity;
- installer run;
- second installer run;
- verifier run;
- rollback run.

Assertions:

- Full profile refuses no-TPM attestation.
- Lite profile installs.
- Windows survives.
- fallback Debian survives.
- Valinor entry exists.
- ARDA identity hashes match.
- awakening WAV hash matches.
- Lite verifier says hardware root unavailable.
- software root verifies.
- initial enforcement is audit.
- repeated install is idempotent.
- rollback restores original boot configuration.

- [ ] **Step 2: Run simulated gauntlet**

Expected: PASS.

- [ ] **Step 3: Run full relevant test suite**

```bash
/usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_attestation_profile.py \
arda_os/backend/tests/test_valinor_lite_evidence.py \
arda_os/backend/tests/test_valinor_lite_identity.py \
arda_os/backend/tests/test_valinor_lite_preflight.py \
arda_os/backend/tests/test_valinor_lite_installer.py \
arda_os/backend/tests/test_valinor_lite_rollback.py \
arda_os/backend/tests/test_verify_valinor_lite.py \
arda_os/backend/tests/test_valinor_lite_release.py \
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py
```

Expected: all PASS.

- [ ] **Step 4: Run repository regression tests covering Phase 4, BPF enforcement, PQC, and boot tooling**

Any regression blocks release.

- [ ] **Step 5: Write installation document**

Document only verified commands and explicitly state:

- does not repartition;
- does not remove Windows;
- TPM-less Lite is not hardware-rooted;
- audit is default;
- rollback command;
- first-boot verification command.

- [ ] **Step 6: Commit**

```bash
git add -f \
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py \
arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md

git commit -m \
"test: graduate portable Valinor Lite installation"
```

---

## Final Acceptance

Before release, verify:

```text
[ ] Historical boot snapshot remains unchanged.
[ ] 6.12.96-valinor kernel hash matches canonical value.
[ ] Initramfs canonical hash is recorded and verified at packaging time.
[ ] Awakening WAV matches canonical hash.
[ ] No-TPM Lite path reports hardware_rooted=false.
[ ] Full path still refuses required TPM evidence when missing.
[ ] BPF LSM behavior is unaffected by TPM absence.
[ ] Native PQC verification passes.
[ ] Installer defaults to audit mode.
[ ] Installer makes boot backup before mutation.
[ ] Existing Debian fallback survives.
[ ] Existing Windows EFI loader survives.
[ ] Re-running installer is idempotent.
[ ] Rollback succeeds from recorded backup.
[ ] Release bundle verifies offline.
[ ] No large kernel archive enters normal Git history.
```

Only after the simulated gauntlet passes should the installer be exercised on the target Windows/Debian laptop.

The first real installation should stop after:

    install-valinor-lite --preflight

and require explicit operator continuation before any boot mutation.
