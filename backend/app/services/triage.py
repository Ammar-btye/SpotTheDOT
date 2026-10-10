"""Import the shared System 1 code (`amd/system1/triage`) without copying it.

The package lives at `<TRIAGE_DIR>/triage` (repo: `amd/system1/triage`; image: `/app/amd/system1/triage`).
Only the pure-Python modules are imported (events, policy, questions, render, kit): no torch.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..config import _REPO_ROOT

_TRIAGE_DIR = Path(os.environ.get("TRIAGE_DIR") or _REPO_ROOT / "amd" / "system1")
if not _TRIAGE_DIR.is_absolute():
    _TRIAGE_DIR = _REPO_ROOT / _TRIAGE_DIR
if str(_TRIAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_TRIAGE_DIR))

from triage import events as T_events  # noqa: E402
from triage import kit as T_kit  # noqa: E402
from triage import policy as T_policy  # noqa: E402
from triage import questions as T_questions  # noqa: E402
from triage import render as T_render  # noqa: E402

__all__ = ["T_events", "T_kit", "T_policy", "T_questions", "T_render", "TRIAGE_DIR"]
TRIAGE_DIR = _TRIAGE_DIR
