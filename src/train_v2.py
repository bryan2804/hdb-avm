"""DEPRECATED shim — training logic now lives in hdb_avm.training.train.

Kept only so the monthly retrain workflow's entry point
(`python3 src/train_v2.py`) keeps working. Do not add logic here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hdb_avm.training.train import train  # noqa: E402

if __name__ == "__main__":
    train()
