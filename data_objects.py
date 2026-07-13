from dataclasses import dataclass, replace, field
from typing import Optional
from uuid import uuid4
import os
from pathlib import Path


@dataclass(frozen=True)
class FileState:
    source_path: str|Path
    current_path: str|Path
    base_name: str
    uri: str = field(default_factory=lambda: str(uuid4()))
    current_hash: Optional[str] = None
    metadata: Optional[dict] = None
    sidecar_path: Optional[Path] = None
    status: str = "NEW"


def create_filestate(source_path: str) -> FileState:
    file_name = os.path.basename(source_path)
    return FileState(
        source_path, current_path=source_path, base_name=file_name, status="NEW"
    )
