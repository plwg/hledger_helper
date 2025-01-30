import shutil


def backup_file(path):
    backup_path = "".join([str(path), ".bak"])

    shutil.copy(path, backup_path)

    return backup_path
