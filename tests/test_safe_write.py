import os
import stat
from pathlib import Path

import pytest

from hhelper.helpers import safe_write as safe_write_module
from hhelper.helpers.safe_write import safe_write


def tmp_copies(directory: Path) -> list[Path]:
    tmp_dir = directory / ".hhelper" / "tmp"
    return list(tmp_dir.iterdir()) if tmp_dir.exists() else []


def test_writes_content_and_leaves_no_copy(tmp_path: Path) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("old\n")

    safe_write(ledger, "new\n")

    assert ledger.read_text() == "new\n"
    assert tmp_copies(tmp_path) == []


def test_creates_a_missing_file(tmp_path: Path) -> None:
    prices = tmp_path / "prices.txt"

    safe_write(prices, "P 2024-01-01 EUR 1.1 USD\n")

    assert prices.read_text() == "P 2024-01-01 EUR 1.1 USD\n"


def test_keeps_inode_permissions_symlinks_and_hard_links(tmp_path: Path) -> None:
    real = tmp_path / "real.ledger"
    real.write_text("old\n")
    os.chmod(real, 0o640)
    inode = real.stat().st_ino
    link = tmp_path / "link.ledger"
    link.symlink_to(real)
    hard_link = tmp_path / "hard.ledger"
    os.link(real, hard_link)

    safe_write(link, "new\n")

    assert link.is_symlink()
    assert real.stat().st_ino == inode
    assert stat.S_IMODE(real.stat().st_mode) == 0o640
    assert hard_link.read_text() == "new\n"


def test_full_disk_leaves_the_file_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("old\n")

    def no_space(fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(safe_write_module.os, "fsync", no_space)

    with pytest.raises(OSError, match="No space"):
        safe_write(ledger, "new\n")

    assert ledger.read_text() == "old\n"
    assert tmp_copies(tmp_path) == []


def test_interrupted_write_keeps_a_recovery_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("old\n")
    real_fsync = os.fsync
    calls = []

    def fail_on_second_fsync(fd: int) -> None:
        calls.append(fd)
        if len(calls) == 2:
            raise OSError(5, "I/O error")
        real_fsync(fd)

    monkeypatch.setattr(safe_write_module.os, "fsync", fail_on_second_fsync)

    with pytest.raises(OSError, match="I/O error"):
        safe_write(ledger, "new\n")

    [copy] = tmp_copies(tmp_path)
    assert copy.read_text() == "new\n"
    assert str(copy) in capsys.readouterr().out
