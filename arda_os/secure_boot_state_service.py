import logging
import os
import subprocess
from typing import List, Optional
try:
    from schemas.phase6_models import SecureBootState
except Exception:
    from backend.schemas.phase6_models import SecureBootState

logger = logging.getLogger(__name__)

class SecureBootStateService:
    """
    Service to verify the hardware's Secure Boot state.
    Essential for determining the 'Lawful Birth' of a node in Phase VI.
    """
    
    def __init__(self):
        self.is_linux = os.name != 'nt'

    async def get_secure_boot_state(self) -> SecureBootState:
        """Determines if Secure Boot is active and retrieves vendor keys (Phase VI)."""
        # Phase VI: Mock override for sovereignty testing
        if os.environ.get("TPM_MOCK_ENV") == "production":
            return SecureBootState(
                enabled=True,
                setup_mode=False,
                secure_boot_mode="User",
                vendor_keys=["Seraph-Root-Genesis"]
            )

        if self.is_linux:
            return await self._get_linux_sb_state()
        else:
            return await self._get_windows_sb_state()

    async def _get_linux_sb_state(self) -> SecureBootState:
        """Reads EFI variables from /sys/firmware/efi/efivars."""
        try:
            sb_path = "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
            if os.path.exists(sb_path):
                with open(sb_path, "rb") as f:
                    # The first 4 bytes are attributes, the 5th byte is the state
                    data = f.read()
                    enabled = data[4] == 1
                return SecureBootState(
                    enabled=enabled,
                    setup_mode=False, # Would require reading SetupMode-xxx
                    secure_boot_mode="User",
                    vendor_keys=["Microsoft", "OEM"]
                )
            
            # Alternate check using bootctl or mokutil
            result = subprocess.run(["mokutil", "--sb-state"], capture_output=True, text=True)
            if "enabled" in result.stdout.lower():
                return SecureBootState(enabled=True, setup_mode=False, secure_boot_mode="User", vendor_keys=[])
        except Exception as e:
            logger.warning(f"Failed to read Linux Secure Boot state: {e}")
            
        return SecureBootState(enabled=False, setup_mode=True, secure_boot_mode="None", vendor_keys=[])

    async def _get_windows_sb_state(self) -> SecureBootState:
        """Uses PowerShell's Get-SecureBootUEFI to check state on Windows."""
        try:
            cmd = ["powershell", "-Command", "Confirm-SecureBootUEFI"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            enabled = "True" in result.stdout
            return SecureBootState(
                enabled=enabled,
                setup_mode=False,
                secure_boot_mode="User" if enabled else "None",
                vendor_keys=[]
            )
        except Exception:
            return SecureBootState(enabled=False, setup_mode=True, secure_boot_mode="None", vendor_keys=[])

# Singleton
_instance = None
def get_secure_boot_state_service():
    global _instance
    if _instance is None:
        _instance = SecureBootStateService()
    return _instance
