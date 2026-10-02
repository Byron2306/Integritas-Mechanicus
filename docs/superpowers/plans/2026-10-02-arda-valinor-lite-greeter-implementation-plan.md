# ARDA Valinor Lite Greeter Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the stock LightDM GTK login surface into a canonical ARDA Valinor Lite greeter using Gate of Becoming plus the approved ARDA mark, while preserving authentication boundaries, rollback custody, release integrity, and truthful Lite trust semantics.

**Architecture:** Keep LightDM and `lightdm-gtk-greeter` as the authentication/display-manager substrate. Add a small greeter adapter that detects supported display-manager state, stages canonical assets, emits deterministic GTK greeter configuration, and exposes verification results. Extend the existing Valinor Lite installer and rollback transaction so greeter files participate in backup, idempotency, release packaging, and restoration.

**Tech Stack:** Python 3.13+, LightDM, `lightdm-gtk-greeter` 2.0.9-compatible configuration, pytest, existing Valinor Lite installer/rollback/release machinery, SHA-256 identity manifests.

**Spec:** `docs/superpowers/specs/2026-10-02-arda-valinor-lite-greeter-identity-design.md`

## Global Constraints

- Preserve LightDM authentication and session-launch responsibility; ARDA owns presentation/configuration only.
- Canonical background is **Gate of Becoming**.
- Canonical mark is the approved architectural `A` / crown / world-tree ARDA emblem.
- Supported current stack: LightDM + `lightdm-gtk-greeter`.
- Detection outcomes: `LIGHTDM_GTK -> ALLOW`, `LIGHTDM_UNKNOWN -> NEEDS_YOU`, `OTHER_DM -> NEEDS_YOU`.
- Valinor Lite may claim `SOFTWARE ROOT VERIFIED`, `ENFORCEMENT AUDIT`, and `KERNEL 6.12.96-valinor` only when those states are verified.
- Valinor Lite must never imply `HARDWARE ROOTED`, `TPM VERIFIED`, or `FSVERITY_STRICT` unless actually true under the appropriate profile.
- No real LightDM restart during development or simulated installation tests.
- No greeter mutation before successful installer preflight and backup.
- Rollback must restore exact prior LightDM config and pre-existing asset bytes.
- Unknown display managers must never be silently reconfigured.
- Greeter assets must be canonical identity-manifest entries and release-manifest verified.
- Generated release artifacts must remain free of `__pycache__`, `.pyc`, stock-theme clutter, and arbitrary host LightDM state.

## Review Focus

- Existing LightDM config contains unrelated custom settings: preserve those bytes on rollback and do not discard them silently during backup/restore.
- LightDM is present but the selected greeter is not GTK: return `NEEDS_YOU` and perform zero greeter mutation.
- Canonical background/logo files are missing or tampered: installer/verifier must refuse rather than configure broken paths.
- A second identical install sees already-installed directories and files: it must converge without backup errors and remain rollback-safe.
- Lite trust metadata is malformed or attempts a hardware-rooted claim: validation must reject the unsupported claim rather than render it.

---

## File Structure

### New files

- `arda_os/kernel/valinor/lite/identity/greeter/gate-of-becoming.webp` — canonical greeter background.
- `arda_os/kernel/valinor/lite/identity/greeter/arda-mark.png` — canonical ARDA mark.
- `arda_os/kernel/valinor/lite/identity/greeter/lightdm-gtk-greeter.conf` — canonical static base config template.
- `arda_os/kernel/valinor/lite/installer/greeter.py` — detection, rendering, verification, and trust-copy validation.
- `arda_os/backend/tests/test_valinor_lite_greeter.py` — focused adapter/config/identity tests.

### Modified files

