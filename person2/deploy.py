"""
person2/deploy.py
-----------------
Compile and deploy the ContentVerifier smart contract.
Re-exported for person2 directory structure.
"""

from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from blockchain.deploy import main

if __name__ == "__main__":
    main()
