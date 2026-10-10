"""Data locations for the offline modules: env first, so the same code runs from a checkout and inside the image.

In the repo, analyst/ lives at amd/system2/analyst and the kit at amd/system1/data/kit. The System 2 image copies
analyst/ to /app/analyst with no repository above it, so repo_root() is None there (never an IndexError at import)
and the kit comes from SPOT_KIT_DIR (docker-compose mounts amd/system1/data/kit read-only at /app/kit). The dataset
gate and the grounding entity catalog both read the kit through kit_dir(), so one run never mixes two kits.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent


def repo_root() -> Optional[Path]:
    """The checkout containing amd/system2/analyst, or None when this package was copied elsewhere (the image)."""
    up = HERE.parents
    if len(up) > 2 and up[0].name == 'system2' and up[1].name == 'amd':
        return up[2]
    return None


def kit_dir() -> Path:
    """SPOT_KIT_DIR, else the checked-in kit; ValueError when neither is available."""
    env = os.environ.get('SPOT_KIT_DIR')
    if env:
        return Path(env)
    root = repo_root()
    if root is None:
        raise ValueError('kit location unknown outside the repository: set SPOT_KIT_DIR')
    return root / 'amd' / 'system1' / 'data' / 'kit'
