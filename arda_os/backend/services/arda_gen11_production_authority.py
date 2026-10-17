"""ARDA Gen11 production release AUTHORITY verifier, not an installer.

The trust-store is provisioned out-of-band by a separately controlled operator.
This module never creates a private key, edits /boot, enrolls keys, reboots, or
returns an installer capability. Admission records a one-use release decision;
actual installation additionally requires an independently reviewed actuator.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'arda-gen11-production-boot-authorization-v1'
POLICY_SCHEMA = 'arda-gen11-production-trust-policy-v1'
ACTION = 'admit_protected_boot_transaction'
DESTINATION = '/boot/grub/grub.cfg'
PROFILE = 'EXPERIMENTAL_RING0_MASKED'
EXPECTED_GEN10_VERITY = 'c7dd6c826af174ab7ba3d819e49f8d40d1b8f7188cb46363054b35cfa6579337'
FIELDS = {'schema','action','authorization_id','generation','boot_profile','destination',
          'dossier_sha256','candidate_grub_sha256','baseline_grub_sha256',
          'baseline_grub_fsverity','gen11_kernel_sha256','gen11_initrd_sha256',
          'measured_policy_transition_sha256','recovery_evidence_sha256',
          'installer_sha256','issued_at','expires_at'}
DIGEST_FIELDS = {'dossier_sha256','candidate_grub_sha256','baseline_grub_sha256',
                 'baseline_grub_fsverity','gen11_kernel_sha256','gen11_initrd_sha256',
                 'measured_policy_transition_sha256','recovery_evidence_sha256','installer_sha256'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[A-Za-z0-9_-]{16,100}\Z')

class Refuse(RuntimeError): pass

def need(ok, why):
    if not ok: raise Refuse(why)

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def sha(data): return hashlib.sha256(data).hexdigest()

def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for part in iter(lambda:f.read(1<<20), b''): h.update(part)
    return h.hexdigest()

def parse_time(value):
    need(type(value) is str, 'time_type')
    try: out=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc: raise Refuse('time_format') from exc
    need(out.tzinfo is not None, 'timezone_required')
    return out.astimezone(timezone.utc)

def safe_public_file(p):
    """Reject symlinks, writable parents, non-root-owned production trust data."""
    p=Path(p)
    need(p.is_absolute(), 'trust_must_be_absolute')
    for path in (p, *p.parents):
        st=path.lstat()
        need(not stat.S_ISLNK(st.st_mode), 'trust_symlink')
        need(st.st_uid==0, 'trust_not_root_owned')
        need(not st.st_mode & (stat.S_IWGRP|stat.S_IWOTH), 'trust_parent_writable')
    need(p.is_file(), 'trust_not_file')
    return p

def check_policy(policy_path, *, enforce_ownership=True):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    path=safe_public_file(policy_path) if enforce_ownership else Path(policy_path)
    doc=json.loads(path.read_text())
    need(type(doc) is dict and set(doc)=={'schema','status','release_key_pem','key_fingerprint_sha256',
                                         'attestation_key_fingerprints_sha256','scope'}, 'policy_fields')
    need(doc['schema']==POLICY_SCHEMA and doc['status']=='APPROVED', 'policy_not_approved')
    need(doc['scope']=='GEN11_PROTECTED_BOOT_ADMISSION_ONLY', 'policy_scope')
    pem=doc['release_key_pem'].encode()
    pub=serialization.load_pem_public_key(pem)
    need(isinstance(pub,Ed25519PublicKey), 'key_type')
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    raw=pub.public_bytes(Encoding.Raw,PublicFormat.Raw)
    fp=sha(raw)
    need(doc['key_fingerprint_sha256']==fp, 'key_fingerprint')
    att=doc['attestation_key_fingerprints_sha256']
    need(type(att) is list and len(att)>0 and all(type(x) is str and SHA.fullmatch(x) for x in att), 'attestation_exclusion_set')
    need(fp not in att, 'attestation_key_reused')
    return pub,fp

def check_envelope(authorization, *, policy_path, expected, now=None, enforce_ownership=True):
    """Authorize a release intent only; no boot/write capability is returned.

    expected must come from a separately validated candidate, existing Gen10
    measurement, reviewed measured-policy plan, recovery proof and installer hash.
    Never build expected from untrusted fields in the envelope itself.
    """
    policy_pub, fp=check_policy(policy_path,enforce_ownership=enforce_ownership)
    raw=json.loads(Path(authorization).read_text()) if isinstance(authorization,(str,Path)) else authorization
    need(type(raw) is dict and set(raw)=={'payload','signature'}, 'envelope_fields')
    p=raw['payload']
    need(type(p) is dict and set(p)==FIELDS, 'signed_field_set')
    need(p['schema']==SCHEMA and p['action']==ACTION,'scope')
    need(type(p['generation']) is int and p['generation']==11,'generation')
    need(p['boot_profile']==PROFILE,'boot_profile')
    need(p['destination']==DESTINATION,'destination')
    need(type(p['authorization_id']) is str and ID.fullmatch(p['authorization_id']),'authorization_id')
    for name in DIGEST_FIELDS: need(type(p[name]) is str and SHA.fullmatch(p[name]),'digest_format:'+name)
    need(set(expected)==DIGEST_FIELDS,'independent_expectations_required')
    for name in DIGEST_FIELDS:
        need(type(expected[name]) is str and SHA.fullmatch(expected[name]),'expected_digest:'+name)
        need(p[name]==expected[name], 'binding:'+name)
    need(p['baseline_grub_fsverity']==EXPECTED_GEN10_VERITY,'gen10_verity_baseline')
    now = now or datetime.now(timezone.utc)
    issued,expires=parse_time(p['issued_at']),parse_time(p['expires_at'])
    need(issued<=now<expires and 0<(expires-issued).total_seconds()<=600, 'freshness')
    try:
        sig=base64.b64decode(raw['signature'],validate=True)
        need(len(sig)==64,'signature_length')
        policy_pub.verify(sig,canonical(p))
    except (ValueError,TypeError) as exc: raise Refuse('signature_encoding') from exc
    except Exception as exc:
        from cryptography.exceptions import InvalidSignature
        if isinstance(exc,InvalidSignature): raise Refuse('invalid_signature') from exc
        raise
    return {'status':'ADMITTED_FOR_HUMAN_REVIEW','authorization_id':p['authorization_id'],
            'authorization_sha256':sha(canonical(raw)),'release_key_fingerprint_sha256':fp,
            'installation_authorized':False,'first_boot_authorized':False,
            'reason':'PRODUCTION_ACTUATOR_AND_RECOVERY_NOT_YET_APPROVED'}

class AdmissionLedger:
    """One-use admission ledger: no automatic retry, no implicit release."""
    def __init__(self, db):
        self.db=Path(db)
        need(self.db.is_absolute() and not self.db.is_symlink(),'ledger_path')
        self.db.parent.mkdir(parents=False,exist_ok=True)
        self.conn=sqlite3.connect(str(self.db), isolation_level=None,timeout=10)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.execute('CREATE TABLE IF NOT EXISTS admissions (id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN (\'review_required\',\'rejected\')))')
    def admit(self,decision):
        need(decision.get('status')=='ADMITTED_FOR_HUMAN_REVIEW', 'not_admitted')
        try:
            self.conn.execute('BEGIN IMMEDIATE')
            self.conn.execute('INSERT INTO admissions(id,digest,state) VALUES (?,?,?)',
                              (decision['authorization_id'],decision['authorization_sha256'],'review_required'))
            self.conn.execute('COMMIT')
        except sqlite3.IntegrityError as exc:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise Refuse('authorization_replay') from exc
        except BaseException:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise
        return decision
