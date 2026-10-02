# Valinor Lite Portable Install — Design

Date: 2026-10-02

## Purpose

Valinor Lite carries the proven Valinor execution-authority substrate
onto ordinary Debian x86_64 machines that do not have a physical TPM.

It preserves Valinor's technical behavior and ceremonial identity while
truthfully degrading hardware-rooted attestation when no TPM is present.

Valinor Lite must be easy to install on an existing Debian system and
must coexist safely with another operating system such as Windows.

## Core Principle

Execution does not equal authority.

Valinor Lite preserves that principle through the same kernel and
deterministic BPF enforcement substrate used by full Valinor.

The absence of a TPM may reduce the strength of platform attestation.
It must never silently weaken, fake, or relabel evidence.

## Kernel

Valinor Lite uses the preserved kernel:

    Linux 6.12.96-valinor

Canonical kernel SHA-256:

    875117b4148753e407725a3d3d838d8f40db95111c88eabd329f9d229414a527

Canonical initramfs SHA-256:

    e1c9cd2c1694b28761d486a3662ec8e32803871bd7bd8de11d382824c382c7ec

The first Lite release does NOT rebuild the kernel.

The preserved kernel already provides:

- CONFIG_BPF_SYSCALL=y
- CONFIG_BPF_LSM=y
- CONFIG_FS_VERITY=y
- CONFIG_SECURITYFS=y
- CONFIG_IMA=y
- CONFIG_EVM=y
- TPM support when hardware is available

TPM support being compiled into the kernel does not make a TPM mandatory.

## Trust Profiles

ARDA gains an explicit attestation profile.

### FULL

    ARDA_ATTESTATION_PROFILE=full

Semantics:

- TPM expected
- TPM quote required where configured
- PCR evidence may be required
- hardware-rooted claims permitted only when verified
- missing mandatory TPM evidence causes REFUSE

### LITE

    ARDA_ATTESTATION_PROFILE=lite

Semantics:

- physical TPM is optional
- hardware_rooted=false when TPM is absent
- tpm_available=false when TPM is absent
- tpm_quote_verified=false when no quote exists
- software_rooted=true only when Lite evidence passes
- no simulated TPM evidence
- no fake PCR values
- no promotion of software evidence into hardware-rooted evidence

Lite evidence includes, where available:

- canonical kernel hash
- canonical initramfs hash
- BPF LSM availability
- pinned ARDA enforcement maps
- fs-verity / measured-execution evidence
- active generation state
- current cgroup binding
- native PQC receipt verification
- Secure Boot state as an independent fact
- filesystem and boot provenance

Secure Boot alone does not imply hardware_rooted=true.

## Enforcement

Lite preserves the Valinor execution-authority substrate:

- BPF LSM
- audit mode
- fsverity_strict mode
- measured execution
- active generations
- deny telemetry
- Tulkas enforcement reporting
- Lórien rollback/recovery
- deterministic authority decisions

Lite must retain the ability to demonstrate a real kernel refusal.

TPM absence must not disable BPF enforcement.

## PQC

Native PQC remains mandatory for claims that depend on PQC sealing.

Existing native implementation:

- provider: liboqs
- signature family: ML-DSA
- tested algorithm: ML-DSA-65

Simulation must not satisfy a native-PQC-required gate.

## Boot Identity

Valinor Lite preserves the ceremonial identity of the original system.

The historical master snapshot remains immutable:

    valinor-boot-snapshot.tar.zst

A clean portable identity payload is derived from that snapshot.

### GRUB Identity

Preserve the ARDA Sovereign visual language, including:

- ARDA OS heading
- LAW OF THE SUBSTRATE subheading
- "Nothing manifests without lawful authority." footer
- existing colors
- layout
- spacing
- timeout/progress presentation
- ARDA visual assets

The original ARDA GRUB identity is installed independently of Debian's
stock desktop-base/Ceratopsian visuals.

Stock Debian theme assets are not part of Valinor Lite identity.

### Plymouth Identity

Install both preserved ARDA Plymouth experiences:

    arda-sovereign
    arda-mirror-gate

ARDA Sovereign includes:

- background.png
- seal.png
- arda.script
- arda-sovereign.plymouth

ARDA Mirror Gate includes:

- background.png
- mirror-gate.png
- seal.png
- arda-mirror.script
- arda-mirror-gate.plymouth

The installer chooses one documented default while retaining both.

### Awakening Audio

Canonical identity audio:

    arda-awakening.wav

Canonical preserved WAV SHA-256:

    90f0e19a8b9318ac6472caa28f85894aebaaae69113cc69a45b9e88cfa0bbc

The Lite installer installs this as a first-class ARDA identity asset.

Audio playback must not block successful boot.

