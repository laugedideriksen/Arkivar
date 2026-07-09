import csv
import os
from datetime import datetime
from hashlib import sha256
from data_objects import FileState
from dataclasses import replace
from pathlib import Path


class LogWriter:
    def __init__(
        self,
        log_file: str | Path = "changelog.csv",
        dt_format: str = "%Y%m%d-%H:%M:%S.%f",
    ) -> None:
        self.log_file = log_file
        self.dt_format = dt_format
        # TODO: Is ensure init necessary?
        # self._ensure_init()

    def _ensure_init(self):
        if not (
            os.path.isdir("staging")
            and os.path.isdir("quarantine")
            and os.path.isfile("changelog.csv")
            and os.path.isfile("metadata.json")
        ):
            raise Exception(
                f"{os.getcwd()} doesn't seem to be initialised. Please run arkivar init."
            )

    def _calculate_sha256(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256().update(byte_block)
            return sha256().hexdigest()

    def change_state(
        self,
        state: "FileState",
        action: str,
        path_after_action: str,
        note: str = "",
        meta_data: dict | None = None,
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
            "QUARANTINE_FILE": "QUARANTINED",
            "ERROR": "ERROR",
            "MOVE": "MOVED",
            "METADATA_EXTRACT": "METADATA_EXTRACTED",
            "STAGE_FILE": "FILE_STAGED",
            "CREATE_SIDECAR": "SIDECAR_CREATED",
        }
        new_status = status_map.get(action, state.status)

        if meta_data:
            return replace(
                state,
                current_path=path_after_action,
                current_hash=hash_after_action,
                status=new_status,
                metadata=meta_data,
            )

        return replace(
            state,
            current_path=path_after_action,
            current_hash=hash_after_action,
            status=new_status,
        )

    def _write_log_entry(
        self,
        action_type: str,
        path_before: str,
        path_after: str,
        hash_before: str = "N/A",
        new_hash: str = "",
        note: str = "",
    ) -> None:

        #        self._ensure_init()

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)

            if not new_hash == "N/A":
                new_hash = self._calculate_sha256(path_after)

            writer.writerow(
                [
                    datetime.now().strftime(self.dt_format),
                    action_type,
                    path_before,
                    path_after,
                    hash_before,
                    new_hash,
                    note,
                ]
            )
            f.flush()
