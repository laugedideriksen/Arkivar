import json
from datetime import date
import puremagic
from data_objects import FileState
import subprocess
from typing import Any, Optional, Tuple
from pathlib import Path


def validate_file(file_state: FileState) -> bool:
    file_path = str(file_state.current_path)
    magic = puremagic.from_file(file_path).lstrip(".")
    extension = file_path.rsplit(".", 1)[-1].lstrip(".")

    match extension:  # Some markdown files have are identified as txt files. This makes sure they don't fail to validate
        case "md":
            extension = "txt"
        case "ascii":
            extension = "txt"
        case _:
            pass

    return magic.lower() == extension.lower()


def run_rsync(
    source: Path, destination: Path, dry_run: bool = False
) -> tuple[bool, str]:
    flags = ["-ca", "--itemize-changes"]  # TODO: check with my earlier version
    if dry_run:
        flags.append("-n")

    cmd = ["rsync"] + flags + [str(source), str(destination)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf8")
        message = " | ".join(line for line in res.stdout.strip().splitlines() if line)
        return (res.returncode == 0, message)
    except Exception as e:
        return (False, str(e))


def run_exiftool(
    file_path: Path, fields: Optional[list[str]] = None
) -> tuple[bool, Any]:
    cmd = ["exiftool", "-j", "-n", "-G", "-s", "-api", "LargeFileSupport=1"]
    if fields:
        cmd += [f"-{field}" for field in fields]
    cmd.append(str(file_path))
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding="utf8"
        )
        data = json.loads(res.stdout)
        return (res.returncode == 0, data[0]) if data else (res.returncode == 0, {})
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        json.JSONDecodeError,
    ) as e:
        return (False, str(e))


def resolve_created_date(
    sidecar: dict, staged_path: Path
) -> Tuple[Optional[date], str]:
    for raw_value in sidecar["dublin_core"].get("dates", []):
        if not raw_value:
            continue
        try:
            return date.fromisoformat(raw_value), "embedded metadata"
        except ValueError:
            continue  # e.g. a bare "2019" from an ID3 Year tag — not day-precise enough

    try:
        return date.fromtimestamp(
            staged_path.stat().st_mtime
        ), "filesystem mtime (low confidence)"
    except OSError:
        pass

    return None, "unresolved"
