from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENROLL = (ROOT / "installer/arda-enroll").read_text()


def test_existing_baseline_is_generation_and_manifest_bound():
    assert 'approved.get("generation") == binding.get("generation")' in ENROLL
    assert 'approved.get("manifest_id") == binding.get("manifest_id")' in ENROLL
    assert (
        'approved.get("policy_generation") == binding.get("policy_generation")'
        in ENROLL
    )


def test_existing_baseline_is_pcr_bound():
    for pcr in ("0", "1", "7", "11"):
        assert (
            f'baseline_pcrs.get("{pcr}") == current_pcrs.get("{pcr}")'
            in ENROLL
        )


def test_stale_baseline_is_preserved_before_refresh():
    assert "Archived stale PCR baseline:" in ENROLL
    assert '"history"' in ENROLL


def test_baseline_generator_runs_when_current_baseline_not_valid():
    assert 'if [[ "$BASELINE_CURRENT" -ne 1 ]]; then' in ENROLL
    assert "arda_generate_pcr_baseline.py" in ENROLL
