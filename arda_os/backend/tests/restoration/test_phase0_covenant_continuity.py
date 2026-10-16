from pathlib import Path
import json
import sqlite3


REPO_ROOT = Path(__file__).resolve().parents[4]
ARDA_ROOT = REPO_ROOT / "arda_os"


def test_covenant_chain_json_exists():
    path = REPO_ROOT / "evidence/08_covenant_chain.json"
    assert path.exists(), f"Missing {path}"


def test_covenant_chain_database_exists():
    path = REPO_ROOT / "evidence/covenant_chain.db"
    assert path.exists(), f"Missing {path}"


def test_covenant_chain_json_is_readable():
    path = REPO_ROOT / "evidence/08_covenant_chain.json"

    data = json.loads(path.read_text())

    assert isinstance(data, list)
    assert len(data) > 0
    assert "entry_type" in data[0]


def test_covenant_database_has_tables():
    path = REPO_ROOT / "evidence/covenant_chain.db"

    conn = sqlite3.connect(path)

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    conn.close()

    assert len(tables) > 0, "Covenant database has no tables"


def test_coronation_references_covenant():
    path = ARDA_ROOT / "backend/services/coronation_schemas.py"

    text = path.read_text()

    assert "covenant" in text.lower()


def test_handoff_references_projection():
    path = ARDA_ROOT / "backend/services/handoff_covenant.py"

    text = path.read_text()

    assert (
        "projection" in text.lower()
        or "constitutional" in text.lower()
    )
