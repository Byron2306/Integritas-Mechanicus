from pathlib import Path
import hashlib
import json
import sqlite3


REPO_ROOT = Path(__file__).resolve().parents[4]
DB = REPO_ROOT / "evidence/covenant_chain.db"
CORONATION = REPO_ROOT / "evidence/08_covenant_chain.json"


def _event_hash(row):
    fields = [
        row["event_id"],
        row["event_type"],
        row["mirror_id"] or "",
        row["principal"] or "",
        row["artifact_hash"] or "",
        row["detail"] or "",
        row["truth_mode"] or "",
        row["timestamp"],
        row["prev_hash"],
    ]
    return hashlib.sha256(
        "|".join(str(v) for v in fields).encode()
    ).hexdigest()


def test_reconciliation_binds_original_coronation_identity():
    coronation = json.loads(CORONATION.read_text())[0]

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT *
        FROM covenant_events
        WHERE event_type = 'CORONATION_IDENTITY_RECONCILIATION'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    assert row is not None
    assert row["mirror_id"] == coronation["mirror_id"]


def test_reconciliation_inherits_prior_execution_head():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    reconciliation = conn.execute(
        """
        SELECT *
        FROM covenant_events
        WHERE event_type = 'CORONATION_IDENTITY_RECONCILIATION'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    assert reconciliation is not None

    prior = conn.execute(
        """
        SELECT *
        FROM covenant_events
        WHERE id < ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (reconciliation["id"],),
    ).fetchone()

    conn.close()

    assert prior is not None
    assert reconciliation["prev_hash"] == prior["event_hash"]


def test_reconciliation_event_hash_is_valid():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT *
        FROM covenant_events
        WHERE event_type = 'CORONATION_IDENTITY_RECONCILIATION'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    assert row is not None
    assert _event_hash(row) == row["event_hash"]


def test_execution_history_before_reconciliation_remains_unmodified():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM covenant_events
        WHERE id < (
            SELECT id
            FROM covenant_events
            WHERE event_type = 'CORONATION_IDENTITY_RECONCILIATION'
            ORDER BY id DESC
            LIMIT 1
        )
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    assert rows

    expected_prev = "0" * 64

    for row in rows:
        assert row["prev_hash"] == expected_prev
        assert _event_hash(row) == row["event_hash"]
        expected_prev = row["event_hash"]
