from backend.services.witnessed_authority_gauntlet import (
    GauntletRunContext,
    GauntletResult,
    opening_banner,
    render_stage,
)

def test_opening_banner_is_unmistakably_arda():
    out = opening_banner()
    assert "ARDA // VALINOR WITNESSED RUN" in out
    assert "EXECUTION DOES NOT EQUAL AUTHORITY" in out
    assert "witness → forge → herald → enforce" in out

def test_stage_uses_myth_mechanism_meaning_order():
    out = render_stage(
        "VARDA · LADY OF LIGHT",
        ["Measured truth / manifest coherence"],
        ["Are we looking at the thing we think we are looking at?"],
    )
    assert out.index("VARDA") < out.index("TECHNICAL") < out.index("WHY IT MATTERS")

def test_run_context_starts_unarmed():
    ctx = GauntletRunContext.new()
    assert ctx.enforcement_armed is False
    assert ctx.native_pqc_verified is False
    assert ctx.heralded is False
    assert ctx.result == GauntletResult.PENDING
