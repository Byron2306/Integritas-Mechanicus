import hashlib, tempfile, unittest
from pathlib import Path
from arda_gen11_recovery_supervisor import Supervisor,Refuse,digest
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(dir='/tmp'); self.root=Path(self.t.name);self.root.chmod(0o700)
  self.current=self.root/'grub.cfg';self.current.write_bytes(b'known-good GRUB')
  self.source=self.root/'new.cfg';self.source.write_bytes(b'Gen11 candidate')
  self.old=digest(self.current);self.new=digest(self.source)
  self.decision={'status':'DISPOSABLE_GUEST_INSTALL_APPROVED','destination':str(self.current),'authorization_id':'lab-authorization-0001','baseline_sha256':self.old,'candidate_sha256':self.new}
  self.s=Supervisor(self.root)
 def tearDown(self): self.s.conn.close();self.t.cleanup()
 def begin(self):return self.s.begin(verified_decision=self.decision,candidate=self.source,old_digest=self.old,new_digest=self.new)
 def test_stage(self):self.assertEqual(self.begin(),'STAGED');self.assertEqual(digest(self.current),self.old)
 def test_missing_authority(self):
  self.decision['status']='ADMITTED_FOR_HUMAN_REVIEW'
  with self.assertRaises(Refuse):self.begin()
 def test_wrong_destination(self):
  self.decision['destination']='/boot/grub/grub.cfg'
  with self.assertRaises(Refuse):self.begin()
 def test_wrong_binding(self):
  self.decision['candidate_sha256']='0'*64
  with self.assertRaises(Refuse):self.begin()
 def test_replay(self):
  self.begin()
  with self.assertRaises(Refuse):self.begin()
 def test_crash_before_replace(self):
  self.begin()
  with self.assertRaises(RuntimeError):self.s.install(failpoint='after_intent')
  self.assertEqual(Supervisor(self.root).watchdog_recover(),'ROLLED_BACK');self.assertEqual(digest(self.current),self.old)
 def test_crash_after_replace(self):
  self.begin()
  with self.assertRaises(RuntimeError):self.s.install(failpoint='after_replace')
  self.assertEqual(Supervisor(self.root).watchdog_recover(),'ROLLED_BACK');self.assertEqual(digest(self.current),self.old)
 def test_boot_proof_pending(self):
  self.begin();self.assertEqual(self.s.install(),'AWAITING_BOOT_PROOF')
  self.assertEqual(self.s.watchdog_recover(),'ROLLED_BACK')
 def test_tampered_backup(self):
  self.begin();self.s.backup.write_bytes(b'evil')
  with self.assertRaises(Refuse):self.s.watchdog_recover()
 def test_unknown_active(self):
  self.begin();self.current.write_bytes(b'unknown')
  with self.assertRaises(Refuse):self.s.watchdog_recover()
 def test_no_production_root(self):
  with self.assertRaises(Refuse):Supervisor(Path('/boot'))
 def test_receipt(self):
  self.begin();self.s.watchdog_recover()
  self.assertIn('"power_loss_proven": false',self.s.receipt.read_text())
if __name__=='__main__':unittest.main()
