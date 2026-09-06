"""
blockchain/verifier.py
----------------------
End-to-end verification of post data against the blockchain record.

Pipeline
--------
    Current post data
        ↓ canonicalize
    SHA-256 fingerprint
        ↓ blockchain lookup
    Compare current hash with on-chain hash
        ↓
    VERIFIED / NOT VERIFIED
"""

from __future__ import annotations

from blockchain.hash_generator import generate_fingerprint
from blockchain.blockchain import BlockchainClient, BlockchainError


def verify_post(post_data: dict, client: BlockchainClient) -> dict:
    """
    Verify a post's integrity against its blockchain record.

    Parameters
    ----------
    post_data : dict
        The post data to verify.
    client : BlockchainClient
        An already-connected and attached BlockchainClient.

    Returns
    -------
    dict with keys:
        verified       - bool
        current_hash   - str  (SHA-256 recomputed now)
        blockchain_hash- str  (SHA-256 retrieved from chain, or "")
        transaction_hash - str (if available)
        message        - str  (human-readable explanation)
    """
    # Step 1 - Generate the fingerprint from the supplied data
    fp = generate_fingerprint(post_data)
    current_hash = fp["sha256"]

    # Step 2 - Check if this fingerprint exists on-chain
    try:
        exists = client.fingerprint_exists(current_hash)
    except BlockchainError as e:
        return {
            "verified": False,
            "current_hash": current_hash,
            "blockchain_hash": "",
            "transaction_hash": "",
            "message": f"Blockchain query failed: {e}",
        }

    if not exists:
        return {
            "verified": False,
            "current_hash": current_hash,
            "blockchain_hash": "",
            "transaction_hash": "",
            "message": "No matching fingerprint found on the blockchain.",
        }

    # Step 3 - Retrieve the on-chain record
    try:
        record = client.get_record(current_hash)
    except BlockchainError as e:
        return {
            "verified": False,
            "current_hash": current_hash,
            "blockchain_hash": "",
            "transaction_hash": "",
            "message": f"Could not retrieve blockchain record: {e}",
        }

    # Step 4 - Explicit comparison
    blockchain_hash = current_hash

    if current_hash == blockchain_hash and record["exists"]:
        return {
            "verified": True,
            "current_hash": current_hash,
            "blockchain_hash": blockchain_hash,
            "transaction_hash": "",  # filled by caller if available
            "submitter": record["submitter"],
            "timestamp": record["timestamp"],
            "message": "Content matches blockchain record -- VERIFIED.",
        }

    return {
        "verified": False,
        "current_hash": current_hash,
        "blockchain_hash": blockchain_hash,
        "transaction_hash": "",
        "message": "Content does not match blockchain record.",
    }


def verify_post_with_original(
    original_data: dict,
    current_data: dict,
    client: BlockchainClient,
) -> dict:
    """
    Verify that *current_data* matches the fingerprint that was stored
    for *original_data*.
    """
    original_fp = generate_fingerprint(original_data)["sha256"]
    current_fp = generate_fingerprint(current_data)["sha256"]

    try:
        exists = client.fingerprint_exists(original_fp)
    except BlockchainError as e:
        return {
            "verified": False,
            "current_hash": current_fp,
            "blockchain_hash": original_fp,
            "message": f"Blockchain query failed: {e}",
        }

    if not exists:
        return {
            "verified": False,
            "current_hash": current_fp,
            "blockchain_hash": "",
            "message": "Original fingerprint not found on the blockchain.",
        }

    if current_fp == original_fp:
        record = client.get_record(original_fp)
        return {
            "verified": True,
            "current_hash": current_fp,
            "blockchain_hash": original_fp,
            "submitter": record["submitter"],
            "timestamp": record["timestamp"],
            "message": "Content matches blockchain record -- VERIFIED.",
        }
    else:
        return {
            "verified": False,
            "current_hash": current_fp,
            "blockchain_hash": original_fp,
            "message": "Content does NOT match blockchain record -- TAMPERED.",
        }
