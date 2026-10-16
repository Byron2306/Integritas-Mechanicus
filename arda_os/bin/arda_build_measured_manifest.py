#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ARDA_OS_ROOT = Path(__file__).resolve().parents[1]
if str(ARDA_OS_ROOT) not in sys.path:
    sys.path.insert(0, str(ARDA_OS_ROOT))

from backend.services.measured_identity import (
    MeasuredIdentityVerifier,
    MeasuredProjectionGenerationStore,
)
from backend.services.measured_policy_profiles import expand_measurement_profile
from backend.services.proof_file_measurement import open_measured


SCHEMA = "arda.measured_manifest.v1"
AUDIENCE = "arda-measured-preflight"

IDENTITY_DIR = Path("/var/lib/arda/identity")
PRIVATE_KEY = IDENTITY_DIR / "measured-manifest-key.pem"
PUBLIC_KEY = IDENTITY_DIR / "measured-manifest-key.pub.pem"
ACTIVE_ALIAS = Path("/var/lib/arda/projection/measured-critical.json")


def run(*argv: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        list(argv),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(argv)} failed: "
            + result.stderr.decode(errors="replace").strip()
        )
    return result.stdout


def ensure_local_manifest_identity() -> tuple[Path, Path, str]:
    if os.geteuid() != 0:
        raise RuntimeError("root required")

    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(IDENTITY_DIR, 0o700)

    if PRIVATE_KEY.exists() != PUBLIC_KEY.exists():
        raise RuntimeError("partial measured-manifest identity exists")

    if not PRIVATE_KEY.exists():
        old_umask = os.umask(0o077)
        try:
            run(
                "/usr/bin/openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(PRIVATE_KEY),
            )
            run(
                "/usr/bin/openssl",
                "pkey",
                "-in",
                str(PRIVATE_KEY),
                "-pubout",
                "-out",
                str(PUBLIC_KEY),
            )
        finally:
            os.umask(old_umask)

    if PRIVATE_KEY.is_symlink() or PUBLIC_KEY.is_symlink():
        raise RuntimeError("manifest identity keys must not be symlinks")

    mode = PRIVATE_KEY.stat().st_mode & 0o777
    if mode & 0o077:
        raise RuntimeError(
            f"manifest private key permissions too broad: {oct(mode)}"
        )

    if PRIVATE_KEY.stat().st_uid != 0:
        raise RuntimeError("manifest private key must be root-owned")

    public_der = run(
        "/usr/bin/openssl",
        "pkey",
        "-pubin",
        "-in",
        str(PUBLIC_KEY),
        "-outform",
        "DER",
    )
    key_id = "arda-measured-local-" + hashlib.sha256(public_der).hexdigest()[:16]

    return PRIVATE_KEY, PUBLIC_KEY, key_id


def current_cgroup() -> tuple[str, int]:
    lines = Path("/proc/self/cgroup").read_text().splitlines()

    unified = None
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[0] == "0":
            unified = parts[2]
            break

    if unified is None:
        raise RuntimeError("cgroup v2 membership unavailable")

    relative = unified if unified.startswith("/") else "/" + unified
    full = Path("/sys/fs/cgroup") / relative.lstrip("/")

    if not full.is_dir():
        raise RuntimeError(f"live cgroup unavailable: {full}")

    return relative, full.stat().st_ino


def sha256_fd(fd: int) -> str:
    digest = hashlib.sha256()
    offset = 0

    while True:
        chunk = os.pread(fd, 1024 * 1024, offset)
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)

    return "sha256:" + digest.hexdigest()


def measure_path(path: str) -> dict:
    try:
        measured = open_measured(path)
    except OSError:
        run("/usr/bin/fsverity", "enable", path)
        measured = open_measured(path)

    try:
        measured.revalidate()

        return {
            "path": path,
            "fs_verity_algorithm_id": measured.algorithm,
            "fs_verity_digest": measured.digest.lower(),
            "workload_digest": sha256_fd(measured.fd),
        }
    finally:
        measured.close()


