from __future__ import annotations

import os
import tempfile
from pathlib import Path

from hhelper.helpers.backup import hhelper_dir


def safe_write(path: Path, content: str) -> None:
    # A complete copy is written to .hhelper/tmp first, so a full disk fails
    # before the file is touched, and the copy survives if the write below is
    # interrupted. The file is then rewritten in place rather than replaced by
    # a rename: hledger-ui --watch only reloads on in-place modification, and
    # links, owner and permissions are kept.
    target = path.resolve()

    fd, tmp_name = tempfile.mkstemp(
        dir=hhelper_dir(path, "tmp"), prefix=f"{target.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    try:
        with target.open("w") as target_file:
            target_file.write(content)
            target_file.flush()
            os.fsync(target_file.fileno())

    except BaseException:
        print(f"Writing {target} failed. The new content is saved at {tmp_path}")
        raise

    tmp_path.unlink()
