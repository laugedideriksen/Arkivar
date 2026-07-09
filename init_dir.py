import os
import csv
import json
from log_writer import LogWriter
from utils import dc_template
from pathlib import Path


def _create_changelog(project_path: Path) -> LogWriter:
    log_file = project_path / "changelog.csv"

    if log_file.exists():
        logger = LogWriter(log_file)
        logger._write_log_entry(
            action_type="ERROR",
            path_before=str(log_file),
            path_after=os.path.abspath(log_file),
            new_hash="N/A",
            note="CREATE_CHANGELOG failed: changelog.csv already exists",
        )
        return logger

    with open(log_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "action_type",
                "file_path_before",
                "file_path_after",
                "hash_before",
                "hash_after",
                "note",
            ]
        )
        f.flush()

    print(f"changelog created at {log_file}")

    logger = LogWriter(log_file)

    logger._write_log_entry(
        action_type="CREATE_CHANGELOG",
        path_before="N/A",
        path_after=os.path.abspath(log_file),
        note="",
    )

    return logger


def _create_dirs(project_path: Path, logger: LogWriter) -> None:
    staging_dir = project_path / "staging"
    quarantine_dir = project_path / "quarantine"
    if staging_dir.exists():
        logger._write_log_entry(
            action_type="ERROR",
            path_before=str(staging_dir),
            path_after=os.path.abspath(staging_dir),
            new_hash="N/A",
            note="CREATE_STAGING_DIR failed: staging/ already exists",
        )
    else:
        os.makedirs(staging_dir, exist_ok=False)
        logger._write_log_entry(
            action_type="CREATE_STAGING_DIR",
            path_before="N/A",
            path_after=os.path.abspath(staging_dir),
            new_hash="N/A",
            note="",
        )
        print("staging/ created.")

    if quarantine_dir.exists():
        logger._write_log_entry(
            action_type="ERROR",
            path_before=str(quarantine_dir),
            path_after=os.path.abspath(quarantine_dir),
            new_hash="N/A",
            note="CREATE_QUARANTINE_DIR failed: quarantine/ already exists",
        )
    else:
        os.makedirs(quarantine_dir, exist_ok=False)
        print("quarantine/ created.")
        logger._write_log_entry(
            action_type="CREATE_QUARANTINE_DIR",
            path_before="N/A",
            new_hash="N/A",
            path_after=os.path.abspath(staging_dir),
            note="",
        )


def _create_metadata_template(project_path: Path, logger: LogWriter):
    metadata_temp = project_path / "metadata.json"
    dc_dict = dc_template()

    if metadata_temp.exists():
        logger._write_log_entry(
            action_type="ERROR",
            path_before=str(metadata_temp),
            path_after=os.path.abspath(metadata_temp),
            note="CREATE_METADATA_TEMPLATE failed: metadata.json already exists",
        )
    else:
        with open(metadata_temp, "w") as f:
            json.dump(dc_dict, f, sort_keys=False, indent=4, ensure_ascii=False)

        print("metadata.json created")
        logger._write_log_entry(
            action_type="CREATE_METADATA_TEMPLATE",
            path_before=str(metadata_temp),
            path_after=os.path.abspath(metadata_temp),
            note="",
        )


def init_dir(project_path: str | Path):
    project_path = Path(project_path).resolve()

    if not project_path.exists():
        os.mkdir(project_path)
        print(f"project directory initiated at {project_path}")
    elif (
        os.path.isdir(project_path / "staging")
        and os.path.isdir(project_path / "quarantine")
        and os.path.isfile(project_path / "changelog.csv")
        and os.path.isfile(project_path / "metadata.json")
    ):
        print(f"{project_path} has already been initialised.")
        return

    logger = _create_changelog(project_path)
    _create_dirs(project_path, logger)
    _create_metadata_template(project_path, logger)

    if (
        os.path.isdir(project_path / "staging")
        and os.path.isdir(project_path / "quarantine")
        and os.path.isfile(project_path / "changelog.csv")
        and os.path.isfile(project_path / "metadata.json")
    ):
        print(f"{project_path} has been initialised.")