def canonical_manifest_payload(manifest: dict) -> bytes:
    unsigned = dict(manifest)
    unsigned.pop("signature", None)

    return json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sign_manifest(private_key: Path, payload: bytes) -> str:
    # Ed25519 is a one-shot signature algorithm. OpenSSL pkeyutl needs
    # a seekable input so it can determine the complete message size.
    with tempfile.NamedTemporaryFile() as payload_file:
        payload_file.write(payload)
        payload_file.flush()

        signature = run(
            "/usr/bin/openssl",
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(private_key),
            "-in",
            payload_file.name,
        )

    return base64.b64encode(signature).decode("ascii")


def verify_signature(
    public_key: Path,
    payload: bytes,
    signature_b64: str,
) -> None:
    signature = base64.b64decode(signature_b64, validate=True)

    with tempfile.NamedTemporaryFile() as payload_file, \
         tempfile.NamedTemporaryFile() as sig_file:
        payload_file.write(payload)
        payload_file.flush()

        sig_file.write(signature)
        sig_file.flush()

        run(
            "/usr/bin/openssl",
            "pkeyutl",
            "-verify",
            "-rawin",
            "-pubin",
            "-inkey",
            str(public_key),
            "-sigfile",
            sig_file.name,
            "-in",
            payload_file.name,
        )

def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="critical-host")
    parser.add_argument("--policy-generation", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.generation <= 0:
        raise RuntimeError("generation must be positive")

    repo_root = Path(__file__).resolve().parents[2]

    paths = expand_measurement_profile(
        args.profile,
        repo_root=str(repo_root),
    )
    if not paths:
        raise RuntimeError("measurement profile resolved to zero files")

    private_key, public_key, key_id = ensure_local_manifest_identity()

    entries = []
    identities: dict[tuple[int, str], str] = {}

    for path in paths:
        entry = measure_path(path)
        identity = (
            entry["fs_verity_algorithm_id"],
            entry["fs_verity_digest"],
        )

        if identity in identities:
            raise RuntimeError(
                "duplicate fs-verity identity: "
                f"{identities[identity]} and {path}"
            )

        identities[identity] = path
        entries.append(entry)

    cgroup_name, cgroup_kernel_id = current_cgroup()

    now = datetime.now(timezone.utc)

    manifest = {
        "schema_version": SCHEMA,
        "manifest_id": "measured-" + uuid.uuid4().hex,
        "generation": args.generation,
        "node_id": socket.gethostname(),
        "policy_generation": args.policy_generation,
        "audience": AUDIENCE,
        "attestation_result_id": None,
        "attestation_evidence_digest": None,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "entries": entries,
        "cgroup_id": cgroup_name,
        "cgroup_kernel_id": cgroup_kernel_id,
        "pid_namespace_inode": Path("/proc/self/ns/pid").stat().st_ino,
        "mount_namespace_inode": Path("/proc/self/ns/mnt").stat().st_ino,
        "signature": {
            "algorithm": "ed25519",
            "keyid": key_id,
        },
    }

    payload = canonical_manifest_payload(manifest)
    manifest["signature"]["signature"] = sign_manifest(private_key, payload)

    verify_signature(
        public_key,
        payload,
        manifest["signature"]["signature"],
    )

    # Validate against the exact userspace contract without touching
    # the real generation database.
    with tempfile.TemporaryDirectory(prefix="arda-manifest-preflight-") as td:
        store = MeasuredProjectionGenerationStore(
            str(Path(td) / "generation.sqlite3")
        )
        try:
            verifier = MeasuredIdentityVerifier(store)
            result = verifier.preflight(
                manifest,
                attestation=None,
                commit_generation=False,
            )
        finally:
            store.close()

    if not result.get("ok"):
        raise RuntimeError(
            "measured manifest preflight failed: "
            + ",".join(result.get("failures") or [])
        )

    output = Path(args.output)
    atomic_json(output, manifest)
    atomic_json(ACTIVE_ALIAS, manifest)

    print(json.dumps({
        "ok": True,
        "manifest_id": manifest["manifest_id"],
        "generation": manifest["generation"],
        "node_id": manifest["node_id"],
        "policy_generation": manifest["policy_generation"],
        "entry_count": len(entries),
        "cgroup_id": cgroup_name,
        "cgroup_kernel_id": cgroup_kernel_id,
        "manifest_signing_key_id": key_id,
        "output": str(output),
        "active_alias": str(ACTIVE_ALIAS),
    }, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