- `arda_os/kernel/valinor/lite/identity/manifest.json` — add required greeter identity records.
- `arda_os/kernel/valinor/lite/installer/install.py` — add greeter paths and install/config/verify transaction phases.
- `arda_os/kernel/valinor/lite/installer/rollback.py` — no new rollback architecture expected; ensure existing manifest-driven restore covers greeter paths.
- `arda_os/backend/tests/test_valinor_lite_installer.py` — installer transaction coverage for greeter phases/custody.
- `arda_os/backend/tests/test_valinor_lite_rollback.py` — exact config/assets restoration coverage.
- `arda_os/backend/tests/test_valinor_lite_install_gauntlet.py` — end-to-end greeter integration.
- `arda_os/backend/tests/test_valinor_lite_identity.py` — canonical greeter manifest/hash checks.
- `arda_os/backend/tests/test_valinor_lite_release.py` — bundle contains canonical greeter identity and excludes host state.
- `arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md` — operator instructions and no-auto-restart boundary.

---

### Task 1: Package Canonical Greeter Identity

**Files:**
- Create: `arda_os/kernel/valinor/lite/identity/greeter/gate-of-becoming.webp`
- Create: `arda_os/kernel/valinor/lite/identity/greeter/arda-mark.png`
- Create: `arda_os/kernel/valinor/lite/identity/greeter/lightdm-gtk-greeter.conf`
- Modify: `arda_os/kernel/valinor/lite/identity/manifest.json`
- Modify: `arda_os/backend/tests/test_valinor_lite_identity.py`

**Interfaces:**
- Consumes: approved Gate of Becoming source asset and approved ARDA mark source asset.
- Produces: canonical paths `greeter/gate-of-becoming.webp`, `greeter/arda-mark.png`, `greeter/lightdm-gtk-greeter.conf` with required SHA-256 manifest entries.

- [ ] **Step 1: Write failing identity tests**

Add tests asserting:

```python
assert greeter_background_record["role"] == "greeter_background"
assert greeter_logo_record["role"] == "greeter_logo"
assert greeter_config_record["role"] == "greeter_config"
assert all(record["status"] == "required" for record in greeter_records)
assert sha256(asset_path) == record["sha256"]
```

Also assert the canonical config contains:

```ini
[greeter]
background=/usr/share/arda/greeter/gate-of-becoming.webp
user-background=false
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH="$PWD/arda_os" /usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_valinor_lite_identity.py
```

Expected: FAIL because greeter identity assets/manifest records do not yet exist.

- [ ] **Step 3: Copy the approved assets into canonical identity paths**

Preserve the approved source pixels. Do not regenerate or recompress unless necessary for deterministic packaging.

- [ ] **Step 4: Create the canonical GTK greeter base config**

Pin only settings supported by current `lightdm-gtk-greeter` and required by the spec. At minimum:

```ini
[greeter]
background=/usr/share/arda/greeter/gate-of-becoming.webp
user-background=false
```

Do not add authentication/session behavior.

- [ ] **Step 5: Update `identity/manifest.json` with exact SHA-256 values**

Use roles:

```text
greeter_background
greeter_logo
greeter_config
```

All three are `required`.

- [ ] **Step 6: Run identity tests GREEN**

Expected: all identity tests PASS.

- [ ] **Step 7: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/identity/greeter/gate-of-becoming.webp \
arda_os/kernel/valinor/lite/identity/greeter/arda-mark.png \
arda_os/kernel/valinor/lite/identity/greeter/lightdm-gtk-greeter.conf \
arda_os/kernel/valinor/lite/identity/manifest.json \
arda_os/backend/tests/test_valinor_lite_identity.py

git commit -m "feat: package canonical ARDA greeter identity"
```

---

### Task 2: Add LightDM GTK Greeter Detection and Rendering

**Files:**
- Create: `arda_os/kernel/valinor/lite/installer/greeter.py`
- Create: `arda_os/backend/tests/test_valinor_lite_greeter.py`

**Interfaces:**
- Consumes: observed display-manager service target, available xgreeter desktop entries, canonical identity asset root, Lite trust metadata.
- Produces:

```python
@dataclass(frozen=True)
class GreeterDetection:
    state: Literal["ALLOW", "NEEDS_YOU"]
    manager: str
    greeter: str
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class GreeterVerification:
    ok: bool
    background_verified: bool
    logo_verified: bool
    config_verified: bool
    truthful_lite_copy: bool
    failures: tuple[str, ...]
