from pathlib import Path
import json

from backend.services.arda_bombadil import CovenantChain


REPO_ROOT = Path(__file__).resolve().parents[2]

coronation_path = REPO_ROOT / "evidence/08_covenant_chain.json"
db_path = REPO_ROOT / "evidence/covenant_chain.db"

coronation = json.loads(coronation_path.read_text())[0]

mirror_id = coronation["mirror_id"]

chain = CovenantChain(db_path)

event = chain.append(
    event_type="CORONATION_IDENTITY_RECONCILIATION",
    mirror_id=mirror_id,
    principal="restoration",
    detail=(
        "Restored execution ledger continuity with original "
        "sovereign coronation mirror identity."
    ),
    truth_mode="VERIFIED",
)

print(json.dumps(event, indent=2))
