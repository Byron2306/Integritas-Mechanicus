# Valinor hardware-rooted proof provisioning design

Date: 2026-10-09
Status: written specification approved by Byron on 2026-10-09.

## Intent and current evidence

Byron wants to repeat ARDA's July hardware-rooted OS-grade proof on the Debian
workstation running the updated `6.12.111-valinor` kernel. Success requires fresh
evidence of the running boot, authoritative blocking enforcement, trusted
measured identity, and TPM attestation. Reproducing historical JSON fields
without their underlying properties is not success.

The operator has demonstrated Secure Boot, integrity lockdown, efivarfs, UEFI
queries, Intel TPM 2.0 access, and a temporary audit attachment. The captured
ARDA program had tag `4fab89cb133d08ca`, program ID 98, link ID 4, and eight
referenced maps; a ninth fs-verity identity map existed but was not referenced.
IDs are observations of that attachment, not reusable configuration values.
The loader detached on timeout. No measured staging records, boot service,
`/etc/arda`, or original `arda_os/bin/arda` exist on this host.

The July checkpoint's Nuvoton identity, generation 112, approved PCRs, and
verdict must not be reused. Integrity lockdown satisfies this design's basic
lockdown requirement; confidentiality lockdown is a separate comparison to
the stronger July 30 checkpoint, not an automatic boot change.

## Approach and alternatives

Use the existing loader, generation ledger, measured identity and TPM services,
with a new operator CLI and explicit verification adapters. Correct their
verification gaps before exposing activation. This preserves the available
project contracts while identifying the implementation as a replacement.

Recovering a trusted backup of the original tools would preserve historical
behavior, but no backup has been located. Blind installation of the existing
service template is unsuitable: its dependencies and policy state are absent,
and its success predicate is not a full OS-grade evaluation.

## Scope and operator interface

Provide `arda_os/bin/arda` as a small executable Python entry point. Its new
reports identify `implementation: replacement-v1` and
`schema_version: arda.proof_report.v1`. Do not claim equivalence to the missing
historical gate. All commands support `--json`; errors produce structured
blockers and a nonzero exit code. Success exits 0, unmet prerequisites exit 1,
and invalid arguments exit 2. Never use a simulation fallback for live proof.

Commands:

- `proof inspect`: inspect boot signals, tool availability, artifact hashes,
  BPF program/link/map evidence, filesystem capabilities, generation state,
  manifest and verifier configuration. No arming, database creation, PCR
  extension, package installation, or service restart.
- `proof prepare --workspace PATH`: create a private recovery workspace with
  copied test executables, configuration templates, artifact identity, and a
  plan. No writes to `/etc`, firmware, package-managed files, or boot entries.
- `measured build --config PATH`: measure explicitly selected immutable files
  and sign a fresh manifest. Require operator-provisioned signing material;
  never manufacture a default trusted key or enroll one automatically.
- `measured verify --manifest PATH --config PATH`: verify trusted signature,
  timestamps, host/boot/cgroup binding, monotonic generation, actual fs-verity
  measurements, and file identities without consuming a generation.
- `proof test-scoped --config PATH`: run the disposable cgroup enforcement
  probe with bounded lifetime and report allowed execution, denied execution,
  kernel telemetry, and successful cleanup. Result scope is `scoped`.
- `proof attest --config PATH`: obtain a verifier challenge, capture fresh
  evidence, submit it, and verify the returned signed verdict. Explicitly
  report PCR11 extension. Do not automatically approve a baseline.
- `proof plan-host --config PATH`: produce a host activation plan and blockers.
  Enumerate required services/cgroups and recovery coverage.
- `proof activate-host --plan PATH --config PATH`: accept only a current,
  validated plan and explicitly selected host policy. Never activate an empty
  plan or activate host enforcement as a side effect of inspection.
- `os-grade --config PATH`: read-only appraisal of current evidence. Missing
  configuration returns blockers rather than bootstrapping state.
- `proof install-service --config PATH`: install the reviewed post-boot units
  only after manual host activation and verification pass. Installation does
  not reboot or change boot selection.

## Components and ownership

Keep the CLI thin. New focused modules under `backend/services` own proof
inspection/reporting, manifest cryptography and file measurement, scoped
orchestration/recovery, and host provisioning. Reuse the existing generation
ledger with transactionally enforced monotonicity. Reuse TPM capture and
verifier components only through adapters that perform independent checks.

Preserve existing local edits to `arda_lsm_loader.c`, `arda_physical_lsm.c`,
and `os_enforcement_service.py`. Build into a dedicated workspace, preserving
the supplied binaries and source hashes. Any necessary source change must be
reviewable as an addition to existing work, not a reset or overwrite.

Root-owned host configuration is `/etc/arda/proof.json`. It supplies trusted
manifest public key and key ID, local node identity, BPF artifact identity,
pin root, policy paths, verifier HTTPS endpoint and public key, approved PCR
baseline path, TPM trust anchors, and enrolled host scope. Template values are
examples, never effective defaults for trust or host activation. Private keys
are not emitted in reports or committed. The verifier signing private key
remains off the attested host for production use.

## Manifest verification and enforcement

