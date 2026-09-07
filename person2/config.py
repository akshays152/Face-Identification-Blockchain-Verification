"""
person2/config.py
-----------------
Loads environment variables for Person 2's Blockchain Verification Module.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Find project root .env
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Config:
    """Centralised configuration loaded from environment variables."""

    RPC_URL: str = os.getenv("RPC_URL", "http://127.0.0.1:8545")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "31337"))

    CONTRACT_SOL: Path = Path(__file__).resolve().parent / "contract.sol"

    @classmethod
    def validate(cls, require_contract: bool = False) -> None:
        errors: list[str] = []
        if not cls.RPC_URL:
            errors.append("RPC_URL is not set. Add it to your .env file.")
        if not cls.PRIVATE_KEY:
            errors.append("PRIVATE_KEY is not set. Add it to your .env file.")
        if require_contract and not cls.CONTRACT_ADDRESS:
            errors.append(
                "CONTRACT_ADDRESS is not set. Deploy the contract first "
                "(py person2/deploy.py) then add the address to .env."
            )
        if errors:
            for e in errors:
                print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
