# ARDA Valinor Lite Greeter Identity Design

**Date:** 2026-10-02  
**Status:** Approved design draft  
**Scope:** ARDA Valinor Lite greeter identity, LightDM GTK integration, installer/rollback custody

## 1. Purpose

Replace the stock Debian-looking login experience with a canonical ARDA Valinor Lite greeter while preserving the existing authentication boundary.

The greeter must feel like the final stage of the ARDA boot ritual:

```text
GRUB
ARDA SOVEREIGN
    ↓
PLYMOUTH
MIRROR GATE
    ↓
LIGHTDM
GATE OF BECOMING
    ↓
SESSION
VALINOR
```

The greeter must not replace LightDM authentication logic. ARDA owns presentation and configuration only.

## 2. Existing Platform Truth

Current host:

- display manager: LightDM
- active service: `lightdm.service`
- greeter package: `lightdm-gtk-greeter`
- greeter desktop entries: `lightdm-greeter.desktop`, `lightdm-gtk-greeter.desktop`
- current `/etc/lightdm/lightdm-gtk-greeter.conf` is effectively stock/default
- canonical Valinor Lite identity already includes GRUB, Plymouth, and boot audio payloads
- installer and rollback already preserve transactional backup evidence

## 3. Canonical Visual Direction

### Background

Use **Gate of Becoming** as the canonical greeter background.

### Logo

Use the new fourth ARDA logo concept as the canonical greeter logo: the architectural `A` mark with crown, world-tree/light structure, and celestial geometry.

The greeter should use the emblem itself as the primary mark rather than relying on a giant text-heavy lockup.

### Visual hierarchy

```text
                    [ ARDA MARK ]

                        ARDA
                   VALINOR LITE

           Nothing manifests without
                lawful authority.

                [ user selector ]
                [ password box ]
                [ ENTER VALINOR ]

          SOFTWARE ROOT · VERIFIED
          KERNEL 6.12.96-valinor
          ENFORCEMENT · AUDIT
```

The design should be restrained and legible at laptop resolutions. The background provides atmosphere; the login card remains clear and usable.

## 4. Trust Semantics

Valinor Lite may truthfully display:

```text
VALINOR LITE
SOFTWARE ROOT VERIFIED
ENFORCEMENT AUDIT
KERNEL 6.12.96-valinor
```

It must not imply `HARDWARE ROOTED`, `TPM VERIFIED`, or `FSVERITY_STRICT` unless those states are actually verified under the Full profile.

The greeter must never upgrade trust claims based on visual branding.

## 5. Canonical Identity Payload

Add a new identity family:

```text
arda_os/kernel/valinor/lite/identity/greeter/
├── gate-of-becoming.webp
├── arda-mark.png
└── lightdm-gtk-greeter.conf
```

The identity manifest must hash-pin every required greeter asset.

Suggested manifest roles: `greeter_background`, `greeter_logo`, `greeter_config`.

Greeter assets are canonical ARDA identity and therefore participate in release manifest verification.

## 6. Runtime Installation Layout

Install canonical assets to deterministic paths:

```text
/usr/share/arda/greeter/gate-of-becoming.webp
/usr/share/arda/greeter/arda-mark.png
/etc/lightdm/lightdm-gtk-greeter.conf
```

Optional generated or adapter-specific files may live under `/etc/arda/greeter/` if needed for recorded state, but ARDA should avoid duplicating configuration without a reason.

## 7. LightDM Strategy

### Preferred adapter

Use the existing `lightdm-gtk-greeter`.

Do not replace LightDM authentication code and do not introduce a custom greeter application.

### Detection outcomes

```text
LIGHTDM_GTK      ALLOW
LIGHTDM_UNKNOWN  NEEDS_YOU
OTHER_DM         NEEDS_YOU
```

The installer must refuse to silently reconfigure an unsupported display manager.

### Base GTK greeter configuration

The generated canonical configuration should include at minimum:

```ini
[greeter]
background=/usr/share/arda/greeter/gate-of-becoming.webp
user-background=false
```

Additional theme, icon, font, position, panel, and clock settings may be included only if validated against the installed `lightdm-gtk-greeter` version.

No authentication behavior may be altered for cosmetic reasons.

## 8. Debian Branding Boundary

The goal is to remove or visually suppress generic Debian branding from the login surface, including stock Debian wallpaper, dominant `Debian 13` presentation, and generic distro-first greeter styling.

