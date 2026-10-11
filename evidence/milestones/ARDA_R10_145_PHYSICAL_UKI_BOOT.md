# ARDA Valinor R10.145: Physical UKI Boot

Date: 2026-10-11

## Result

PASS: Lenovo-orchestrated, one-time ARDA UKI boot.

The Acer successfully booted Linux 6.12.111-valinor through
firmware entry Boot0001, ARDA-R10-145-UKI.

## UKI artifact

SHA256:
ded2b740da194f23430154cfbb66657d98e17e40c72bba0e99bc1d5f0976a18b

Verified:
- PE signature validated using enrolled DKMS certificate.
- Embedded kernel byte-identical to pinned source.
- Embedded initrd byte-identical to pinned source.
- Embedded command line matched approved arguments.
- Original GRUB recovery files retained.

## Physical boot evidence

BootCurrent: 0001
Boot entry: ARDA-R10-145-UKI
Kernel: 6.12.111-valinor
Boot ID: 79ae50a8-9f50-4307-b00c-b1982c7fc8dc

Command line:
root=UUID=b217972c-511b-4443-8e1c-bb1c3649590b ro intel_iommu=on iommu=pt quiet

PCR0:
6eaad2b8ac522289f25d8654fc2e8cb7d37edd0c4a115f024393ccfec905bbda

PCR1:
ada403ceef7d97a8d812e73740babeee1515f0b0d0211047b9673b2e62eae952

PCR7:
869561b03ea4f0f9f04b9437ec8eb322368fa9a323c59a4dcB1520353a5e62ce

PCR8:
0000000000000000000000000000000000000000000000000000000000

PCR9:
247003f71c53abeda279a18ae637f107483eac0547229216aec2dc5cafa96034

PCR11:
8708090bc23d9e1700569e12187961e7ca92d52d237d172d7b1cd58d78fe6cd0

TPM event log SHA256:
2d60272b6ae6ac80dc9dd60c4c509264b9c0db3e768faae4cf1e2356091ae4a0

## Verification scope

PASS:
- Signed UKI construction and signature verification.
- Exact embedded kernel/initrd/cmdline inspection.
- Real firmware selection of dedicated ARDA UKI entry.
- Successful physical boot of Valinor.
- Nonzero PCR11 observed.

PENDING:
- Independent PCR11 event-log replay and fresh TPM quote.
- UKI-specific PCR1/PCR7 baseline appraisal.
- Complete authenticated execution-chain appraisal.
- Whole-host enforcement and persistence qualification.

hardware_rooted_os_grade: false
software_os_grade: false

## Safety

Existing GRUB recovery files preserved.
No Secure Boot key changes.
No TPM PCR extensions performed manually.
No host-global BPF enforcement activated.

The physical UKI boot is verified. Full OS-grade attestation
is not yet established.
