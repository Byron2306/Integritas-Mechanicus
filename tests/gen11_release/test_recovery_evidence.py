import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICES = (
    Path(__file__).resolve().parents[2]
    / "arda_os/backend/services"
)
sys.path.insert(0, str(SERVICES))

import arda_gen11_recovery_evidence as evidence


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryEvidenceTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "recovery.tar.gz"
        self.good = b"known-good-laboratory-grub\n"

        receipt = {
            "schema": "arda-preboot-lab-v1",
            "status": "PRIMARY_RESTORED",
            "primary_grub_sha256": sha(self.good),
            "recovery_boot": True,
            "laboratory_only": True,
        }

        self.files = {
            name: b"lab-fixture"
            for name in evidence.REQUIRED
        }
        self.files[
            "root/arda-recovery-lab/grub.gen10-known-good.cfg"
        ] = self.good
        self.files[
            "root/arda-recovery-lab/receipts/preboot-recovery.json"
        ] = json.dumps(receipt).encode()
        self.files[
            "root/arda-preboot-recovery/recovery.cfg"
        ] = b"linux /vmlinuz arda.recovery=1\n"
        self.files[
            "etc/systemd/system/arda-preboot-repair.service"
        ] = b"ConditionKernelCommandLine=arda.recovery=1\n"
        self.files[
            "usr/local/sbin/arda-preboot-repair"
        ] = (
            b"not_independent_recovery_boot\n"
            b"unknown_primary_grub_content\n"
        )

    def pack(self, *, link=None):
        with tarfile.open(self.bundle, "w:gz") as archive:
            for name, data in sorted(self.files.items()):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                if name == link:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "/etc/passwd"
                    info.size = 0
                archive.addfile(
                    info,
                    None if name == link else io.BytesIO(data),
                )

    def inspect(self):
        self.pack()
        with patch.object(
            evidence, "EXPECTED_BUNDLE",
            sha(self.bundle.read_bytes()),
        ), patch.object(
            evidence, "EXPECTED_GRUB", sha(self.good)
        ):
            return evidence.inspect(self.bundle)

    def test_valid_fixture(self):
        result = self.inspect()
        self.assertEqual(
            result["status"],
            "HISTORICAL_LAB_EVIDENCE_VALIDATED",
        )
        self.assertFalse(result["production_install_authorized"])

    def test_missing_member_refused(self):
        self.files.pop(
            "usr/local/sbin/arda-lab-auto-recover"
        )
        with self.assertRaises(evidence.EvidenceRefused):
            self.inspect()

    def test_forged_receipt_refused(self):
        path = (
            "root/arda-recovery-lab/receipts/"
            "preboot-recovery.json"
        )
        receipt = json.loads(self.files[path])
        receipt["status"] = "INSTALL_AUTHORIZED"
        self.files[path] = json.dumps(receipt).encode()
        with self.assertRaises(evidence.EvidenceRefused):
            self.inspect()

    def test_symlink_member_refused(self):
        self.pack(
            link="usr/local/sbin/arda-preboot-repair"
        )
        with patch.object(
            evidence, "EXPECTED_BUNDLE",
            sha(self.bundle.read_bytes()),
        ), patch.object(
            evidence, "EXPECTED_GRUB", sha(self.good)
        ):
            with self.assertRaises(evidence.EvidenceRefused):
                evidence.inspect(self.bundle)

    def test_oversized_member_refused(self):
        self.files[
            "root/arda-recovery-lab/grub.candidate.cfg"
        ] = b"x" * 2_000_001
        with self.assertRaises(evidence.EvidenceRefused):
            self.inspect()

    def test_modified_bundle_digest_refused(self):
        self.pack()
        with self.assertRaises(evidence.EvidenceRefused):
            evidence.inspect(self.bundle)


if __name__ == "__main__":
    unittest.main()