```

Functions:

```python
def detect_greeter(
    *,
    display_manager_target: str,
    xgreeter_entries: tuple[str, ...],
) -> GreeterDetection


def render_lightdm_gtk_config(
    *,
    background_path: str,
    user_background: bool = False,
) -> str


def validate_lite_trust_copy(
    *,
    profile: str,
    software_rooted: bool,
    enforcement_mode: str,
    hardware_rooted: bool,
) -> tuple[bool, tuple[str, ...]]


def verify_greeter(
    *,
    config_text: str,
    background_sha256: str,
    expected_background_sha256: str,
    logo_sha256: str,
    expected_logo_sha256: str,
    trust_copy_ok: bool,
) -> GreeterVerification
```

- [ ] **Step 1: Write failing adapter tests**

Tests must pin:

```text
lightdm.service + lightdm-gtk-greeter.desktop -> ALLOW
lightdm.service + unknown greeter -> NEEDS_YOU
other display-manager target -> NEEDS_YOU
```

Also test:

```python
assert "background=/usr/share/arda/greeter/gate-of-becoming.webp" in rendered
assert "user-background=false" in rendered
```

And Lite trust-copy rejection:

```python
assert validate_lite_trust_copy(
    profile="lite",
    software_rooted=True,
    enforcement_mode="audit",
    hardware_rooted=True,
)[0] is False
```

Review-focus test: unrelated custom existing config text must not be passed through the renderer as if canonical; backup/restore owns preservation, renderer owns deterministic ARDA output.

- [ ] **Step 2: Run tests RED**

Expected: import failure for missing `installer.greeter`.

- [ ] **Step 3: Implement the minimal adapter**

Use pure functions and dataclasses. Do not read `/etc` directly inside the pure renderer/verifier functions. Keep host discovery injectable/testable.

- [ ] **Step 4: Run focused tests GREEN**

Expected: all greeter adapter tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/installer/greeter.py \
arda_os/backend/tests/test_valinor_lite_greeter.py

git commit -m "feat: detect and verify ARDA LightDM greeter"
```

---

### Task 3: Integrate Greeter Into Installer Transaction

**Files:**
- Modify: `arda_os/kernel/valinor/lite/installer/install.py`
- Modify: `arda_os/backend/tests/test_valinor_lite_installer.py`

**Interfaces:**
- Consumes: Task 2 `GreeterDetection`, canonical identity root, existing installer backup transaction.
- Produces: installed assets at `/usr/share/arda/greeter/*`, configured `/etc/lightdm/lightdm-gtk-greeter.conf`, and phases:

```text
INSTALL_GREETER_IDENTITY
CONFIGURE_GREETER
VERIFY_GREETER
```

- [ ] **Step 1: Write failing installer tests**

Add tests asserting:

```python
assert "INSTALL_GREETER_IDENTITY" in events
assert "CONFIGURE_GREETER" in events
assert "VERIFY_GREETER" in events
```

Assert destination bytes equal canonical identity bytes.

Assert `/etc/lightdm/lightdm-gtk-greeter.conf` is included in backup before mutation.

Review-focus tests:

- `NEEDS_YOU` detection yields install refusal before greeter mutation.
- missing/tampered canonical greeter asset yields refusal before writing greeter config.
- second identical install succeeds and converges.

- [ ] **Step 2: Run installer tests RED**

Expected: missing greeter phases/paths.

- [ ] **Step 3: Extend `_planned_paths()`**

Add:

```text
/usr/share/arda/greeter/gate-of-becoming.webp
/usr/share/arda/greeter/arda-mark.png
/etc/lightdm/lightdm-gtk-greeter.conf
```

The existing parent-provenance machinery must automatically cover new directories.

