"""Gen11 protected boot transition: audited admission and cold recovery rehearsal.

NO production file mutation, trusted-key generation, GRUB selection, or reboot.
This module will not elevate ADMITTED_FOR_HUMAN_REVIEW to install authority.
"""
from __future__ import annotations
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

GEN10_GRUB = '3bd6231883dbb955901eb133067a1760bb58d23b3920ee185208027cebb5f441'
GEN11_GRUB = 'fb3c66c81df3dabcd9390597a124f2686e759549f70dff68fe41cf05f99ddc62'
GEN10_VERITY = 'c7dd6c826af174ab7ba3d819e49f8d40d1b8f7188cb46363054b35cfa6579337'
FALLBACK = "menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'"
TARGET = "menuentry 'ARDA Valinor Gen11 Experimental'"
MASKED = ('arda-ring0.service','arda-ring0-verify.service','arda-valinor-postboot.service',
          'arda-valinor-postboot.timer','arda-postboot-grade.service')

class Refuse(RuntimeError): pass

def need(predicate, reason):
    if not predicate: raise Refuse(reason)

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def safe_read(path):
    p=Path(path)
    need(p.is_absolute() and not p.is_symlink() and p.is_file(),'file_not_regular_absolute')
    return p

def check_candidate(path, *, old_hash=GEN10_GRUB,new_hash=GEN11_GRUB):
    p=safe_read(path)
    need(sha(p)==new_hash,'candidate_hash')
    cfg=p.read_text()
    need(TARGET in cfg and FALLBACK in cfg,'entries_missing')
    need(all('systemd.mask='+s in cfg for s in MASKED),'experimental_isolation')
    need(cfg.count(TARGET)==1,'duplicate_experimental_entry')
    try:
        chk=subprocess.run(['grub-script-check',str(p)],capture_output=True,text=True,timeout=20)
    except (FileNotFoundError,subprocess.TimeoutExpired) as exc: raise Refuse('grub_syntax_unavailable') from exc
    need(chk.returncode==0,'grub_syntax_invalid')
    return {'candidate_sha256':new_hash,'fallback_sha256':old_hash}

def audit_protected_state(*, baseline, candidate, fsverity_output, policy_transition, recovery_proof,
                          installer, expected, authority_decision):
    """Evaluate independent release evidence. Never derive expected values from a signature.

    Production authorization checker is upstream. Admission alone cannot empower writes.
    """
    before=safe_read(baseline); after=safe_read(candidate)
    need(sha(before)==GEN10_GRUB,'baseline_digest')
    check_candidate(after)
    need(type(fsverity_output) is str and ('sha256:'+GEN10_VERITY) in fsverity_output,'baseline_fsverity')
    need(type(authority_decision) is dict and authority_decision.get('status')=='ADMITTED_FOR_HUMAN_REVIEW','authority_not_admitted')
    need(authority_decision.get('installation_authorized') is False,'authority_claims_install')
    files={'measured_policy_transition_sha256':policy_transition,
           'recovery_evidence_sha256':recovery_proof,'installer_sha256':installer}
    need(type(expected) is dict and set(expected)==set(files),'expected_set')
    for key,p in files.items():
        need(sha(safe_read(p))==expected[key],'evidence_mismatch:'+key)
    proof=json.loads(Path(recovery_proof).read_text())
    need(type(proof) is dict and proof.get('schema')=='arda-gen11-cold-recovery-proof-v1','recovery_schema')
    need(proof.get('status')=='PASSED' and proof.get('fallback_sha256')==GEN10_GRUB,'recovery_incomplete')
    need(proof.get('environment')=='DISPOSABLE_BOOT_ENVIRONMENT','recovery_environment')
    need(proof.get('independent_verifier') is True,'independence_not_proven')
    return {'schema':'arda-gen11-protected-transition-review-v1','status':'REVIEW_REQUIRED',
            'baseline_grub_sha256':GEN10_GRUB,'candidate_grub_sha256':GEN11_GRUB,
            'baseline_fsverity':GEN10_VERITY,'evidence_sha256':dict(expected),
            'installation_authorized':False,'first_boot_authorized':False,
            'reason':'NO_APPROVED_PRODUCTION_ACTUATOR_OR_MEASURED_POLICY_SWITCH'}

def emit_receipt(path, result):
    """Create one immutable-in-practice user-space review receipt, never under /boot."""
    p=Path(path)
    need(p.is_absolute() and not p.exists() and not p.is_symlink(),'receipt_destination')
    need(not (p==Path('/boot') or p==Path('/etc') or str(p).startswith(('/boot/','/etc/','/sys/','/usr/'))),'production_path_forbidden')
    parent=p.parent
    need(parent.is_dir() and not parent.is_symlink() and parent.stat().st_uid==os.getuid(),'receipt_parent')
    need(not parent.stat().st_mode & (stat.S_IWGRP|stat.S_IWOTH),'receipt_parent_writable')
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        data=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
        os.write(fd,data);os.fsync(fd)
    finally:os.close(fd)
    dfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(dfd)
    finally:os.close(dfd)
    return p
