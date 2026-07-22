import csv
import os
from datetime import datetime, date
from hashlib import sha256
from data_objects import FileState
from dataclasses import replace
from pathlib import Path


class LogWriter:
    def __init__(
        self,
        log_file: Path = Path("changelog.csv"),
        dt_format: str = "%Y%m%d-%H:%M:%S.%f",
    ) -> None:
        self.log_file = log_file
        self.dt_format = dt_format
        # TODO: Is ensure init necessary?
        # self._ensure_init()

    def _calculate_sha256(self, file_path: Path) -> str:
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        h = sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                h.update(byte_block)
            return h.hexdigest()

    def change_state(
        self,
        state: "FileState",
        action: str,
        path_after_action: Path,
        note: str = "",
        meta_data: dict | None = None,
        sidecar_path: Path | None = None,
        created_date: date | None = None,
    ) -> "FileState":
        timestamp = datetime.now().strftime(self.dt_format)
        path_before_action = state.current_path
        hash_before_action = state.current_hash or "N/A"
        hash_after_action = self._calculate_sha256(path_after_action)

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    timestamp,
                    action,
                    path_before_action,
                    path_after_action,
                    hash_before_action,
                    hash_after_action,
                    note,
                ]
            )
            f.flush()

        status_map = {
            "INGEST_FILE": "INGESTED",
            "VALIDATE_FILETYPE": "VALIDATED",
            "VALIDATION_FAILED": "VALIDATION_FAILED",
            "QUARANTINE_FILE": "QUARANTINED",
            "ERROR": "ERROR",
            "MOVE_FILE": "FILE_MOVED",
            "METADATA_EXTRACT": "METADATA_EXTRACTED",
            "STAGE_FILE": "FILE_STAGED",
            "CREATE_SIDECAR": "SIDECAR_CREATED",
        }
        new_status = status_map.get(action, state.status)
        updates = {
            "current_path": path_after_action,
            "current_hash": hash_after_action,
            "status": new_status,
        }
        if meta_data is not None:
            updates["metadata"] = meta_data
        if sidecar_path is not None:
            updates["sidecar_path"] = sidecar_path
        if created_date is not None:
            updates["created_date"] = created_date

        return replace(state, **updates)

    def _write_log_entry(
        self,
        action_type: str,
        path_before: Path | None,
        path_after: Path,
        hash_before: str | None = None,
        new_hash: str | None = None,
        note: str = "",
    ) -> None:

        #        self._ensure_init()

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)

            if new_hash is None and path_after.is_file():
                new_hash = self._calculate_sha256(path_after)

            writer.writerow(
                [
                    datetime.now().strftime(self.dt_format),
                    action_type,
                    str(path_before) if path_before is not None else "N/A",
                    path_after,
                    str(hash_before) if hash_before is not None else "N/A",
                    new_hash,
                    note,
                ]
            )
            f.flush()
