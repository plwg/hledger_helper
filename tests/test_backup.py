from pathlib import Path

from hhelper.helpers.backup import KEEP_BACKUPS, backup_file


def backups_of(directory: Path, name: str) -> list[Path]:
    backup_dir = directory / ".hhelper" / "backups"
    return sorted(p for p in backup_dir.iterdir() if p.name.startswith(f"{name}.2"))


def test_backup_goes_to_the_hhelper_folder(tmp_path: Path) -> None:
    ledger = tmp_path / "my.ledger"
    ledger.write_text("content\n")

    backup_path = Path(backup_file(ledger))

    assert backup_path.parent == tmp_path / ".hhelper" / "backups"
    assert backup_path.read_text() == "content\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == [".hhelper", "my.ledger"]


def test_only_the_most_recent_backups_are_kept(tmp_path: Path) -> None:
    ledger = tmp_path / "my.ledger"

    for version in range(KEEP_BACKUPS + 2):
        ledger.write_text(f"version {version}\n")
        newest = Path(backup_file(ledger))

    kept = backups_of(tmp_path, "my.ledger")

    assert len(kept) == KEEP_BACKUPS
    assert newest.read_text() == f"version {KEEP_BACKUPS + 1}\n"
    assert kept[0].read_text() == "version 2\n"


def test_rotation_does_not_touch_other_files_backups(tmp_path: Path) -> None:
    header = tmp_path / "my.ledger.header"
    header.write_text("; header\n")
    backup_file(header)

    ledger = tmp_path / "my.ledger"
    ledger.write_text("content\n")
    for _ in range(KEEP_BACKUPS + 2):
        backup_file(ledger)

    assert len(backups_of(tmp_path, "my.ledger.header")) == 1
