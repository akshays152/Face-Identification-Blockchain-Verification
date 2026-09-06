"""
person2/deploy.py
-----------------
Compile and deploy the ContentVerifier smart contract.

Usage
-----
    py person2/deploy.py

Requires a running blockchain node (local Anvil/Hardhat or Sepolia)
and a .env file with RPC_URL and PRIVATE_KEY.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from person2.blockchain import BlockchainClient, BlockchainError


def main() -> None:
    print("=" * 50)
    print("  CONTENTVERIFIER -- CONTRACT DEPLOYMENT")
    print("=" * 50)
    print()

    client = BlockchainClient()

    # -- Connect --
    print("[1] Connecting to blockchain ...")
    try:
        client.connect()
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Connected to {client.w3.provider.endpoint_uri}")
    print(f"     Account: {client.account}")
    print()

    # -- Compile --
    print("[2] Compiling ContentVerifier ...")
    try:
        client.compile_contract()
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    print("[OK] Contract compiled")
    print()

    # -- Deploy --
    print("[3] Deploying contract ...")
    try:
        address = client.deploy()
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    print("[OK] Contract deployed")
    print(f"     Contract Address: {address}")
    print()
    print("-" * 50)
    print(f"Add this to your .env file:")
    print(f"  CONTRACT_ADDRESS={address}")
    print("-" * 50)


if __name__ == "__main__":
    main()
