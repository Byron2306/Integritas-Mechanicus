import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import arda_gen11_boot_transition as t

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.old=self.root/'old.cfg';self.old.write_bytes(b'old')
        self.new=self.root/'new.cfg'
        self.new.write_text(t.TARGET+'\n'+t.FALLBACK+'\n'+'\n'.join('systemd.mask='+x for x in t.MASKED))
        self.policy=self.root/'policy';self.policy.write_text('reviewed transition')
        self.installer=self.root/'installer';self.installer.write_text('audited executable')
        self.recovery=self.root/'recovery.json'
        self.proof={'schema':'arda-gen11-cold-recovery-proof-v1','status':'PASSED','fallback_sha256':'OLD','environment':'DISPOSABLE_BOOT_ENVIRONMENT','independent_verifier':True}
        self.recovery.write_text(json.dumps(self.proof))
        self.authority={'status':'ADMITTED_FOR_HUMAN_REVIEW','installation_authorized':False}
        self.expected={}
    def invoke(self):
        self.expected={'measured_policy_transition_sha256':t.sha(self.policy),
                       'recovery_evidence_sha256':t.sha(self.recovery),'installer_sha256':t.sha(self.installer)}
        with patch.object(t,'GEN10_GRUB',t.sha(self.old)),patch.object(t,'GEN11_GRUB',t.sha(self.new)),patch.object(t,'GEN10_VERITY','a'*64),patch.object(t,'check_candidate',return_value={}),patch.object(t,'sha',wraps=t.sha):
            # call excludes actual GRUB probe only in these fixture tests
            proof=json.loads(self.recovery.read_text());proof['fallback_sha256']=t.sha(self.old);self.recovery.write_text(json.dumps(proof))
            self.expected['recovery_evidence_sha256']=t.sha(self.recovery)
            return t.audit_protected_state(baseline=self.old,candidate=self.new,
                       fsverity_output='sha256:'+'a'*64,policy_transition=self.policy,
                       recovery_proof=self.recovery,installer=self.installer,expected=self.expected,
                       authority_decision=self.authority)
    def test_review_only(self):
        r=self.invoke();self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertFalse(r['installation_authorized'])
    def test_refuse_bad_authority(self):
        self.authority={'status':'APPROVED','installation_authorized':True}
        with self.assertRaises(t.Refuse): self.invoke()
    def test_refuse_incomplete_recovery(self):
        self.proof['status']='PENDING';self.recovery.write_text(json.dumps(self.proof))
        with self.assertRaises(t.Refuse): self.invoke()
    def test_refuse_nonindependent_recovery(self):
        self.proof['independent_verifier']=False;self.recovery.write_text(json.dumps(self.proof))
        with self.assertRaises(t.Refuse): self.invoke()
    def test_refuse_non_disposable_recovery(self):
        self.proof['environment']='LENOVO_PRODUCTION';self.recovery.write_text(json.dumps(self.proof))
        with self.assertRaises(t.Refuse): self.invoke()
    def test_refuse_tampered_baseline(self):
        with patch.object(t,'GEN10_GRUB','1'*64):
            with self.assertRaises(t.Refuse): t.audit_protected_state(baseline=self.old,candidate=self.new,fsverity_output='sha256:a',policy_transition=self.policy,recovery_proof=self.recovery,installer=self.installer,expected={},authority_decision=self.authority)
    def test_candidate_symlink_refused(self):
        link=self.root/'link';link.symlink_to(self.new)
        with self.assertRaises(t.Refuse): t.check_candidate(link)
    def test_receipt_protected_destination_refused(self):
        with self.assertRaises(t.Refuse):t.emit_receipt('/boot/grub/testreceipt',{})
    def test_receipt_exclusive_and_durable(self):
        dest=self.root/'receipt.json'
        t.emit_receipt(dest,{'installation_authorized':False})
        self.assertEqual(json.loads(dest.read_text())['installation_authorized'],False)
        with self.assertRaises(t.Refuse):t.emit_receipt(dest,{})

if __name__=='__main__':unittest.main()
