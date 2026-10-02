# Valinor Lite Installation

Valinor Lite is the software-rooted deployment profile for machines
without a usable TPM.

It uses the Valinor kernel, BPF LSM authority, measured execution,
native PQC verification, canonical ARDA identity, transactional install,
and deterministic rollback.

It does not claim hardware-rooted trust.

## Trust Boundary

Expected no-TPM state:

TRUST PROFILE .............. VALINOR_LITE
TPM ......................... ABSENT
HARDWARE ROOT ............... UNAVAILABLE
SOFTWARE ROOT ............... VERIFIED
ENFORCEMENT MODE ............ AUDIT

TPM presence or Secure Boot alone never upgrades Lite to hardware-rooted
trust.

## First Real-Machine Rule

The first real action is only:

./install-valinor-lite --preflight

Do not run --install until preflight has been reviewed.

## Release Verification

Verify the archive:

sha256sum -c valinor-lite-6.12.96.tar.zst.sha256

Then verify the bundled manifest offline.

Archive SHA256:
cd18653a510cf0e2f67ff00006d22b09ede74983051c770045f4a2b719e9071d

Kernel SHA256:
875117b4148753e407725a3d3d838d8f40db95111c88eabd329f9d229414a527

Initramfs SHA256:
e1c9cd2c1694b28761d486a3662ec8e32803871bd7bd8de11d382824c382c7ec

These hashes represent different trust boundaries.

## Installation

Only after approved preflight:

./install-valinor-lite --install

Initial enforcement is audit.

The installer must preserve Windows EFI state and a Debian fallback kernel.

## First-Boot Verification

Run:

./verify/verify-valinor-lite --evidence-file <evidence.json>

The verifier is observational and must never promote audit to
fsverity_strict.

## Rollback

Rollback uses the exact recorded backup generation.

It restores only recorded state, preserves Windows and unrelated fallback
kernels, and removes empty parent directories only when backup provenance
proves they did not exist before installation.

## Idempotency

A second installation of the same payload must converge to the same target
state.

To restore the machine to its state before the first installation, use the
first installation's recorded state and backup ID.

## Acceptance

The simulated gauntlet verifies:

- Full refuses a no-TPM host.
- Lite installs.
- Windows survives.
- Debian fallback survives.
- Valinor kernel installs.
- ARDA identity installs.
- Awakening WAV identity matches.
- Software root verifies.
- Hardware root remains unavailable.
- Enforcement remains audit.
- Second install is idempotent.
- Rollback restores the original boot state.

## Governing Principle

Execution does not equal authority.

Valinor Lite may claim software-rooted trust only when required evidence
verifies.

It must never fabricate hardware authority.
