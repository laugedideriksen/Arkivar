import os
import arkivar
from log_writer import LogWriter
from data_objects import FileState, create_filestate, IngestReport
from init_dir import init_dir, ensure_init
from pathlib import Path, PurePath


def _ingest_file(
    source: FileState | Path, project_path: Path, logger: LogWriter
) -> FileState:
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

    return data_source


def _classify(data_source: FileState, report: IngestReport) -> None:
    if data_source.status == "ERROR":
        report.errored.append((data_source.current_path, data_source.status))
    elif data_source.status == "QUARANTINED":
        report.quarantined.append(data_source.current_path)
    else:
        report.ingested.append(data_source.current_path)


def _ingest_directory(
    source_path: str | Path, project_path: Path, logger: LogWriter
) -> IngestReport:
    ingestion_root = Path(source_path).resolve()
    report = IngestReport()

    for file_path in ingestion_root.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(ingestion_root).parent
            data_source = create_filestate(file_path, relative_path)
            data_source = _ingest_file(data_source, project_path, logger)
            _classify(data_source, report)
    return report


def ingest(source_path: str | Path, project_path: str | Path) -> IngestReport:
    source_path = Path(source_path).resolve()
    project_path = Path(project_path).resolve()
    logger = LogWriter(project_path / "changelog.csv")
    report = IngestReport()

    if not os.path.exists(source_path):
        print(f"INGEST FAILED: {source_path} does not exist")
        return report
    elif not ensure_init(project_path):
        return report

    arkivar.clean_project_metadata(project_path, logger)

    if os.path.isfile(source_path):
        data_source = _ingest_file(source_path, project_path, logger)
        _classify(data_source, report)
    elif os.path.isdir(source_path):
        report = _ingest_directory(source_path, project_path, logger)

    arkivar.finalise(logger)

    if report.clean:
        print(f"Ingest complete: {len(report.ingested)} files organised, 0 issues.")
    else:
        print(
            f"Ingest completed with issues — {len(report.quarantined)} quarantined, {len(report.errored)} errored."
        )

    return report


def requeue_quarantine(project_path: Path | str) -> IngestReport:
    """Re-attempt validation for every file in quarantine/, and run the rest of the pipeline for any that now pass. Files that still fail are left untouched."""
    project_path = Path(project_path).resolve()

    ensure_init(project_path)

    logger = LogWriter(project_path / "changelog.csv")
    quarantine_dir = project_path / "quarantine"
    report = IngestReport()

    for file_path in quarantine_dir.rglob("*"):
        if not file_path.is_file():
            continue

        relative_source_path = file_path.relative_to(quarantine_dir).parent
        data_source = create_filestate(file_path, relative_source_path)

        data_source = arkivar.validate(data_source, logger)
        if data_source.status != "VALIDATED":
            report.errored.append((file_path, "still fails validation"))
            continue

        data_source = arkivar.extract_metadata(data_source, logger)
        if data_source.status == "METADATA_EXTRACTED":
            data_source = arkivar.create_sidecar_file(data_source, logger, project_path)
        if data_source.status == "SIDECAR_CREATED":
            data_source = arkivar.organise(project_path, data_source, logger)

        if data_source.status == "ERROR":
            report.errored.append((file_path, "failed after re-validation"))
        else:
            report.ingested.append(file_path)

    return report


def bag_project(
    project_path: str | Path,
    output_path: str | Path | None = None,
    cleanup: str = "none",
) -> Path:
    project_path = Path(project_path)
    if output_path:
        output_path = Path(output_path)

    bag_path = arkivar.bag_project(project_path, output_path, cleanup=cleanup)
    print(f"Project bagged at {bag_path}")

    return bag_path


if __name__ == "__main__":
    # init_dir("testdir")
    # ingest("/home/ld/Documents/Coding/ongoingProjects/OnsetExtractor/data", "testdir")
    # requeue_quarantine("testdir")
    bag_project("testdir", cleanup="full")
