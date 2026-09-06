"""
blockchain/blockchain.py
------------------------
Python interface to the ContentVerifier smart contract.

Provides:
    BlockchainClient.connect()
    BlockchainClient.store_fingerprint(sha256_hex)
    BlockchainClient.fingerprint_exists(sha256_hex)
    BlockchainClient.get_record(sha256_hex)
"""

from __future__ import annotations

import sys
from pathlib import Path

from web3 import Web3
from solcx import compile_source, install_solc, get_installed_solc_versions

from blockchain.config import Config

SOLC_VERSION = "0.8.20"


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
        Config.validate(require_contract=False)
        try:
            self.w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))
        except Exception as exc:
            raise BlockchainError(
                f"Could not create Web3 provider.\n"
                f"  RPC_URL: {Config.RPC_URL}\n"
                f"  Error:   {exc}"
            ) from exc

        if not self.w3.is_connected():
            raise BlockchainError(
                f"Blockchain connection failed.\n"
                f"  Check RPC_URL in your .env file ({Config.RPC_URL}).\n"
                f"  If using a local node, make sure it is running."
            )

        self._private_key = Config.PRIVATE_KEY
        self.account = self.w3.eth.account.from_key(self._private_key).address

    # -- Compilation --

    def compile_contract(self) -> tuple[list, str]:
        """Compile contract.sol and return (abi, bytecode)."""
        if self._abi and self._bytecode:
            return self._abi, self._bytecode

        sol_path = Config.CONTRACT_SOL
        if not sol_path.is_file():
            raise BlockchainError(f"Solidity source not found: {sol_path}")

        # Ensure the compiler is installed
        if SOLC_VERSION not in [str(v) for v in get_installed_solc_versions()]:
            print(f"  Installing solc {SOLC_VERSION} ...")
            install_solc(SOLC_VERSION)

        source = sol_path.read_text(encoding="utf-8")
        compiled = compile_source(
            source,
            output_values=["abi", "bin"],
            solc_version=SOLC_VERSION,
        )

        # Extract the ContentVerifier contract
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
            "chainId": Config.CHAIN_ID,
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
        addr = address or Config.CONTRACT_ADDRESS
        if not addr:
            raise BlockchainError(
                "No CONTRACT_ADDRESS provided.\n"
                "  Deploy first (py blockchain/deploy.py) then set CONTRACT_ADDRESS in .env."
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
        """
        Store a SHA-256 fingerprint on the blockchain.

        Parameters
        ----------
        sha256_hex : str
            64-character hex SHA-256 digest.

        Returns
        -------
        dict with ``fingerprint``, ``transaction_hash``,
        ``block_number``, ``contract_address``.
        """
        if not self.contract:
            raise BlockchainError("Contract not attached. Call attach() or deploy() first.")

        hash_bytes = bytes.fromhex(sha256_hex)
        if len(hash_bytes) != 32:
            raise BlockchainError(f"Expected 32-byte hash, got {len(hash_bytes)} bytes.")

        # Check if already stored
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
            "chainId": Config.CHAIN_ID,
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
        """
        Retrieve the on-chain record for a fingerprint.

        Returns
        -------
        dict with ``submitter``, ``timestamp``, ``exists``.
        """
        if not self.contract:
            raise BlockchainError("Contract not attached.")
        hash_bytes = bytes.fromhex(sha256_hex)
        submitter, timestamp, exists = self.contract.functions.getRecord(hash_bytes).call()
        return {
            "submitter": submitter,
            "timestamp": timestamp,
            "exists": exists,
        }
