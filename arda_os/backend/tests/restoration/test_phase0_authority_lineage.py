from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_ROOT = REPO_ROOT / "arda_os"



def test_coronation_schema_exists():
    path = RUNTIME_ROOT / "backend/services/coronation_schemas.py"
    assert path.exists(), f"Missing {path}"


def test_formation_manifest_exists():
    path = RUNTIME_ROOT / "backend/services/formation_manifest.py"
    assert path.exists(), f"Missing {path}"


def test_genesis_score_exists():
    path = RUNTIME_ROOT / "backend/services/genesis_score.py"
    assert path.exists(), f"Missing {path}"


def test_constitutional_projection_exists():
    path = RUNTIME_ROOT / "backend/services/constitutional_projection.py"
    assert path.exists(), f"Missing {path}"


def test_handoff_covenant_exists():
    path = RUNTIME_ROOT / "backend/services/handoff_covenant.py"
    assert path.exists(), f"Missing {path}"


def test_ainur_verdicts_exists():
    path = RUNTIME_ROOT / "backend/arda/ainur/verdicts.py"
    assert path.exists(), f"Missing {path}"


def test_covenant_chain_evidence_exists():
    path = REPO_ROOT / "evidence/covenant_chain.db"
    assert path.exists(), f"Missing {path}"
