from data_objects import FileState
from log_writer import LogWriter
from utils import run_rsync, validate_file
import os


def stage(data_source: FileState, logger: LogWriter, dest_path: str) -> FileState:
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
            data_source, "ERROR", data_source.current_path, note="Signature mismatch"
        )

def quarantine(
    data_source: FileState, logger: LogWriter, quarantine_dir: str
) -> FileState:
    """Move files that fail check to quarantine/"""
    if data_source.status != "ERROR":
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

    extracted_metadata = {}

    return logger.change_state(
        data_source,
        "METADATA_EXTRACT",
        data_source.current_path,
        meta_data=extracted_metadata,
    )


def write_sidecar(data_source: FileState, logger: LogWriter) -> FileState:
    """Reformat extracted metadata, ombine it with project metadata and write it to a sidecar file."""
    pass


def organise(data_source: FileState, logger: LogWriter) -> FileState:
    """Move files to bag folders"""
    pass

def finalise(logger: LogWriter)->None:
    #TODO: calculate checksum of changelog.
    log_file = logger.log_file
    logger._calculate_sha256(os.path.abspath(log_file))
    pass
