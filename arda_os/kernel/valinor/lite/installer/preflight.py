"""Installer-facing Valinor Lite preflight contract.

The implementation lives in backend.services so installation tooling and
verification tests share one deterministic preflight authority.
"""

from backend.services.valinor_lite_preflight import (
    PreflightReport,
    run_preflight,
)

__all__ = [
    "PreflightReport",
    "run_preflight",
]
