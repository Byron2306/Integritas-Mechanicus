"""Gen11 transactional GRUB replacement engine, SANDBOX ONLY.

This module demonstrates power-loss recovery sequencing on ordinary files.
It refuses all /boot and /etc targets, and is NOT a production installer.
No implicit use of attestation keys as release authorities.
"""
from __future__ import annotations
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

class Refuse(RuntimeError):
    pass

def _digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def _sync_dir(path):
    fd=os.open(path,os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def _write_new(path, data):
    with Path(path).open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())

def _atomic_json(path, obj):
    path=Path(path)
    temp=path.with_name(path.name+'.new')
    if temp.exists(): raise Refuse('journal_temp_already_exists')
    _write_new(temp, (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode())
    os.replace(temp,path);_sync_dir(path.parent)

def _safe_directory(path):
    p=Path(path)
    if not p.is_absolute() or p.is_symlink() or not p.exists() or not p.is_dir(): raise Refuse('sandbox_directory_invalid')
    real=p.resolve(strict=True)
    # Even root executing the code cannot target critical paths.
    if str(real).startswith(('/boot/','/etc/','/usr/','/var/lib/arda/','/sys/','/run/')) or real in map(Path, ('/','/boot','/etc','/usr','/var')):
        raise Refuse('production_target_forbidden')
    if p.stat().st_uid != os.getuid() or p.stat().st_mode & (stat.S_IWGRP|stat.S_IWOTH):
        raise Refuse('sandbox_owner_or_permissions')
    return real

class SandboxInstall:
    """Crash-state proof, no privileged bootloader modifications."""
    def __init__(self, root):
        self.root=_safe_directory(root)
        self.current=self.root/'grub.cfg'
        self.staged=self.root/'grub.candidate'
        self.backup=self.root/'grub.gen10.backup'
        self.journal=self.root/'install-receipt.json'
        self.rollback_receipt=self.root/'rollback-receipt.json'

    def stage(self, *, candidate, expected_old, expected_new, approval_verified=False):
        if approval_verified is not True: raise Refuse('authorization_not_verified')
        if self.journal.exists() or self.backup.exists() or self.staged.exists(): raise Refuse('existing_transaction')
        if any(p.is_symlink() for p in (self.current,self.backup,self.staged,self.journal)): raise Refuse('symlink_forbidden')
        if not self.current.is_file() or _digest(self.current)!=expected_old: raise Refuse('baseline_mismatch')
        if _digest(candidate)!=expected_new: raise Refuse('candidate_mismatch')
        original=self.current.read_bytes()
        proposed=Path(candidate).read_bytes()
        _write_new(self.backup,original)
        _write_new(self.staged,proposed)
        _sync_dir(self.root)
        self._record({'state':'STAGED','baseline_sha256':expected_old,'candidate_sha256':expected_new})
        return 'STAGED'

    def _record(self,record):
        _atomic_json(self.journal,record)

    def _load(self):
        if not self.journal.exists(): raise Refuse('no_transaction')
        return json.loads(self.journal.read_text())

    def commit(self, *, failpoint=None):
        j=self._load()
        if j['state']!='STAGED': raise Refuse('invalid_transaction_state')
        if _digest(self.current)!=j['baseline_sha256'] or _digest(self.backup)!=j['baseline_sha256'] or _digest(self.staged)!=j['candidate_sha256']:
            raise Refuse('precommit_integrity_mismatch')
        j['state']='INSTALLING';self._record(j)
        if failpoint=='after_intent': raise RuntimeError('SIMULATED_POWER_LOSS_AFTER_INTENT')
        os.replace(self.staged,self.current)
        _sync_dir(self.root)
        if failpoint=='after_replace': raise RuntimeError('SIMULATED_POWER_LOSS_AFTER_REPLACE')
        if _digest(self.current)!=j['candidate_sha256']: raise Refuse('postinstall_digest_mismatch')
        j['state']='COMMITTED';self._record(j)
        return 'COMMITTED'

    def recover(self):
        j=self._load()
        if j['state']=='COMMITTED': raise Refuse('committed_requires_separate_release_rollback')
        if j['state'] not in ('STAGED','INSTALLING'): raise Refuse('invalid_recovery_state')
        if not self.backup.exists() or _digest(self.backup)!=j['baseline_sha256']:
            raise Refuse('backup_invalid_manual_recovery_required')
        # Preserve the receipt and fail closed on malformed destination.
        if self.current.is_symlink(): raise Refuse('current_symlink_forbidden')
        if self.current.exists() and _digest(self.current) not in (j['baseline_sha256'], j['candidate_sha256']):
            raise Refuse('unknown_current_content_manual_recovery_required')
        if self.current.exists() and _digest(self.current)==j['candidate_sha256']:
            restore=self.root/'grub.restore.tmp'
            if restore.exists(): raise Refuse('restore_temp_exists')
            _write_new(restore,self.backup.read_bytes())
            os.replace(restore,self.current);_sync_dir(self.root)
        if _digest(self.current)!=j['baseline_sha256']: raise Refuse('rollback_readback_mismatch')
        j['state']='ROLLED_BACK';self._record(j)
        _atomic_json(self.rollback_receipt,{'status':'ROLLED_BACK','restored_sha256':j['baseline_sha256']})
        return 'ROLLED_BACK'
