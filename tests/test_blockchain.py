"""
Tests for blockchain.blockchain and blockchain.verifier
-------------------------------------------------------
Verifies interaction with the local ContentVerifier smart contract.

Requirements
------------
1. Local blockchain node must be running:
    npx hardhat node                                   # in one terminal
2. Run tests:
    py -m pytest tests/test_blockchain.py -v           # in another
"""

import os
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blockchain.blockchain import BlockchainClient, BlockchainError
from blockchain.hash_generator import generate_fingerprint
from blockchain.verifier import verify_post, verify_post_with_original

# A dummy SHA-256 for basic contract testing
TEST_SHA256 = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
TEST_SHA256_2 = "c5b25372336340243e3328e1b12b2345be03c9d72dfc9bd26fb8e1546740685b"

SAMPLE_POST = {
    "post_url": "https://example.com/blockchain-test-123",
    "post_text": "Sample text for verification testing",
    "metadata": {"user": "test_agent"},
}


@pytest.fixture(scope="module")
def connected_client():
    """
    Connect to local node and deploy a fresh contract for the test module.
    Skips tests if the node is not running.
    """
    from blockchain.config import Config

    # Use Hardhat defaults if not set in environment
    if "RPC_URL" not in os.environ:
        os.environ["RPC_URL"] = "http://127.0.0.1:8545"
        Config.RPC_URL = os.environ["RPC_URL"]
    if "PRIVATE_KEY" not in os.environ:
        os.environ["PRIVATE_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        Config.PRIVATE_KEY = os.environ["PRIVATE_KEY"]
    if "CHAIN_ID" not in os.environ:
        os.environ["CHAIN_ID"] = "31337"
        Config.CHAIN_ID = int(os.environ["CHAIN_ID"])

    client = BlockchainClient()
    try:
        client.connect()
    except BlockchainError as e:
        pytest.skip(f"Blockchain connection failed (is 'npx hardhat node' running?): {e}")

    try:
        client.deploy()
    except BlockchainError as e:
        pytest.skip(f"Contract deployment failed: {e}")

    return client


class TestBlockchainStorage:
    def test_store_fingerprint(self, connected_client: BlockchainClient):
        result = connected_client.store_fingerprint(TEST_SHA256)
        assert result["fingerprint"] == TEST_SHA256
        assert result["transaction_hash"]
        assert result["block_number"] > 0
        assert result["contract_address"] == connected_client.contract.address

    def test_fingerprint_exists(self, connected_client: BlockchainClient):
        exists = connected_client.fingerprint_exists(TEST_SHA256)
        assert exists is True

    def test_fingerprint_not_exists(self, connected_client: BlockchainClient):
        dummy_hash = "0" * 64
        exists = connected_client.fingerprint_exists(dummy_hash)
        assert exists is False

    def test_get_record(self, connected_client: BlockchainClient):
        record = connected_client.get_record(TEST_SHA256)
        assert record["exists"] is True
        assert record["submitter"] == connected_client.account
        assert record["timestamp"] > 0

    def test_get_record_nonexistent(self, connected_client: BlockchainClient):
        dummy_hash = "0" * 64
        record = connected_client.get_record(dummy_hash)
        assert record["exists"] is False
        assert record["timestamp"] == 0

    def test_duplicate_store_rejected(self, connected_client: BlockchainClient):
        with pytest.raises(BlockchainError) as exc:
            connected_client.store_fingerprint(TEST_SHA256)
        assert "already stored" in str(exc.value).lower()


class TestVerification:
    @pytest.fixture(scope="class", autouse=True)
    def setup_sample(self, connected_client: BlockchainClient):
        """Store the fingerprint for SAMPLE_POST before running verification tests."""
        fp = generate_fingerprint(SAMPLE_POST)["sha256"]
        if not connected_client.fingerprint_exists(fp):
            connected_client.store_fingerprint(fp)

    def test_verify_original_data(self, connected_client: BlockchainClient):
        result = verify_post(SAMPLE_POST, connected_client)
        assert result["verified"] is True
        assert result["current_hash"] == result["blockchain_hash"]
        assert "VERIFIED" in result["message"]

    def test_verify_tampered_text(self, connected_client: BlockchainClient):
        tampered = {**SAMPLE_POST, "post_text": "TAMPERED TEXT"}
        result = verify_post(tampered, connected_client)
        assert result["verified"] is False
        assert result["blockchain_hash"] == ""
        assert "No matching fingerprint" in result["message"]

    def test_verify_tampered_url(self, connected_client: BlockchainClient):
        tampered = {**SAMPLE_POST, "post_url": "https://example.com/hacked"}
        result = verify_post(tampered, connected_client)
        assert result["verified"] is False

    def test_verify_tampered_metadata(self, connected_client: BlockchainClient):
        tampered = {**SAMPLE_POST, "metadata": {"user": "hacker"}}
        result = verify_post(tampered, connected_client)
        assert result["verified"] is False

    def test_verify_with_original_same(self, connected_client: BlockchainClient):
        result = verify_post_with_original(SAMPLE_POST, SAMPLE_POST, connected_client)
        assert result["verified"] is True

    def test_verify_with_original_tampered(self, connected_client: BlockchainClient):
        tampered = {**SAMPLE_POST, "post_text": "TAMPERED TEXT"}
        result = verify_post_with_original(SAMPLE_POST, tampered, connected_client)
        assert result["verified"] is False
        assert "TAMPERED" in result["message"]

    def test_missing_blockchain_record(self, connected_client: BlockchainClient):
        new_post = {**SAMPLE_POST, "post_url": "https://example.com/brand-new"}
        result = verify_post(new_post, connected_client)
        assert result["verified"] is False
        assert "No matching fingerprint" in result["message"]
