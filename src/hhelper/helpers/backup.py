from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def backup_file(path: Path) -> str:
    backup_path = "".join([str(path), ".bak"])

    shutil.copy(path, backup_path)

    return backup_path
