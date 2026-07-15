from data_objects import FileState
from log_writer import LogWriter
from utils import (
    run_rsync,
    validate_file,
    run_exiftool,
    dc_template,
)
from metadata import (
        exiftool_fields_for,
        build_sidecar,
        write_sidecar,
        validate_sidecar,
        )
import os
import json
from pathlib import Path


def stage(data_source: FileState, logger: LogWriter, staging_dir: Path) -> FileState:
    """Move file to staging/."""
    target_dir = staging_dir / data_source.relative_source_path
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / data_source.base_name

    success, msg = run_rsync(data_source.source_path, target_path)

    if success:
        return logger.change_state(
            data_source, "STAGE_FILE", target_path, note=f"Rsync OK: {msg}"
        )
    else:
        return logger.change_state(
            data_source, "ERROR", data_source.current_path, note=f"Rsync FAIL: {msg}"
        )


def validate(data_source: FileState, logger: LogWriter) -> FileState:
    """Validate that magic number matches file extension."""
    if data_source.status == "ERROR":
        return data_source

    if validate_file(data_source):
        return logger.change_state(
            data_source,
            "VALIDATE_FILETYPE",
            data_source.current_path,
            note="Signature match",
        )
    else:
        return logger.change_state(
            data_source,
            "VALIDATION_FAILED",
            data_source.current_path,
            note="FILE VALIDATION FAILED",
        )


def quarantine(
    data_source: FileState, logger: LogWriter, quarantine_dir: Path
) -> FileState:
    """Move files that fail check to quarantine/"""
    if data_source.status != "VALIDATION_FAILED":
        return data_source

    filename = os.path.basename(data_source.current_path)
    target_path = quarantine_dir / filename

    try:
        os.rename(data_source.current_path, target_path)
        return logger.change_state(
            data_source,
            "QUARANTINE_FILE",
            target_path,
            note="Moved due to validation error",
        )
    except Exception as e:
        return logger.change_state(
            data_source,
            "ERROR",
            data_source.current_path,
            note=f"Quarantine move failed: {e}",
        )


def extract_metadata(data_source: FileState, logger: LogWriter) -> FileState:
    """Extract metadata from file and add it to FileState"""
    if data_source.status != "VALIDATED":
        return data_source

    suffix = data_source.current_path.suffix.lower()
    try:
        fields = exiftool_fields_for(suffix)
    except ValueError as e:
        return logger.change_state(data_source, "ERROR", data_source.current_path, note=str(e))

    success, output = run_exiftool(data_source.current_path, fields)

    if success and output != {}:
        return logger.change_state(
            data_source,
            "METADATA_EXTRACT",
            data_source.current_path,
            meta_data=output,
        )
    elif success and output == {}:
        return logger.change_state(
            data_source,
            "METADATA_EXTRACT",
            data_source.current_path,
            meta_data=output,
            note="No metadata to extract",
        )
    else:
        return logger.change_state(
            data_source,
            "ERROR",
            data_source.current_path,
            note=f"Exiftool failed: {output}",
        )


def clean_project_metadata(project_path: Path, logger: LogWriter) -> None:
    """Replaces any unaltered field in metadata.json with an empty list"""
    try:
        metadata_file = project_path / "metadata.json"
        dc_temp = dc_template()
        with open(metadata_file, "r") as f:
            project_metadata = json.load(f)

        for key, value in project_metadata.items():
            if value == dc_temp[key]:
                project_metadata[key] = []

        with open(metadata_file, "w") as f:
            json.dump(
                project_metadata, f, sort_keys=False, indent=4, ensure_ascii=False
            )

        logger._write_log_entry(
            action_type="CLEAN_PROJECT_METADATA",
            path_before=metadata_file,
            path_after=metadata_file,
        )

        print("metadata.json has been cleaned")
    except Exception as e:
        raise e

def create_sidecar_file(data_source: FileState, logger: LogWriter, project_path: Path) -> FileState:
    suffix = data_source.current_path.suffix
    exif_data = data_source.metadata
    metadata_file = project_path / "metadata.json"
    with open(metadata_file, "r") as f:
        project_metadata = json.load(f)
    sidecar_dict = build_sidecar(project_metadata, exif_data, suffix)
    data_source = write_sidecar(data_source, logger, sidecar_dict)
    return data_source

def organise(project_path: Path, data_source: FileState, logger: LogWriter) -> FileState:
   """Move files to bag folders"""
   data_dir = project_path / "data"
   target_dir = data_dir / data_source.relative_source_path
   target_dir.mkdir(parents=True, exist_ok=True)
   file_target = target_dir / data_source.base_name
   sidecar_target = target_dir / data_source.sidecar_path.name

   staged_file_path = data_source.current_path
   staged_sidecar_path = data_source.sidecar_path
   
   success, msg = run_rsync(data_source.current_path, file_target)

   if success:
       sidecar_success, sidecar_msg = run_rsync(data_source.sidecar_path, sidecar_target)
       if sidecar_success:
           staged_file_path.unlink()
           staged_sidecar_path.unlink()
           logger._write_log_entry(
                   action_type="SIDECAR_MOVED",
                   path_before=data_source.sidecar_path,
                   path_after=sidecar_target,
                   note=f"Rsync OK: {sidecar_msg}"
                   )
           return logger.change_state(
                   data_source, "MOVE_FILE", file_target, sidecar_path=sidecar_target, note=f"Rsync OK: {msg}"
                   )
       else:
           return logger.change_state(
                   data_source, "ERROR", data_source.current_path, note=f"Rsync FAILED on sidecar: {sidecar_msg}"
                   )
   else:
       return logger.change_state(
               data_source, "ERROR", data_source.current_path, note=f"Rsync FAIL: {msg}"
               )

def finalise(logger: LogWriter) -> None:
    # TODO: calculate checksum of changelog.
    log_file = logger.log_file
    logger._calculate_sha256(log_file.resolve())

    logger._write_log_entry(
            action_type="CLOSE_CHANGELOG",
            path_before=log_file,
            path_after=log_file,
            note="Ingestion finished. To verify new changelog checksum, first remove this row.")
    pass
