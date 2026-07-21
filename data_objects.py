from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4
import os
from pathlib import Path
from datetime import date


@dataclass(frozen=True)
class FileState:
    source_path: Path
    relative_source_path: Path  # path relative to the directory being ingested.
    current_path: Path
    base_name: str
    uri: str = field(default_factory=lambda: str(uuid4()))
    current_hash: Optional[str] = None
    metadata: Optional[dict] = None
    sidecar_path: Optional[Path] = None
    created_date: Optional[date] = None
    status: str = "NEW"


def create_filestate(
    source_path: Path, relative_source_path: Path = Path(".")
) -> FileState:
    file_name = os.path.basename(source_path)
    return FileState(
        source_path=source_path,
        relative_source_path=relative_source_path,
        current_path=source_path,
        base_name=file_name,
        status="NEW",
    )


@dataclass
class IngestReport:
    ingested: list[Path] = field(default_factory=list)
    quarantined: list[Path] = field(default_factory=list)
    errored: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.quarantined and not self.errored
