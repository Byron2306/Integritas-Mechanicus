from pathlib import Path
import sqlite3
import json


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_coronation_identity_reconciliation_exists():

    coronation = json.loads(
        (REPO_ROOT / "evidence/08_covenant_chain.json").read_text()
    )[0]

    mirror_id = coronation["mirror_id"]

    conn = sqlite3.connect(
        REPO_ROOT / "evidence/covenant_chain.db"
    )

    rows = conn.execute(
        """
        SELECT event_type, mirror_id
        FROM covenant_events
        WHERE event_type = 'CORONATION_IDENTITY_RECONCILIATION'
        AND mirror_id = ?
        """,
        (mirror_id,)
    ).fetchall()

    conn.close()

    assert rows
