"""
part2/verifier.py
-------------------
End-to-end verification of post data against the blockchain record.
Re-exported for part2 directory structure.
"""

from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from blockchain.verifier import verify_post, verify_post_with_original

__all__ = ["verify_post", "verify_post_with_original"]
