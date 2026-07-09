import os
import arkivar
import log_writer
from data_objects import FileState
from utils import create_filestate
from init_dir import init_dir
from pathlib import Path


def _ingest_file(source_path: str, project_path: Path) -> None:
    data_source = create_filestate(source_path)
    staging_dir = project_path / "staging"
    quarantine_dir = project_path / "quarantine"
    logger = log_writer.LogWriter(project_path / "changelog.csv")

    state = create_filestate(source_path)
    if state.status != "ERROR":
        state = arkivar.stage(state, logger, staging_dir)
    if state.status != "ERROR":
        state = arkivar.validate(state, logger)
        if state.status == "VALIDATION_FAILED":
            state = arkivar.quarantine(state, logger, quarantine_dir)
    if state.status == "VALIDATED":
        state = arkivar.extract_metadata(state, logger)

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
    # TODO: add ensure init
    if not os.path.exists(source_path):
        print(f'INGEST FAILED: {source_path} does not exist')
    elif os.path.isfile(source_path):
        _ingest_file(source_path, project_path)
        pass

if __name__ == "__main__":
    #init_dir("testdir")
    ingest("testfile.md", "testdir")
