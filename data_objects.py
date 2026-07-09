from dataclasses import dataclass, replace
from typing import Optional
import os


@dataclass(frozen=True)
class FileState:
    source_path: str
    current_path: str
    base_name: str
    current_hash: Optional[str] = None
    metadata: Optional[dict] = None
    status: str = "NEW"
