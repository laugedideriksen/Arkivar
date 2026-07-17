import os
import arkivar
from log_writer import LogWriter
from data_objects import FileState, create_filestate
from init_dir import init_dir
from pathlib import Path, PurePath
import bagit


def _ingest_file(
    source: FileState | Path, project_path: Path, logger: LogWriter
) -> None:
    if isinstance(source, PurePath):
        data_source = create_filestate(source)
    else:
        data_source = source

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

    if data_source.status == "METADATA_EXTRACTED":
        data_source = arkivar.create_sidecar_file(data_source, logger, project_path)

    if data_source.status == "SIDECAR_CREATED":
        data_source = arkivar.organise(project_path, data_source, logger)


def _ingest_directory(
    source_path: str | Path, project_path: Path, logger: LogWriter
) -> None:
    ingestion_root = Path(source_path).resolve()
    for file_path in ingestion_root.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(ingestion_root).parent
            data_source = create_filestate(file_path, relative_path)
            _ingest_file(data_source, project_path, logger)


def ingest(source_path: str | Path, project_path: str | Path) -> None:
    source_path = Path(source_path).resolve()
    project_path = Path(project_path).resolve()
    logger = LogWriter(project_path / "changelog.csv")
    # TODO: add ensure init

    if not os.path.exists(source_path):
        print(f"INGEST FAILED: {source_path} does not exist")
        return

    if not (
        os.path.isdir(project_path / "staging")
        and os.path.isdir(project_path / "quarantine")
        and os.path.isdir(project_path / "data")
        and os.path.isfile(project_path / "changelog.csv")
        and os.path.isfile(project_path / "metadata.json")
    ):
        raise Exception(
            f"{project_path} doesn't seem to be initialised. Please run arkivar init {project_path}."
        )

    arkivar.clean_project_metadata(project_path, logger)

    if os.path.isfile(source_path):
        _ingest_file(source_path, project_path, logger)
    elif os.path.isdir(source_path):
        _ingest_directory(source_path, project_path, logger)

    arkivar.finalise(logger)


def reevaluate_quarantine(project_path: Path, logger: LogWriter):
    # TODO: reevaluate all files in quarantine. To be run manually, after potentially renaming, etc.
    pass


def bag_project(project_path: str | Path) -> None:
    project_path = Path(project_path)
    bagit.make_bag(project_path, checksums=["sha256"])


if __name__ == "__main__":
    # init_dir("testdir")
    ingest("/home/ld/Documents/Coding/ongoingProjects/OnsetExtractor/data", "testdir")
    # bag_project("testdir")