Use canonical UTF-8 JSON with sorted keys and compact separators. An Ed25519
signature covers every manifest field except the signature bytes, including
signature algorithm and key ID, boot ID, scope, cgroup bindings and entries.
Trust comes from configured public keys, not keys embedded in the manifest.
Reject unknown keys, malformed signatures, naive timestamps, stale manifests,
generation replay, and host/boot/cgroup mismatch. Manifests expire at most 300
seconds after issuance for staging. Activation must occur during that window;
subsequent proof also needs current verified runtime evidence.

For every enrolled executable, open and measure the real file, require enabled
fs-verity, and compare the kernel-reported algorithm/digest and file identity
to the signed entry. Reject missing, mutable, substituted or unmeasurable
files. Cryptographic verification and file measurements precede staging and
generation commitment. Preserve the existing monotonic ledger even when its
staging table is empty.

The existing BPF path uses inode/device identities rather than digest lookup.
Do not treat its mode name as proof of content identity. The implementation
must bind trusted measurements of immutable files to runtime allowlist
identities and ensure identities cannot become stale or reused during a
proof session. Hold validated file handles throughout that session, recheck
the bindings before appraisal, and fail on changes. Persisted inode entries
alone cannot authorize a later boot or restarted session. If this binding
cannot be established with the existing object, block measured activation
and implement a reviewed kernel enforcement change before proceeding.

Scoped mode may enforce only a disposable enrolled cgroup; verify support in
the built object and loader before use. No policy redline flag is set merely
to reproduce the July rule count: the current source's redline path can veto
all non-audit executions. Constitutional policy must retain useful allow/deny
behavior, be explicit, and have an execution test. Never silently disable a
required policy check to make the result green.

## Recovery and host activation

Scoped tests last at most 120 seconds. An unenrolled supervisor owns the
loader/link, retains cleanup handles, and restores the pre-test state on
success, exception, signal, or timeout. Refuse to reset existing live maps or
take ownership of unrelated attachments. Confirm cleanup in kernel evidence.

Test that the selected executable runs, an unlisted copied executable is
denied, and denial counters/events identify that probe. Verify another
unenrolled cgroup remains executable. Failure of any check blocks promotion.

Host-wide activation requires an explicit coverage plan for existing and
new cgroups, interpreters, required services, attestation tools, and recovery
commands. A single scoped manifest is insufficient. Retain a known-good boot
entry and a tested recovery route. Install no service that globally enables
strict mode before coverage is validated. If future cgroup enrollment or
recovery cannot be guaranteed, report a host activation blocker.

## TPM and verifier requirements

Use a verifier-issued nonce and session, single-use replay protection, and
SHA-256 PCRs 0, 1, 7, 11. Collect raw quote/signature, AK material, software-state
binding, boot ID, manifest digest, and generation. Independently verify quote
signature, nonce, selection and PCR values; a capture-side `verified: true`
sidecar is not authoritative evidence.

Manufacturer-rooted identity requires a validated EK certificate chain and
proof of AK/EK binding for this Intel TPM. A vendor property string or a
self-signed attestation key cannot satisfy it. Missing trust material blocks
the hardware-rooted verdict with an actionable reason.

Bind the manifest, boot and generation into the quoted software-state binding.
Validate approved baseline and available boot-event evidence according to an
explicit verifier policy. No automatic baseline approval. The signed verifier
result must bind host, boot, manifest, generation, nonce/session, evidence
digest, issuer, issue time and expiry; lifetime is at most 300 seconds. Verify
with a separately configured public key, reject replay and mismatches, and
store results atomically. Loopback/local-only verification is labeled and
cannot satisfy the production off-box verifier requirement.

## Final report and persistence

Each check reports `pass`, `fail`, `unknown`, or `skipped`, with supporting
evidence and a reason. A skipped required check is a blocker. Preserve the
familiar fields `ok`, `software_os_grade`, `hardware_rooted_os_grade`, and
`boundary`, while documenting the replacement criteria.

`software_os_grade` requires host-wide live blocking attachment, verified
artifact/link/map identity, valid non-empty policy, trusted immutable measured
identities and current generation coverage, plus a live denial test and
telemetry. Scoped tests cannot satisfy it.

`hardware_rooted_os_grade` additionally requires enabled Secure Boot, enforced
lockdown, EFI runtime visibility, fresh independently verified quote, approved
boot appraisal, manufacturer-rooted TPM identity and fresh trusted off-box
signed verdict bound to the current state. Any missing requirement yields
false. `ok` is true only for the full hardware-rooted result. Report
confidentiality lockdown separately.

The post-boot workflow must repeat measurement validation and fresh attestation
before enabling enforcement. It must never reuse boot-bound inode maps,
expired verdicts, or stale cgroup IDs. Persist only approved configuration and
monotonic history, not a claim that a prior boot remains authoritative.

## Validation and completion evidence

Unit tests cover signature tampering, untrusted keys, mutable/substituted files,
replay and expiry, missing BPF links/maps, scoped-versus-host reporting,
verifier result mismatches, and absence of inspection side effects.

Orchestration tests cover timeout, signal/exception cleanup, existing-map
ownership, missing cgroup support, and failure before generation commitment.
No unit test may be presented as real hardware proof.

Operator hardware checks confirm scoped allow/deny/telemetry and recovery,
trusted TPM evidence on this Intel device, explicit host coverage, manual
host-grade appraisal, and fresh successful appraisal after service installation
and a separately authorized reboot. Save source/binary identities and all
results with the new evidence bundle. Until those pass, report incomplete
proof with concrete blockers.
