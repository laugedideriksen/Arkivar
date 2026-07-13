from data_objects import FileState
from log_writer import LogWriter
from utils import (
    run_rsync,
    validate_file,
    run_exiftool,
    dc_template,
    metadata_map,
    type_specific_metadata,
)
import os
import json
from pathlib import Path
from pprint import pprint


def stage(data_source: FileState, logger: LogWriter, dest_path: Path) -> FileState:
    """Move file to staging/."""
    filename = os.path.basename(data_source.source_path)
    target_path = os.path.join(dest_path, filename)

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
    target_path = os.path.join(quarantine_dir, filename)

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

    # TODO: Extract metadata
    success, output = run_exiftool(data_source.current_path)

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
    # TODO: TEST!!! And figure out how to log this action.
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
            path_before=str(metadata_file),
            path_after=str(metadata_file),
        )

        print("metadata.json has been cleaned")
    except Exception as e:
        raise e


def consolidate_metadata(data_source: FileState, logger: LogWriter) -> FileState:
    """Consolidate extracted metadata and project metadata"""
    if data_source.status != "METADATA_EXTRACTED":
        return data_source

    object_path = Path(data_source.current_path)
    project_path = object_path.parent.parent
    metadata_file = project_path / "metadata.json"
    with open(metadata_file, "r") as f:
        project_metadata = json.load(f)
    object_metadata = data_source.metadata
    filetype_metadata = type_specific_metadata(object_path.suffix)

    # Create metadata template for data_source based on project metadata, and exif fields specific to its filetype
    for k, v in filetype_metadata.items():
        object_metadata_template = project_metadata | {k: v}

    # TODO: iterate over object_metadata_template and replace existing values with values from data_source.metadata, if present. Use metadata_map to translate naming conventions.
    # TODO: Might make more sense to insert values to filetype metadata and only then replace in/add to object metadata?

    pprint(object_metadata_template, sort_dicts=False)
    return data_source


# def write_sidecar(data_source: FileState, logger: LogWriter) -> FileState:
#    """Reformat extracted metadata, combine it with project metadata and write it to a sidecar file."""
#    pass
#
#
# def organise(data_source: FileState, logger: LogWriter) -> FileState:
#    """Move files to bag folders"""
#    pass


def finalise(logger: LogWriter) -> None:
    # TODO: calculate checksum of changelog.
    log_file = logger.log_file
    logger._calculate_sha256(os.path.abspath(log_file))
    pass
