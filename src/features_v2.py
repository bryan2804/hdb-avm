"""DEPRECATED shim — feature logic now lives in hdb_avm.features.pipeline.

Kept only so the monthly retrain workflow's entry point
(`python3 src/features_v2.py`) keeps working. Do not add logic here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hdb_avm.features.pipeline import build_features  # noqa: E402

if __name__ == "__main__":
    build_features()
