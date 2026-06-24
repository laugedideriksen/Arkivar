from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class FileState:
    source_path: str
    current_path: str
    current_hash: Optional[str]
    base_name: str
    metadata: Optional[dict]
    status: str = "NEW"
