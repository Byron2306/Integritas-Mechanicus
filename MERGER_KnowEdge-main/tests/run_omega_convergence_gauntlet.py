#!/usr/bin/env python3
"""Convenience launcher for MERGER V5 OMEGA convergence gauntlet."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    gauntlet = repo_root / "arda_os" / "tests" / "merger_v5_omega_convergence_gauntlet.py"
    runpy.run_path(str(gauntlet), run_name="__main__")
