import hashlib
import tempfile
import unittest
from pathlib import Path
from arda_gen11_install_actuator import SandboxInstall,Refuse

def h(b): return hashlib.sha256(b).hexdigest()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'private'
        self.root.mkdir(mode=0o700)
        self.old=b'gen10 safe grub entry';self.new=b'gen11 experimental and gen10 fallback'
        (self.root/'grub.cfg').write_bytes(self.old)
        self.candidate=Path(self.tmp.name)/'candidate'
        self.candidate.write_bytes(self.new)
        self.s=SandboxInstall(self.root)
    def tearDown(self): self.tmp.cleanup()
    def stage(self, **kwargs):
        return self.s.stage(candidate=self.candidate,expected_old=h(self.old),expected_new=h(self.new),approval_verified=True,**kwargs)
    def test_no_authorization(self):
        with self.assertRaisesRegex(Refuse,'authorization_not_verified'):
            self.s.stage(candidate=self.candidate,expected_old=h(self.old),expected_new=h(self.new))
    def test_stages_without_installing(self):
        self.stage();self.assertEqual((self.root/'grub.cfg').read_bytes(),self.old)
    def test_commit(self):
        self.stage();self.assertEqual(self.s.commit(),'COMMITTED');self.assertEqual((self.root/'grub.cfg').read_bytes(),self.new)
    def test_replay_refused(self):
        self.stage();self.s.commit()
        with self.assertRaises(Refuse): self.s.commit()
    def test_duplicate_stage_refused(self):
        self.stage()
        with self.assertRaises(Refuse): self.stage()
    def test_tampered_candidate_refused(self):
        self.candidate.write_bytes(b'bad')
        with self.assertRaises(Refuse): self.stage()
    def test_changed_baseline_refused(self):
        (self.root/'grub.cfg').write_bytes(b'bad')
        with self.assertRaises(Refuse): self.stage()
    def test_crash_before_replace(self):
        self.stage()
        with self.assertRaises(RuntimeError): self.s.commit(failpoint='after_intent')
        self.assertEqual(SandboxInstall(self.root).recover(),'ROLLED_BACK')
        self.assertEqual((self.root/'grub.cfg').read_bytes(),self.old)
    def test_crash_after_replace(self):
        self.stage()
        with self.assertRaises(RuntimeError): self.s.commit(failpoint='after_replace')
        self.assertEqual(SandboxInstall(self.root).recover(),'ROLLED_BACK')
        self.assertEqual((self.root/'grub.cfg').read_bytes(),self.old)
    def test_tampered_backup_refuses_recovery(self):
        self.stage();(self.root/'grub.gen10.backup').write_bytes(b'bad')
        with self.assertRaisesRegex(Refuse,'backup_invalid') : self.s.recover()
    def test_changed_current_refuses_recovery(self):
        self.stage();(self.root/'grub.cfg').write_bytes(b'unknown')
        with self.assertRaisesRegex(Refuse,'unknown_current'): self.s.recover()
    def test_symlink_target_refused(self):
        (self.root/'grub.cfg').unlink();(self.root/'grub.cfg').symlink_to(self.candidate)
        with self.assertRaises(Refuse): self.stage()
    def test_world_writable_sandbox_refused(self):
        self.root.chmod(0o777)
        with self.assertRaises(Refuse): SandboxInstall(self.root)
    def test_production_directory_refused(self):
        with self.assertRaises(Refuse): SandboxInstall(Path('/etc'))
if __name__=='__main__':unittest.main()
