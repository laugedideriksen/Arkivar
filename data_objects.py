from dataclasses import dataclass, replace, field
from typing import Optional, Callable, Any
from uuid import uuid4
import os
from pathlib import Path
from enum import Enum
from rdflib import Namespace


@dataclass(frozen=True)
class FileState:
    source_path: Path
    relative_source_path: Path # path relative to the directory being ingested.
    current_path: Path
    base_name: str
    uri: str = field(default_factory=lambda: str(uuid4()))
    current_hash: Optional[str] = None
    metadata: Optional[dict] = None
    sidecar_path: Optional[Path] = None
    status: str = "NEW"


def create_filestate(source_path: Path, relative_source_path: Path = Path(".")) -> FileState:
    source_path = source_path
    file_name = os.path.basename(source_path)
    return FileState(
        source_path=source_path, relative_source_path=relative_source_path, current_path=source_path, base_name=file_name, status="NEW"
    )

class Target(Enum):
    DUBLIN_CORE = "dublin_core"
    TECHNICAL = "technical"

@dataclass(frozen=True)
class FieldDefinition:
    exif_field: str                                # exiftool's field name, e.g. "Date/Time Original"
    target: Target
    key: str                                        # DC key or technical predicate local name
    namespace: Optional[Namespace] = None           # only used when target is TECHNICAL
    transform: Optional[Callable[[str], Any]] = None  # optional value normalizer
