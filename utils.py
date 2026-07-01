import os
import puremagic
from data_objects import FileState
import subprocess

def validate_file(file_state: FileState) -> bool:
    file_path = file_state.current_path
    magic = puremagic.from_file(file_path).lstrip(".")
    extension = file_path.rsplit(".", 1)[-1].lstrip(".")
    return magic == extension


def run_rsync(source: str, destination: str, dry_run: bool = False) -> tuple[bool, str]:
    flags = ["-ca", "--itemize-changes"]  # TODO: check with my earlier version
    if dry_run:
        flags.append("-n")

    cmd = ["rsync"] + flags + [source, destination]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf8")
        return (res.returncode == 0, res.stdout)
    except Exception as e:
        return (False, str(e))

def create_filestate(source_path: str)->FileState:
    file_name = os.path.basename(source_path)
    return FileState(source_path, current_path=source_path, base_name=file_name, status="NEW")
