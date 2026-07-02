import os
import json
import puremagic
from data_objects import FileState
import subprocess
from typing import Any

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

def run_exiftool(file_path)->tuple[bool, Any]:
    cmd = ['exiftool', '-j', '-n', '-G', '-api', 'LargeFileSupport=1', file_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf8")
        data = json.loads(res.stdout)
        return (res.returncode == 0, data[0]) if data else (res.returncode == 0, {})
    except subprocess.CalledProcessError as e:
        return (False, str(e))


def create_filestate(source_path: str)->FileState:
    file_name = os.path.basename(source_path)
    return FileState(source_path, current_path=source_path, base_name=file_name, status="NEW")
