import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from arda_gen11_protected_promotion import inspect, Refuse

OLD=b'gen10 baseline\n'
NEW=("menuentry 'ARDA Valinor Gen11 Experimental'\n"+
     "menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'\n"+
     '\n'.join('systemd.mask='+x for x in ('arda-ring0.service','arda-ring0-verify.service','arda-valinor-postboot.service','arda-valinor-postboot.timer','arda-postboot-grade.service'))).encode()
import hashlib
def sha(b):return hashlib.sha256(b).hexdigest()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.old=root/'grub.cfg';self.old.write_bytes(OLD)
        self.new=root/'candidate';self.new.write_bytes(NEW)
        self.dossier=root/'dossier.json';self.d={
         'schema':'arda-gen11-boot-release-candidate-v1','status':'CANDIDATE_ONLY',
         'active_generation':10,'target_generation':11,'boot_profile':'EXPERIMENTAL_RING0_MASKED',
         'release_authorized':False,'first_boot_authorized':False,
         'artifacts':{'gen10_grub':{'path':'/boot/grub/grub.cfg','sha256':sha(OLD)},
                      'grub_candidate':{'sha256':sha(NEW)}}}
        self.dossier.write_text(json.dumps(self.d));self.v='a'*64
        self.kw=dict(dossier=self.dossier,staged=self.new,expected_baseline=sha(OLD),
                     fsverity_digest=self.v,measured_verity=self.v,parsed_grub_ok=True)
        self.patcher=patch('arda_gen11_protected_promotion.guard_target',return_value=self.old)
        self.patcher.start()
    def tearDown(self):self.patcher.stop();self.tmp.cleanup()
    def run_inspect(self,**kwargs):return inspect(**(self.kw|kwargs))
    def test_valid_evidence_still_refuses(self):
        x=self.run_inspect(trusted_recovery_proven=True,boot_authority_provisioned=True)
        self.assertFalse(x['production_install_authorized']);self.assertEqual(x['verdict'],'REFUSE_PRODUCTION_INSTALL')
    def test_missing_authority(self):self.assertIn('separate_boot_authority_not_provisioned',self.run_inspect()['missing_release_gates'])
    def test_tampered_candidate(self):
        self.new.write_bytes(b'evil')
        with self.assertRaises(Refuse):self.run_inspect()
    def test_changed_baseline(self):
        self.old.write_bytes(b'changed')
        with self.assertRaises(Refuse):self.run_inspect()
    def test_missing_verity(self):
        with self.assertRaises(Refuse):self.run_inspect(fsverity_digest=None)
    def test_different_verity(self):
        with self.assertRaises(Refuse):self.run_inspect(measured_verity='b'*64)
    def test_wrong_generation(self):
        self.d['target_generation']=12;self.dossier.write_text(json.dumps(self.d))
        with self.assertRaises(Refuse):self.run_inspect()
    def test_claims_boot_permission(self):
        self.d['first_boot_authorized']=True;self.dossier.write_text(json.dumps(self.d))
        with self.assertRaises(Refuse):self.run_inspect()
    def test_missing_fallback(self):
        self.new.write_bytes(NEW.replace(b'Debian GNU/Linux',b'OTHER'))
        self.d['artifacts']['grub_candidate']['sha256']=sha(self.new.read_bytes());self.dossier.write_text(json.dumps(self.d))
        with self.assertRaises(Refuse):self.run_inspect()
    def test_syntax_not_proven(self):
        with self.assertRaises(Refuse):self.run_inspect(parsed_grub_ok=False)
    def test_incorrect_pinned_old(self):
        with self.assertRaises(Refuse):self.run_inspect(expected_baseline='0'*64)

if __name__=='__main__':unittest.main()