- [ ] **Step 4: Add installer inputs for greeter support**

Extend `install_valinor_lite(...)` with a minimal explicit greeter input rather than reading the live host implicitly. Preserve existing call sites through a default only if semantics remain unambiguous; otherwise update all tests/callers in the same task.

The implementer must use Task 2's `GreeterDetection` and verifier, not duplicate detection logic.

- [ ] **Step 5: Install assets and deterministic config in transaction order**

No LightDM restart. No shelling out to `systemctl restart lightdm`.

- [ ] **Step 6: Verify transaction GREEN**

Run:

```bash
PYTHONPATH="$PWD/arda_os" /usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_valinor_lite_installer.py \
arda_os/backend/tests/test_valinor_lite_greeter.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -f \
arda_os/kernel/valinor/lite/installer/install.py \
arda_os/backend/tests/test_valinor_lite_installer.py

git commit -m "feat: install ARDA LightDM greeter transactionally"
```

---

### Task 4: Prove Exact Greeter Rollback

**Files:**
- Modify: `arda_os/backend/tests/test_valinor_lite_rollback.py`
- Modify: `arda_os/kernel/valinor/lite/installer/rollback.py` only if the tests expose a real gap.

**Interfaces:**
- Consumes: Task 3 backup records and existing Task 6 rollback engine.
- Produces: exact restoration of prior LightDM config/assets and topology.

- [ ] **Step 1: Write failing integration-style rollback tests**

Use a real Task 3 install to generate backup metadata, then rollback it.

Assert:

```python
assert restored_config_bytes == original_config_bytes
assert restored_background_bytes == original_background_bytes
assert restored_logo_bytes == original_logo_bytes
```

Also test a host where greeter asset destinations did not exist before install; rollback must remove them and prune only proven-new empty parents.

Review-focus test: if an unrelated file is placed inside `/usr/share/arda/greeter/` after install, rollback must not delete the non-empty directory.

- [ ] **Step 2: Run rollback tests**

Expected: PASS if existing manifest-driven rollback is sufficiently generic. If RED, investigate root cause before modifying `rollback.py`.

- [ ] **Step 3: Implement only any proven rollback gap**

Do not add greeter-specific deletion heuristics if generic backup provenance already solves it.

- [ ] **Step 4: Run installer + rollback tests GREEN**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f \
arda_os/backend/tests/test_valinor_lite_rollback.py
# Add rollback.py only if changed.

git commit -m "test: prove ARDA greeter rollback custody"
```

---

### Task 5: Integrate Greeter Into Portable Release

**Files:**
- Modify: `arda_os/backend/tests/test_valinor_lite_release.py`
- Modify: `arda_os/kernel/valinor/lite/build_release.py` only if focused tests prove it is not already generic enough.

**Interfaces:**
- Consumes: canonical identity tree from Task 1.
- Produces: release archive containing greeter assets and their manifest hashes without host LightDM state.

- [ ] **Step 1: Write failing release assertions**

Assert extracted bundle contains:

```text
identity/greeter/gate-of-becoming.webp
identity/greeter/arda-mark.png
identity/greeter/lightdm-gtk-greeter.conf
```

Assert all hashes verify.

Assert bundle does **not** contain:

```text
/etc/lightdm/
lightdm.service state
host-generated greeter config
__pycache__
*.pyc
```

- [ ] **Step 2: Run release tests**

If current identity staging is generic, tests may already pass. If they fail, the failure must identify the exact staging gap.

- [ ] **Step 3: Make minimal builder change only if required**

Preserve the explicit release allowlist philosophy. Do not recursively capture host state.

- [ ] **Step 4: Run release tests GREEN**

Expected: PASS.

- [ ] **Step 5: Build and offline-verify a candidate release**

Use the preserved real kernel archive and existing candidate-build workflow.

Expected bundled verifier output:

```text
ALL HASHES PASS
```

- [ ] **Step 6: Commit**

```bash
git add -f \
arda_os/backend/tests/test_valinor_lite_release.py
# Add build_release.py only if changed.