Failure to play the awakening sound is non-fatal and must be reported
separately from security/enforcement status.

## Boot Menu

The installer must create a safe Debian-first dual-boot structure.

Intended menu semantics:

    VALINOR LITE · Linux 6.12.96-valinor
    Debian fallback
    Advanced options
    Windows (when detected)
    UEFI Firmware Settings (when supported)

The installer must not delete or overwrite an existing Windows EFI
loader.

A working Debian distribution kernel must remain installed as fallback.

Valinor must not become the only bootable kernel during installation.

## Easy Installer

Primary interface:

    sudo ./install-valinor-lite

The installer is interactive and idempotent.

It performs:

1. platform census
2. Debian/x86_64 verification
3. EFI/BIOS detection
4. TPM detection
5. Secure Boot observation
6. existing kernel inventory
7. Windows/other OS detection
8. free-space and boot filesystem checks
9. backup of current GRUB/Plymouth configuration
10. archive checksum verification
11. kernel installation
12. module installation
13. initramfs registration/verification
14. Lite attestation profile installation
15. ARDA identity installation
16. Plymouth configuration
17. awakening-audio installation
18. GRUB theme/menu configuration
19. update-grub
20. verification of generated entries
21. post-install health report

No irreversible step occurs before preflight succeeds.

## Safety and Rollback

Before modifying boot configuration, create a timestamped backup of:

- /etc/default/grub
- /etc/grub.d
- /boot/grub
- active Plymouth configuration
- relevant EFI metadata

Installer must provide:

    sudo ./install-valinor-lite --rollback

Rollback restores boot configuration without deleting user data.

The installer must never:

- format a partition
- resize a partition
- delete Windows
- delete an EFI loader
- remove the distribution fallback kernel
- enable fsverity_strict globally as part of installation
- claim TPM-backed trust without a TPM
- require network access after artifacts have been downloaded

## Installation Artifacts

Portable release structure:

    valinor-lite/
    ├── install-valinor-lite
    ├── manifest/
    │   ├── SHA256SUMS
    │   └── release.json
    ├── kernel/
    │   └── valinor-kernel-6.12.96.tar.zst
    ├── identity/
    │   ├── grub/
    │   ├── plymouth/
    │   │   ├── arda-sovereign/
    │   │   └── arda-mirror-gate/
    │   └── audio/
    │       └── arda-awakening.wav
    ├── profile/
    │   └── valinor-lite.env
    └── verify/
        └── verify-valinor-lite

The historical full boot snapshot is retained separately and is not
used directly as the install payload.

## Verification

Successful installation requires proving, not assuming:

- installed kernel hash matches manifest
- installed initramfs exists
- module tree exists
- GRUB contains Valinor entry
- fallback Debian entry remains
- Windows entry remains when Windows was present before installation
- ARDA GRUB assets match manifest
- ARDA Plymouth assets match manifest
- awakening WAV matches manifest
- selected Plymouth theme resolves
- Lite profile reports its trust boundary honestly
- TPM absence produces hardware_rooted=false
- BPF LSM remains available after Valinor boot
- native PQC self-test succeeds where native-PQC claims are enabled

## First-Boot State

Valinor Lite boots conservatively.

Default enforcement state:

    audit

Strict enforcement is never automatically promoted merely because the
installer completed successfully.

After first boot the verifier reports:

    TRUST PROFILE
    TPM
    HARDWARE ROOT
    SOFTWARE ROOT
    KERNEL IDENTITY
    BPF LSM
    PQC
    ENFORCEMENT MODE

Example on a machine without TPM:

    TRUST PROFILE .............. VALINOR_LITE
    TPM ......................... ABSENT
    HARDWARE ROOT ............... UNAVAILABLE
    SOFTWARE ROOT ............... VERIFIED
    KERNEL IDENTITY ............. VERIFIED
    BPF LSM ..................... VERIFIED
    PQC ......................... VERIFIED
    ENFORCEMENT MODE ............ AUDIT

## Historical Preservation Boundary

The original snapshot is evidence of the historical Valinor machine.

Do not rewrite it to make it cleaner.

Derived Lite artifacts may remove unrelated Debian stock themes, but
the historical snapshot remains byte-for-byte preserved.

## Success Criteria

Valinor Lite succeeds when a clean Debian x86_64 laptop without a TPM
can:

1. install Valinor without losing Debian or Windows bootability;
2. boot Linux 6.12.96-valinor;
3. display the preserved ARDA visual identity;
4. use the preserved ARDA awakening sound;
5. report TPM absence truthfully;
6. establish software-rooted evidence;
7. retain native PQC evidence;
8. retain BPF LSM authority enforcement;
9. recover safely through a Debian fallback kernel;
10. uninstall or rollback the boot integration without user-data loss.
