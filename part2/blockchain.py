"""
part2/blockchain.py
----------------------
Python interface to the ContentVerifier smart contract.

Provides:
    BlockchainClient.connect()
    BlockchainClient.store_fingerprint(sha256_hex)
    BlockchainClient.fingerprint_exists(sha256_hex)
    BlockchainClient.get_record(sha256_hex)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from web3 import Web3
from solcx import compile_source, install_solc, get_installed_solc_versions

# Load .env from project root
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

SOLC_VERSION = "0.8.20"
CONTRACT_SOL = Path(__file__).resolve().parent / "contract.sol"

# Configuration from environment
RPC_URL: str = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
CHAIN_ID: int = int(os.getenv("CHAIN_ID", "31337"))


class BlockchainError(Exception):
    """Raised for blockchain-related errors with a user-friendly message."""


class BlockchainClient:
    """High-level wrapper around the ContentVerifier contract."""

    def __init__(self) -> None:
        self.w3: Web3 | None = None
        self.contract = None
        self.account: str = ""
        self._private_key: str = ""
        self._abi: list | None = None
        self._bytecode: str = ""

    # -- Connection --

    def connect(self) -> None:
        """Connect to the blockchain node specified in .env."""
        if not PRIVATE_KEY:
            raise BlockchainError(
                "PRIVATE_KEY is not set. Add it to your .env file."
            )
        try:
            self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        except Exception as exc:
            raise BlockchainError(
                f"Could not create Web3 provider.\n"
                f"  RPC_URL: {RPC_URL}\n"
                f"  Error:   {exc}"
            ) from exc

        if not self.w3.is_connected():
            raise BlockchainError(
                f"Blockchain connection failed.\n"
                f"  Check RPC_URL in your .env file ({RPC_URL}).\n"
                f"  If using a local node, make sure it is running."
            )

        self._private_key = PRIVATE_KEY
        self.account = self.w3.eth.account.from_key(self._private_key).address

    # -- Compilation --

    def compile_contract(self) -> tuple[list, str]:
        """Compile contract.sol and return (abi, bytecode)."""
        if self._abi and self._bytecode:
            return self._abi, self._bytecode

        if not CONTRACT_SOL.is_file():
            raise BlockchainError(f"Solidity source not found: {CONTRACT_SOL}")

        if SOLC_VERSION not in [str(v) for v in get_installed_solc_versions()]:
            print(f"  Installing solc {SOLC_VERSION} ...")
            install_solc(SOLC_VERSION)

        source = CONTRACT_SOL.read_text(encoding="utf-8")
        compiled = compile_source(
            source,
            output_values=["abi", "bin"],
            solc_version=SOLC_VERSION,
        )

        contract_id = None
        for cid in compiled:
            if "ContentVerifier" in cid:
                contract_id = cid
                break
        if contract_id is None:
            contract_id, _ = compiled.popitem()

        interface = compiled[contract_id]
        self._abi = interface["abi"]
        self._bytecode = interface["bin"]
        return self._abi, self._bytecode

    # -- Deploy --

    def deploy(self) -> str:
        """Deploy the ContentVerifier contract. Returns the contract address."""
        if not self.w3:
            raise BlockchainError("Not connected. Call connect() first.")

        abi, bytecode = self.compile_contract()
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        tx = Contract.constructor().build_transaction({
            "from": self.account,
            "nonce": self.w3.eth.get_transaction_count(self.account),
            "gas": 3_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": CHAIN_ID,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self._private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise BlockchainError("Contract deployment transaction failed.")

        address = receipt.contractAddress
        self._attach(address)
        return address

    # -- Attach to an existing deployment --

    def attach(self, address: str | None = None) -> None:
        """Attach to an already-deployed ContentVerifier contract."""
        addr = address or CONTRACT_ADDRESS
        if not addr:
            raise BlockchainError(
                "No CONTRACT_ADDRESS provided.\n"
                "  Deploy first (py part2/deploy.py) then set CONTRACT_ADDRESS in .env."
            )
        self._attach(addr)

    def _attach(self, address: str) -> None:
        abi, _ = self.compile_contract()
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi,
        )

    # -- Store --

    def store_fingerprint(self, sha256_hex: str) -> dict:
        """Store a SHA-256 fingerprint on the blockchain."""
        if not self.contract:
            raise BlockchainError("Contract not attached. Call attach() or deploy() first.")

        hash_bytes = bytes.fromhex(sha256_hex)
        if len(hash_bytes) != 32:
            raise BlockchainError(f"Expected 32-byte hash, got {len(hash_bytes)} bytes.")

        if self.contract.functions.verifyHash(hash_bytes).call():
            raise BlockchainError(
                "This fingerprint is already stored on the blockchain.\n"
                "  Each fingerprint can only be stored once."
            )

        tx = self.contract.functions.storeHash(hash_bytes).build_transaction({
            "from": self.account,
            "nonce": self.w3.eth.get_transaction_count(self.account),
            "gas": 200_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": CHAIN_ID,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self._private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise BlockchainError("Store transaction failed on-chain.")

        return {
            "fingerprint": sha256_hex,
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "contract_address": self.contract.address,
        }

    # -- Query --

    def fingerprint_exists(self, sha256_hex: str) -> bool:
        """Check whether a fingerprint has been stored."""
        if not self.contract:
            raise BlockchainError("Contract not attached.")
        hash_bytes = bytes.fromhex(sha256_hex)
        return self.contract.functions.verifyHash(hash_bytes).call()

    def get_record(self, sha256_hex: str) -> dict:
        """Retrieve the on-chain record for a fingerprint."""
        if not self.contract:
            raise BlockchainError("Contract not attached.")
        hash_bytes = bytes.fromhex(sha256_hex)
        submitter, timestamp, exists = self.contract.functions.getRecord(hash_bytes).call()
        return {
            "submitter": submitter,
            "timestamp": timestamp,
            "exists": exists,
        }