Debian remains the underlying operating system substrate and must not be falsified in system metadata.

If residual Debian branding comes from a component outside the configured GTK greeter, the installer must identify that component before modifying it. It must not blindly patch LightDM internals.

## 9. Installer Transaction

Extend the Valinor Lite installer transaction:

```text
PREFLIGHT
    ↓
BACKUP
    ↓
INSTALL_GREETER_IDENTITY
    ↓
CONFIGURE_GREETER
    ↓
VERIFY_GREETER
    ↓
COMMIT_INSTALL_STATE
```

The greeter paths must be included in the installer's planned-path custody set.

Before mutation, backup must capture:

- existing `/etc/lightdm/lightdm-gtk-greeter.conf`
- pre-existing ARDA greeter asset destinations
- parent-directory provenance where needed

No greeter mutation occurs before successful preflight and backup.

## 10. Rollback

Rollback must restore the exact prior greeter state from the recorded backup generation.

Requirements:

- restore previous LightDM GTK greeter config byte-for-byte
- restore any pre-existing assets
- remove only ARDA greeter paths proven to be installer-created
- prune only empty parent directories proven absent before install
- never alter Windows EFI, unrelated kernels, or unrelated display-manager files
- never discover or guess another backup generation

Repeated rollback must remain safe.

## 11. Greeter Verification

Provide deterministic verification that checks:

- configured display manager is LightDM
- selected greeter is compatible
- canonical background exists and hash matches
- canonical ARDA mark exists and hash matches
- active greeter config points to canonical background
- user background is disabled
- no unsupported trust claim is rendered from Lite configuration

Verification is observational and must not restart LightDM automatically during tests or installation simulation.

A real display-manager restart or logout remains a deliberate operator action.

## 12. Testing

Create focused tests for:

1. canonical greeter assets exist
2. identity manifest includes exact greeter hashes
3. LightDM GTK detection returns `ALLOW`
4. unknown LightDM greeter returns `NEEDS_YOU`
5. non-LightDM display manager returns `NEEDS_YOU`
6. generated config selects Gate of Becoming
7. generated config disables per-user background
8. Lite greeter metadata never claims hardware-rooted trust
9. installer backs up prior greeter config before mutation
10. installer installs canonical greeter assets
11. second install is idempotent
12. rollback restores prior greeter config
13. rollback restores prior greeter assets
14. rollback removes only installer-created greeter paths
15. full simulated Valinor Lite installation gauntlet includes greeter identity

## 13. Release Bundle Integration

The Task 8 release builder must include the new greeter identity family through the canonical identity payload.

No recursive copy of arbitrary host LightDM state is allowed.

Generated release archives must remain free of Python bytecode and unrelated desktop themes.

## 14. Files Expected to Change

```text
arda_os/kernel/valinor/lite/identity/greeter/
arda_os/kernel/valinor/lite/identity/manifest.json
arda_os/kernel/valinor/lite/installer/greeter.py
arda_os/kernel/valinor/lite/installer/install.py
arda_os/kernel/valinor/lite/installer/rollback.py
arda_os/backend/tests/test_valinor_lite_greeter.py
arda_os/backend/tests/test_valinor_lite_install_gauntlet.py
arda_os/kernel/valinor/lite/VALINOR_LITE_INSTALLATION.md
```

The release builder may require focused changes if identity handling is not already generic enough.

## 15. Non-Goals

This task does not:

- build a custom authentication greeter
- replace LightDM
- install Debian itself
- repartition disks
- modify Windows
- enable strict enforcement
- claim hardware-rooted trust for Lite
- restart the active display manager automatically during development

## 16. Safety Rules

- no real greeter mutation before focused and simulated tests pass
- no automatic LightDM restart
- no blind patching of unknown display-manager components
- preserve exact prior config for rollback
- preserve user login capability above visual perfection
- keep Lite trust language truthful

## 17. Acceptance

Task is accepted when:

- Gate of Becoming is the canonical login background
- the new ARDA mark is canonical greeter identity
- LightDM GTK is configured deterministically
- Debian visual dominance is removed from the greeter
- Lite trust text remains truthful
- installer and rollback preserve greeter custody
- repeated install converges
- simulated installation gauntlet passes
- release bundle carries and verifies the greeter identity
- no real display-manager restart was required to prove correctness
