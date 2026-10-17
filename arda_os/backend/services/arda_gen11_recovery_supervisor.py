"""ARDA Gen11 crash-recovery supervisor, disposable-guest only.

This is an integration boundary, NOT a production /boot installer. The caller
must provide a laboratory test token. This token is NOT cryptographic
authority; production-signature integration is deliberately absent.
The boot watchdog can roll back uncommitted changes without a signing key.
"""
from __future__ import annotations
import hashlib, json, os, stat, sqlite3
from pathlib import Path

class Refuse(RuntimeError): pass

def need(x,why):
    if not x: raise Refuse(why)

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def fsync_dir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def exclusive(p,data):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
    except BaseException:
        raise

def record(p,data):
    tmp=p.with_name(p.name+'.pending')
    need(not tmp.exists(),'journal_pending_manual_review')
    exclusive(tmp,(json.dumps(data,sort_keys=True)+'\n').encode())
    os.replace(tmp,p);fsync_dir(p.parent)

def sandbox(root):
    p=Path(root)
    need(p.is_absolute() and p.is_dir() and not p.is_symlink(),'invalid_root')
    rp=p.resolve(strict=True)
    need(str(rp).startswith('/tmp/') or str(rp).startswith('/home/'),'disposable_path_only')
    for parent in (rp, *rp.parents):
        need(not parent.is_symlink(),'symlink_parent')
    mode=rp.stat()
    need(mode.st_uid==os.getuid() and not mode.st_mode & 0o022,'sandbox_permission')
    return rp

class Supervisor:
    def __init__(self, root):
        self.root=sandbox(root)
        self.active=self.root/'grub.cfg'
        self.candidate=self.root/'candidate.cfg'
        self.backup=self.root/'gen10.backup'
        self.journal=self.root/'transaction.json'
        self.receipt=self.root/'recovery-receipt.json'
        self.db=self.root/'authority-ledger.sqlite'
        self.conn=sqlite3.connect(self.db,isolation_level=None)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.execute('CREATE TABLE IF NOT EXISTS ids(id TEXT PRIMARY KEY, state TEXT NOT NULL)')

    def _state(self):
        need(self.journal.exists() and not self.journal.is_symlink(),'journal_missing')
        j=json.loads(self.journal.read_text())
        need(j.get('schema')=='arda-gen11-recovery-supervisor-v1','journal_schema')
        return j

    def begin(self, *, verified_decision, candidate, old_digest, new_digest):
        """Laboratory-only state machine: the decision object is NOT trusted.

        Production verifier returns ADMITTED_FOR_HUMAN_REVIEW and is rejected.
        Never wire this method to real /boot writes or accept a caller-supplied
        dictionary as proof of signature verification.
        """
        need(isinstance(verified_decision,dict),'decision_required')
        need(verified_decision.get('status')=='DISPOSABLE_GUEST_INSTALL_APPROVED', 'installer_scope_not_approved')
        need(verified_decision.get('destination')==str(self.active),'destination_not_bound')
        auth_id=verified_decision.get('authorization_id')
        need(isinstance(auth_id,str) and len(auth_id)>=16,'authorization_id')
        need(verified_decision.get('candidate_sha256')==new_digest and verified_decision.get('baseline_sha256')==old_digest,'signed_binding')
        for p in (self.active,self.candidate,self.backup,self.journal,self.receipt):
            need(not p.is_symlink(),'symlink')
        need(not any(p.exists() for p in (self.candidate,self.backup,self.journal,self.receipt)),'unfinished_transaction')
        need(self.active.is_file() and digest(self.active)==old_digest,'baseline_changed')
        need(digest(candidate)==new_digest,'candidate_changed')
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            self.conn.execute('INSERT INTO ids VALUES (?,?)',(auth_id,'reserved'))
            self.conn.execute('COMMIT')
        except BaseException:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise
        exclusive(self.backup,self.active.read_bytes())
        exclusive(self.candidate,Path(candidate).read_bytes())
        fsync_dir(self.root)
        record(self.journal,{'schema':'arda-gen11-recovery-supervisor-v1','state':'STAGED','id':auth_id,'old':old_digest,'new':new_digest})
        return 'STAGED'

    def install(self, *, failpoint=None):
        j=self._state()
        need(j['state']=='STAGED','invalid_state')
        need(digest(self.active)==j['old'] and digest(self.backup)==j['old'] and digest(self.candidate)==j['new'],'integrity')
        j['state']='INSTALLING';record(self.journal,j)
        if failpoint=='after_intent':raise RuntimeError('SIMULATED_CRASH_AFTER_INTENT')
        os.replace(self.candidate,self.active);fsync_dir(self.root)
        if failpoint=='after_replace':raise RuntimeError('SIMULATED_CRASH_AFTER_REPLACE')
        need(digest(self.active)==j['new'],'installed_digest')
        # This signals file installation completed, NOT that first boot succeeded.
        j['state']='AWAITING_BOOT_PROOF';record(self.journal,j)
        return 'AWAITING_BOOT_PROOF'

    def watchdog_recover(self):
        """Restart-safe watchdog. Unknown modifications cause REFUSE, not overwrite."""
        j=self._state()
        need(j['state'] in ('STAGED','INSTALLING','AWAITING_BOOT_PROOF'),'not_recoverable')
        need(self.backup.is_file() and not self.backup.is_symlink() and digest(self.backup)==j['old'],'backup_corrupt')
        need(self.active.is_file() and not self.active.is_symlink(),'active_not_regular')
        current=digest(self.active)
        need(current in (j['old'],j['new']),'unknown_active_content')
        if current==j['new']:
            restore=self.root/'restore.tmp'
            need(not restore.exists(),'restore_incomplete_manual_review')
            exclusive(restore,self.backup.read_bytes())
            os.replace(restore,self.active);fsync_dir(self.root)
        need(digest(self.active)==j['old'],'rollback_failed')
        j['state']='ROLLED_BACK';record(self.journal,j)
        record(self.receipt,{'schema':'arda-gen11-recovery-proof-v1','status':'ROLLED_BACK','id':j['id'],'restored_sha256':j['old'],'power_loss_proven':False,'boot_proven':False})
        self.conn.execute('UPDATE ids SET state=? WHERE id=?',('rolled_back',j['id']))
        return 'ROLLED_BACK'

    def status(self):
        return self._state()['state']
