import os
import arkivar
import log_writer
from data_objects import FileState
from utils import create_filestate
from init_dir import init_dir
from pathlib import Path


def _ingest_file(
    source_path: str, project_path: Path, logger: log_writer.LogWriter
) -> None:
    data_source = create_filestate(source_path)
    staging_dir = project_path / "staging"
    quarantine_dir = project_path / "quarantine"

    if data_source.status != "ERROR":
        data_source = arkivar.stage(data_source, logger, staging_dir)
    if data_source.status != "ERROR":
        data_source = arkivar.validate(data_source, logger)
        if data_source.status == "VALIDATION_FAILED":
            data_source = arkivar.quarantine(data_source, logger, quarantine_dir)
    if data_source.status == "VALIDATED":
        data_source = arkivar.extract_metadata(data_source, logger)

    # state = arkivar.consolidate_metadata(state, logger)
    # state = arkivar.write_sidecar(state, logger)
    # state = arkivar.organise(state, logger)
    # arkivar.finalise(logger)

    pass


def ingest_directory(source_path: str) -> None:
    # walk tree and add all files to data_sources
    data_sources = []

    for data_source in data_sources:
        pass


def ingest(source_path: str, project_path: str | Path):
    project_path = Path(project_path).resolve()
    logger = log_writer.LogWriter(project_path / "changelog.csv")
    # TODO: add ensure init

    print(project_path)
    arkivar.clean_project_metadata(project_path, logger)

    if not os.path.exists(source_path):
        print(f"INGEST FAILED: {source_path} does not exist")
    elif os.path.isfile(source_path):
        _ingest_file(source_path, project_path, logger)
        pass


if __name__ == "__main__":
    # init_dir("testdir")
    ingest("testfile.md", "testdir")
