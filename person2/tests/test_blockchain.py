"""
Tests for person2.blockchain and person2.verifier
──────────────────────────────────────────────────
These tests require a running local blockchain (Hardhat node).

Run with:
    npx hardhat node          # in one terminal
    py -m pytest person2/tests/test_blockchain.py -v   # in another

The tests deploy a fresh contract for each test session, so no
leftover state between runs.
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from person2.blockchain import BlockchainClient, BlockchainError
from person2.hash_generator import generate_fingerprint
from person2.verifier import verify_post, verify_post_with_original

# ── Fixtures ─────────────────────────────────────────────────

SAMPLE_POST = {
    "post_url": "https://example.com/sample-post-12345",
    "post_image": "nonexistent.jpg",
    "post_text": "Sample content for blockchain verification testing",
    "metadata": {"source": "development-test", "platform": "example"},
    "similarity": 0.91,
}


def _blockchain_available() -> bool:
    """Check if a local blockchain is reachable."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        return w3.is_connected()
    except Exception:
        return False


# Skip the whole module if no blockchain is running
pytestmark = pytest.mark.skipif(
    not _blockchain_available(),
    reason="Local blockchain not running (start with: npx hardhat node)",
)


@pytest.fixture(scope="module")
def client() -> BlockchainClient:
    """Deploy a fresh contract and return a connected client."""
    # Force local config
    os.environ.setdefault("RPC_URL", "http://127.0.0.1:8545")
    os.environ.setdefault("CHAIN_ID", "31337")
    # Hardhat/Anvil default account #0
    os.environ.setdefault(
        "PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )

    # Reload config so it picks up the env vars we just set
    from person2.config import Config
    Config.RPC_URL = os.environ["RPC_URL"]
    Config.PRIVATE_KEY = os.environ["PRIVATE_KEY"]
    Config.CHAIN_ID = int(os.environ["CHAIN_ID"])

    c = BlockchainClient()
    c.connect()
    address = c.deploy()
    Config.CONTRACT_ADDRESS = address
    return c


# ── Blockchain storage tests ─────────────────────────────────

class TestBlockchainStorage:

    def test_store_fingerprint(self, client: BlockchainClient):
        fp = generate_fingerprint(SAMPLE_POST)
        result = client.store_fingerprint(fp["sha256"])

        assert result["fingerprint"] == fp["sha256"]
        assert result["transaction_hash"]  # non-empty real tx hash
        assert isinstance(result["block_number"], int)
        assert result["contract_address"] == client.contract.address

    def test_fingerprint_exists(self, client: BlockchainClient):
        fp = generate_fingerprint(SAMPLE_POST)
        assert client.fingerprint_exists(fp["sha256"]) is True

    def test_fingerprint_not_exists(self, client: BlockchainClient):
        fake_hash = "a" * 64
        assert client.fingerprint_exists(fake_hash) is False

    def test_get_record(self, client: BlockchainClient):
        fp = generate_fingerprint(SAMPLE_POST)
        record = client.get_record(fp["sha256"])

        assert record["exists"] is True
        assert record["submitter"] == client.account
        assert record["timestamp"] > 0

    def test_get_record_nonexistent(self, client: BlockchainClient):
        fake_hash = "b" * 64
        record = client.get_record(fake_hash)
        assert record["exists"] is False

    def test_duplicate_store_rejected(self, client: BlockchainClient):
        fp = generate_fingerprint(SAMPLE_POST)
        with pytest.raises(BlockchainError, match="already stored"):
            client.store_fingerprint(fp["sha256"])


# ── Verification tests ───────────────────────────────────────

class TestVerification:

    def test_verify_original_data(self, client: BlockchainClient):
        """Original data that was stored should verify."""
        result = verify_post(SAMPLE_POST, client)
        assert result["verified"] is True
        assert "VERIFIED" in result["message"]

    def test_verify_tampered_text(self, client: BlockchainClient):
        """Modified text should NOT verify."""
        tampered = copy.deepcopy(SAMPLE_POST)
        tampered["post_text"] = "This text was tampered with"
        result = verify_post(tampered, client)
        assert result["verified"] is False

    def test_verify_tampered_url(self, client: BlockchainClient):
        """Modified URL should NOT verify."""
        tampered = copy.deepcopy(SAMPLE_POST)
        tampered["post_url"] = "https://evil.com/fake"
        result = verify_post(tampered, client)
        assert result["verified"] is False

    def test_verify_tampered_metadata(self, client: BlockchainClient):
        """Modified metadata should NOT verify."""
        tampered = copy.deepcopy(SAMPLE_POST)
        tampered["metadata"] = {"source": "tampered"}
        result = verify_post(tampered, client)
        assert result["verified"] is False

    def test_verify_with_original_same(self, client: BlockchainClient):
        """Comparing original with itself → VERIFIED."""
        result = verify_post_with_original(SAMPLE_POST, SAMPLE_POST, client)
        assert result["verified"] is True

    def test_verify_with_original_tampered(self, client: BlockchainClient):
        """Comparing original with tampered → NOT VERIFIED."""
        tampered = copy.deepcopy(SAMPLE_POST)
        tampered["post_text"] = "TAMPERED CONTENT"
        result = verify_post_with_original(SAMPLE_POST, tampered, client)
        assert result["verified"] is False
        assert "TAMPERED" in result["message"] or "NOT" in result["message"]

    def test_missing_blockchain_record(self, client: BlockchainClient):
        """A post that was never stored → NOT VERIFIED."""
        unseen = {
            "post_url": "https://never-stored.com/xyz",
            "post_text": "Never stored on blockchain",
            "metadata": {},
        }
        result = verify_post(unseen, client)
        assert result["verified"] is False
        assert "No matching" in result["message"] or "not found" in result["message"].lower()
