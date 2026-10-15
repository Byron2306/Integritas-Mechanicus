# ARDA Valinor Debian Candidate 0.1.4

Date: 2026-10-15

## Artifact

`build/arda-valinor_0.1.4_amd64.deb`

SHA256:

`28a5704ff33c09755139ed163ed666caa4b59e23febc85cba173be62df813497`

## Package contract

The package installs ARDA Valinor hardware-rooted enrollment machinery.

Package installation itself does NOT:

- enroll the host
- mint measured identity
- write live attested-host verifier configuration
- activate the continuous-proof timer
- import current host TPM state
- import PCR11 state
- import a generation database
- import machine identity
- import a signed verdict
- import verifier private signing material

## Portable contents

The package includes:

- `arda-install`
- `arda-preflight`
- `arda-doctor`
- `arda-enroll`
- `arda-attest`
- `arda-grade`
- constitutional policy
- active projection plan
- Intel EK trust anchors
- verifier public key
- `arda-valinor-postboot.service`
- `arda-valinor-postboot.timer`
- attested-host configuration template

## Continuous proof contract

Continuous proof is armed only after successful hardware-rooted enrollment.

Ordering:

1. Step 70 hardware-rooted OS-grade PASS
2. Step 80 continuous proof configuration
3. timer enablement

The timer refresh interval is five minutes.

## Portable identity boundary

Installed configuration contains no:

- `arda-gen1-restoration-verifier`
- `arda-phase4-loopback-restoration`
- verifier private key configuration

No host/private state files were found in the package.

Generic source code may contain verifier-related environment variable names.
Those references are implementation capability, not bundled signing authority.

## Disposable Debian acceptance

Installed successfully into a disposable Debian 13 container.

Observed:

- package version `0.1.4`
- all installer commands present
- postboot service present
- postboot timer present
- `/etc/arda/attested-host.env` absent
- enrollment state empty
- portable trust anchors present

Dry-run correctly REFUSED because the disposable container lacked:

- TPM device
- Secure Boot state
- kernel lockdown state

This refusal is expected and confirms fail-closed behavior.

The container shared the host Valinor kernel, but kernel visibility alone was
insufficient to pass hardware-rooted enrollment.

## Invariant

Migrate machinery, never machine identity.
