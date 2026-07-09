import os
import arkivar
import log_writer
from data_objects import FileState
from utils import create_filestate


def _ingest_file(source_path: str, destination_path: str) -> None:
    data_source = create_filestate(source_path)
    logger = log_writer.LogWriter()

    state = create_filestate(source_path)
    state = arkivar.stage(state, logger, destination_path)
    state = arkivar.validate(state, logger)
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


def main(source_path: str, destination_path: str):
    if os.path.isfile(source_path):
        _ingest_file(source_path, destination_path)
        pass
