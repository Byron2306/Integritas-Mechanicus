#!/usr/bin/env python3

from backend.services.witnessed_authority_gauntlet import (
    GauntletRunContext,
    opening_banner,
    render_stage,
)

def main() -> int:
    ctx = GauntletRunContext.new()

    print(opening_banner())
    print()
    print(f"RUN ID ...................... {ctx.run_id}")
    print(f"HOST ........................ {ctx.hostname}")

    print(render_stage(
        "THE MUSIC AWAKENS",
        [
            "Gauntlet context initialized.",
            "Enforcement remains in safe preflight posture.",
        ],
        [
            "Nothing dangerous has been armed yet.",
        ],
    ))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
