"""
Face Identification & Blockchain Verification -- Main Pipeline
------------------------
This script ties the search/face output to the blockchain verification module.

Usage
-----
    py main.py [path_to_post_json]

If no path is provided, it defaults to data/discovered_post.json,
and falls back to data/sample_post.json if that doesn't exist.
"""

import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure the root is in path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from blockchain.blockchain import BlockchainClient, BlockchainError
from blockchain.hash_generator import generate_fingerprint
from blockchain.verifier import verify_post, verify_post_with_original

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------

DATA_DIR = _ROOT / "data"
DEFAULT_POST_JSON = DATA_DIR / "discovered_post.json"
SAMPLE_POST_JSON = DATA_DIR / "sample_post.json"

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------

def _hr() -> str:
    return "=" * 55

def _sub_hr() -> str:
    return "-" * 55

def _load_post(path: Path) -> dict:
    if not path.is_file():
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {path.name}: {e}")
        sys.exit(1)

# -------------------------------------------------------------
# Pipeline
# -------------------------------------------------------------

def main():
    # -- Determine input file --
    if len(sys.argv) > 1:
        post_path = Path(sys.argv[1])
    elif DEFAULT_POST_JSON.is_file():
        post_path = DEFAULT_POST_JSON
    else:
        post_path = SAMPLE_POST_JSON

    print()
    print(_hr())
    print("  FACE VERIFICATION -- BLOCKCHAIN VERIFICATION MODULE")
    print(_hr())
    print()

    # -- [1] Load post data --
    print("[1] Loading discovered post ...")
    post_data = _load_post(post_path)
    print(f"[OK] Post data loaded from: {post_path.name}")
    print(f"     URL:  {post_data.get('post_url', 'N/A')}")
    print(f"     Text: {str(post_data.get('post_text', ''))[:40]}...")
    print()

    # -- [2] Fingerprint --
    print("[2] Creating canonical fingerprint ...")
    fp = generate_fingerprint(post_data)
    sha256 = fp["sha256"]
    img_status = fp["image_info"]["status"]
    img_detail = fp["image_info"]["detail"]
    print("[OK] SHA-256 generated")
    print(f"     Fingerprint: {sha256}")
    print(f"     Image:       {img_status} -- {img_detail}")
    print()

    # -- [3] Connect to blockchain --
    print("[3] Connecting to blockchain ...")
    client = BlockchainClient()
    try:
        client.connect()
    except BlockchainError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Connected to {client.w3.provider.endpoint_uri}")
    print(f"     Account: {client.account}")
    print()

    # -- [4] Deploy / Attach Contract --
    # For this demo, we deploy a fresh contract every run so
    # the local node doesn't throw "already stored" errors if
    # the same data is tested repeatedly.
    print("[4] Deploying fresh ContentVerifier contract ...")
    try:
        addr = client.deploy()
    except BlockchainError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    print(f"[OK] Contract deployed at: {addr}")
    print()

    # -- [5] Store --
    print("[5] Uploading fingerprint to blockchain ...")
    try:
        store_res = client.store_fingerprint(sha256)
        print("[OK] Blockchain transaction confirmed")
        print(f"     Transaction: {store_res['transaction_hash']}")
        print(f"     Block:       {store_res['block_number']}")
    except BlockchainError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    print()

    # -- [6] Retrieve --
    print("[6] Reading blockchain record ...")
    try:
        record = client.get_record(sha256)
        print("[OK] Record retrieved")
        print(f"     Exists:    {record['exists']}")
        print(f"     Submitter: {record['submitter']}")
        print(f"     Timestamp: {record['timestamp']}")
    except BlockchainError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    print()

    # -- [7] Verify --
    print("[7] Verifying content integrity ...")
    verification = verify_post(post_data, client)
    if verification["verified"]:
        print("[OK] Hash matches blockchain record")
        print()
        print(_hr())
        print("  RESULT:  VERIFIED  [OK]")
        print(_hr())
    else:
        print(f"[FAIL] {verification['message']}")
        print()
        print(_hr())
        print("  RESULT:  NOT VERIFIED  [FAIL]")
        print(_hr())


    # =========================================================
    # Tamper test demonstration
    # =========================================================
    print()
    print(_sub_hr())
    print("  TAMPER TEST")
    print(_sub_hr())
    print()

    # Modify the text
    tampered_data = dict(post_data)
    tampered_data["post_text"] = "THIS TEXT HAS BEEN MALICIOUSLY MODIFIED"

    tamper_res = verify_post_with_original(
        original_data=post_data,
        current_data=tampered_data,
        client=client
    )

    print(f"  Original SHA-256:  {tamper_res['blockchain_hash']}")
    print(f"  Tampered SHA-256:  {tamper_res['current_hash']}")
    print(f"  Hashes match:      {tamper_res['current_hash'] == tamper_res['blockchain_hash']}")
    print()

    if not tamper_res["verified"]:
        print("  [FAIL] NOT VERIFIED -- content has been modified")
        print(f"        {tamper_res['message']}")
    else:
        print("  [OK] Wait, that shouldn't happen.")

    # Re-verify original
    print()
    print(_sub_hr())
    print("  SANITY CHECK -- re-verify original data")
    print(_sub_hr())
    print()
    
    sanity = verify_post_with_original(
        original_data=post_data,
        current_data=post_data,
        client=client
    )
    if sanity["verified"]:
        print("  [OK] VERIFIED -- original data still matches blockchain")
    else:
        print("  [FAIL] Something went wrong with sanity check.")

    print()
    print(_hr())
    print("  PIPELINE COMPLETE")
    print(_hr())


if __name__ == "__main__":
    main()
