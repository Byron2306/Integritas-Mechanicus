# Valinor Kernel And QEMU ISO Artifact Manifest

Generated: 2026-08-02

This manifest records the latest local ARDA Valinor kernel and QEMU/live ISO build artifacts that were prepared for repository preservation. The binary upload to GitHub LFS was attempted, but GitHub rejected it because the repository/account LFS budget is exceeded. Until LFS or a GitHub Release upload is restored, these checksums preserve exact artifact identity and local paths.

## Local Artifact Index

| SHA-256 | Size bytes | Local repository path |
| --- | ---: | --- |
| `97ba8b52e1480691d97021c1c30b698dc2f1997a913dfee47c91fe18fdfde381` | 1,424,875,520 | `arda_os/distribution/build/artifact-workspace/release/arda-valinor-live-trixie-amd64.iso` |
| `97ba8b52e1480691d97021c1c30b698dc2f1997a913dfee47c91fe18fdfde381` | 1,424,875,520 | `arda_os/distribution/releases/artifacts/saved/arda-valinor-live-trixie-amd64-20260802-143029.iso` |
| `03345564a33cc65f6fe7cc4d88411402448a91cf9c32e28cbe73e3e2a46725a4` | 9,898,064 | `arda_os/distribution/build/workspace/artifacts/linux-headers-6.12.96-valinor_6.12.96-valinor2-1_amd64.deb` |
| `aa32206145c2adcffd75a9c99fef759666c9b0dfb08e07228785bffe64f0fb6a` | 109,456,532 | `arda_os/distribution/build/workspace/artifacts/linux-image-6.12.96-valinor_6.12.96-valinor2-1_amd64.deb` |
| `02f8b7811daf8f6c7930092795fa63c6d81f91d858894c3daa678f9902f426b7` | 1,395,944 | `arda_os/distribution/build/workspace/artifacts/linux-libc-dev_6.12.96-valinor2-1_amd64.deb` |
| `e1c9cd2c1694b28761d486a3662ec8e32803871bd7bd8de11d382824c382c7ec` | 148,984,856 | `arda_os/kernel/valinor/releases/frozen/2026-07-29-valinor3/initrd.img-6.12.96-valinor` |
| `38aa71b00fe1298cfa41cb636c1b2c32079b7ae495f130ed28708073c1b8863b` | 9,897,812 | `arda_os/kernel/valinor/releases/frozen/2026-07-29-valinor3/linux-headers-6.12.96-valinor_6.12.96-valinor3-1_amd64.deb` |
| `94b81d1ba448e342fce3bae601b827a86dcecd028f7b487dddc54a2dd48ad7e6` | 109,455,824 | `arda_os/kernel/valinor/releases/frozen/2026-07-29-valinor3/linux-image-6.12.96-valinor_6.12.96-valinor3-1_amd64.deb` |
| `875117b4148753e407725a3d3d838d8f40db95111c88eabd329f9d229414a527` | 12,060,744 | `arda_os/kernel/valinor/releases/frozen/2026-07-29-valinor3/vmlinuz-6.12.96-valinor` |

## Upload Status

The first push attempt included these artifacts through Git LFS and failed with:

```text
batch response: This repository exceeded its LFS budget. The account responsible for the budget should increase it to restore access.
error: failed to push some refs to 'github.com:Byron2306/Integritas-Mechanicus.git'
```

Recommended follow-up once storage is available:

1. Restore GitHub LFS budget for `Byron2306/Integritas-Mechanicus`, then commit these binary artifacts through LFS.
2. Or upload the ISO/kernel packages to a GitHub Release and retain this manifest as the repository-side provenance index.
