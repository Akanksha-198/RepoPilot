import os
from pathlib import Path

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/srv/workspace")).resolve()
DATA_DIR = Path(os.getenv("DATA_DIR", "/srv/data")).resolve()
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "manifests").mkdir(parents=True, exist_ok=True)