git commit -m "test: carry ARDA greeter through portable release"
```

---

### Task 6: Extend Full Simulated Installation Gauntlet

**Files:**
- Modify: `arda_os/backend/tests/test_valinor_lite_install_gauntlet.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: end-to-end acceptance evidence that greeter identity survives install, second install, verification, and rollback.

- [ ] **Step 1: Extend the simulated host fixture**

Seed a prior LightDM GTK config and optional prior greeter assets.

- [ ] **Step 2: Add greeter acceptance assertions**

After first install:

```python
assert installed_background_hash == canonical_background_hash
assert installed_logo_hash == canonical_logo_hash
assert "background=/usr/share/arda/greeter/gate-of-becoming.webp" in installed_config
assert "user-background=false" in installed_config
```

Assert Lite trust copy remains truthful.

After second install:

```python
assert after_second == after_first
```

After rollback:

```python
assert lightdm_config_bytes == original_lightdm_config_bytes
assert original_boot_and_greeter_topology_restored
```

- [ ] **Step 3: Run gauntlet GREEN**

Run:

```bash
PYTHONPATH="$PWD/arda_os" /usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py
```

Expected: all gauntlet tests PASS.

- [ ] **Step 4: Commit**

```bash
git add -f \
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py

git commit -m "test: add ARDA greeter to Valinor Lite gauntlet"
```

---

### Task 7: Document Operator Workflow and Run Final Regression

**Files:**
- Modify: `arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md`

**Interfaces:**
- Consumes: completed greeter implementation.
- Produces: operator instructions for install, verification, and deliberate greeter activation.

- [ ] **Step 1: Update operator documentation**

Document:

- Gate of Becoming + ARDA mark canonical identity.
- LightDM GTK support boundary.
- no automatic display-manager restart.
- how to inspect installed greeter config.
- logout/reboot as the deliberate point where the operator sees the new greeter.
- rollback restores previous LightDM config.
- Lite trust-copy restrictions.

- [ ] **Step 2: Run complete Valinor Lite focused suite**

```bash
PYTHONPATH="$PWD/arda_os" /usr/bin/python3 -m pytest -q \
arda_os/backend/tests/test_attestation_profile.py \
arda_os/backend/tests/test_phase4_attestation_profiles.py \
arda_os/backend/tests/test_valinor_lite_evidence.py \
arda_os/backend/tests/test_valinor_lite_identity.py \
arda_os/backend/tests/test_valinor_lite_preflight.py \
arda_os/backend/tests/test_valinor_lite_greeter.py \
arda_os/backend/tests/test_valinor_lite_installer.py \
arda_os/backend/tests/test_valinor_lite_rollback.py \
arda_os/backend/tests/test_verify_valinor_lite.py \
arda_os/backend/tests/test_valinor_lite_release.py \
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py
```

Expected: all PASS.

- [ ] **Step 3: Run broad backend regression**

```bash
PYTHONPATH="$PWD/arda_os" /usr/bin/python3 -m pytest -q \
arda_os/backend/tests
```

Expected baseline unless independently repaired:

```text
e2e_threat_pipeline_test.py::test_threat_pipeline
test_secret_fire_gauntlet.py::test_sovereign_harmony
test_harmonic_engine_cadence.py::test_score_observation_spam_attack
```

Any additional failure blocks completion.

- [ ] **Step 4: Audit Git state**

```bash
git diff --check
git status --short
git diff --cached --check
```

Never stage the unrelated LFS proof bundle, preserved kernel archive, `config/`, generated release archives, or Python bytecode.

- [ ] **Step 5: Commit documentation**

```bash
git add -f \
arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md

git commit -m "docs: document ARDA Valinor Lite greeter"
```

- [ ] **Step 6: Final branch verification**

```bash
git log --oneline -12
git status --short
```

Do not restart LightDM as part of automated verification.
