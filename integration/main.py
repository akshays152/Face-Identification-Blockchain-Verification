"""
integration/main.py
-------------------
End-to-end Blockchain Verification Pipeline.

This script ties Person 1's output (person1/post_result.json) to
Person 2's blockchain verification module.

Usage
-----
    py integration/main.py                        # uses person1/post_result.json
    py integration/main.py path/to/post.json      # uses a custom JSON file

Person 1 does NOT need to change any of Person 2's code.
They only need to write their results to person1/post_result.json.
"""

from __future__ import annotations

import io
import json
import sys
import copy
from pathlib import Path

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from person2.hash_generator import generate_fingerprint
from person2.blockchain import BlockchainClient, BlockchainError
from person2.verifier import verify_post, verify_post_with_original

# -- Paths --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POST_JSON = PROJECT_ROOT / "person1" / "post_result.json"
SAMPLE_POST_JSON = PROJECT_ROOT / "person2" / "sample_post_result.json"


def _hr(char: str = "=", width: int = 55) -> str:
    return char * width


def _load_post(path: Path) -> dict:
    """Load and validate post JSON."""
    if not path.is_file():
        print(f"[ERROR] Post JSON not found: {path}")
        print("  Person 1 should create this file, or use the sample:")
        print(f"    py integration/main.py {SAMPLE_POST_JSON}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("[ERROR] Post JSON must be a JSON object (dict).")
        sys.exit(1)

    return data


def main() -> None:
    # -- Determine input file --
    if len(sys.argv) > 1:
        post_path = Path(sys.argv[1])
    elif DEFAULT_POST_JSON.is_file():
        post_path = DEFAULT_POST_JSON
    else:
        post_path = SAMPLE_POST_JSON

    print()
    print(_hr())
    print("  BLOCKCHAIN VERIFICATION MODULE")
    print(_hr())
    print()

    # -- [1] Load post data --
    print("[1] Loading discovered post ...")
    post_data = _load_post(post_path)
    print(f"[OK] Post data loaded from: {post_path.name}")
    print(f"     URL:  {post_data.get('post_url', '(none)')}")
    text_preview = (post_data.get("post_text", "") or "")[:60]
    print(f"     Text: {text_preview}...")
    print()

    # -- [2] Generate fingerprint --
    print("[2] Creating canonical fingerprint ...")
    fp = generate_fingerprint(post_data)
    sha = fp["sha256"]
    print("[OK] SHA-256 generated")
    print(f"     Fingerprint: {sha}")
    img = fp["image_info"]
    if img["status"] != "ok":
        print(f"     Image:       {img['status']} -- {img['detail']}")
    else:
        print(f"     Image:       hashed ({img['detail']})")
    print()

    # -- [3] Connect to blockchain --
    print("[3] Connecting to blockchain ...")
    client = BlockchainClient()
    try:
        client.connect()
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Connected to {client.w3.provider.endpoint_uri}")
    print(f"     Account: {client.account}")
    print()

    # -- [4] Deploy fresh contract for this run --
    print("[4] Deploying fresh ContentVerifier contract ...")
    try:
        address = client.deploy()
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Contract deployed at: {address}")
    print()

    # -- [5] Upload fingerprint --
    print("[5] Uploading fingerprint to blockchain ...")
    try:
        result = client.store_fingerprint(sha)
    except BlockchainError as e:
        print(f"     Note: {e}")
        result = {"transaction_hash": "(already stored)", "block_number": "N/A"}
    else:
        print("[OK] Blockchain transaction confirmed")
        print(f"     Transaction: 0x{result['transaction_hash']}")
        print(f"     Block:       {result['block_number']}")
    print()

    # -- [6] Retrieve record --
    print("[6] Reading blockchain record ...")
    try:
        record = client.get_record(sha)
    except BlockchainError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    print("[OK] Record retrieved")
    print(f"     Exists:    {record['exists']}")
    print(f"     Submitter: {record['submitter']}")
    print(f"     Timestamp: {record['timestamp']}")
    print()

    # -- [7] Verify original content --
    print("[7] Verifying content integrity ...")
    v = verify_post(post_data, client)
    if v["verified"]:
        print("[OK] Hash matches blockchain record")
    else:
        print(f"[FAIL] {v['message']}")
    print()

    print(_hr())
    if v["verified"]:
        print("  RESULT:  VERIFIED  [OK]")
    else:
        print("  RESULT:  NOT VERIFIED  [FAIL]")
    print(_hr())
    print()

    # -- [8] Tamper test --
    print(_hr("-"))
    print("  TAMPER TEST")
    print(_hr("-"))
    print()

    tampered = copy.deepcopy(post_data)
    tampered["post_text"] = "This text has been TAMPERED with!"
    tampered_fp = generate_fingerprint(tampered)

    print(f"  Original SHA-256:  {sha}")
    print(f"  Tampered SHA-256:  {tampered_fp['sha256']}")
    print(f"  Hashes match:      {sha == tampered_fp['sha256']}")
    print()

    t = verify_post_with_original(post_data, tampered, client)
    if t["verified"]:
        print("  [OK] VERIFIED -- content unchanged")
    else:
        print("  [FAIL] NOT VERIFIED -- content has been modified")
    print(f"        {t['message']}")
    print()

    # -- [9] Re-verify original (sanity check) --
    print(_hr("-"))
    print("  SANITY CHECK -- re-verify original data")
    print(_hr("-"))
    print()

    s = verify_post_with_original(post_data, post_data, client)
    if s["verified"]:
        print("  [OK] VERIFIED -- original data still matches blockchain")
    else:
        print("  [FAIL] NOT VERIFIED -- unexpected!")
    print()

    print(_hr())
    print("  PIPELINE COMPLETE")
    print(_hr())
    print()


if __name__ == "__main__":
    main()
