from __future__ import annotations

import re
import shutil
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Number of backups kept per file; older ones are deleted
KEEP_BACKUPS = 10


def hhelper_dir(path: Path, name: str) -> Path:
    # Everything hhelper creates lives in a .hhelper folder next to the files
    directory = path.parent / ".hhelper" / name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def backup_file(path: Path) -> str:
    backup_dir = hhelper_dir(path, "backups")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"{path.name}.{stamp}.bak"

    shutil.copy(path, backup_path)

    # Timestamps sort chronologically; only this file's backups are matched
    own_backup = re.compile(rf"{re.escape(path.name)}\.\d{{8}}-\d{{6}}-\d{{6}}\.bak")
    backups = sorted(p for p in backup_dir.iterdir() if own_backup.fullmatch(p.name))

    for old_backup in backups[:-KEEP_BACKUPS]:
        old_backup.unlink()

    return str(backup_path)
