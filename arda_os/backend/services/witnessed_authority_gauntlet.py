from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import socket
import uuid


class GauntletResult(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    REFUSED = "REFUSED"


@dataclass
class GauntletRunContext:
    run_id: str
    started_at: str
    hostname: str
    enforcement_armed: bool = False
    native_pqc_verified: bool = False
    heralded: bool = False
    witness_digests: dict[str, str] = field(default_factory=dict)
    result: GauntletResult = GauntletResult.PENDING

    @classmethod
    def new(cls):
        return cls(
            run_id=f"arda-gauntlet-{uuid.uuid4().hex[:12]}",
            started_at=datetime.now(timezone.utc).isoformat(),
            hostname=socket.gethostname(),
        )


def opening_banner() -> str:
    return """
╔══════════════════════════════════════════════════════════════╗
║              ARDA // VALINOR WITNESSED RUN                 ║
║                                                            ║
║              EXECUTION DOES NOT EQUAL AUTHORITY            ║
╚══════════════════════════════════════════════════════════════╝

                    .       *       .
              *        THE MUSIC        *
                    .       *       .

              witness → forge → herald → enforce
""".strip()


def render_stage(title: str, technical: list[str], why: list[str]) -> str:
    out = [
        "",
        "┌────────────────────────────────────────────────────────────┐",
        f"  {title}",
        "└────────────────────────────────────────────────────────────┘",
        "",
        "TECHNICAL",
    ]
    out += [f"  {x}" for x in technical]
    out += ["", "WHY IT MATTERS"]
    out += [f"  {x}" for x in why]
    return "\n".join(out)
