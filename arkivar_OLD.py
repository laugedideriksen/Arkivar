import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, replace
from typing import Optional
import csv
import json
from hashlib import sha256
import puremagic
import bagit


@dataclass(frozen=True)
class FileState:
    source_path: str
    current_path: str
    current_hash: Optional[str]
    base_name: str
    status: str = "NEW"


# CHANGELOG
class LogWriter:
    def __init__(
        self, log_file: str = "changelog.csv", dt_format: str = "%Y%m%d-%H:%M:%S.%f"
    ) -> None:
        self.log_file = log_file
        self.dt_format = dt_format
        self._ensure_init()

    def _ensure_init(self):
        if (
            not os.path.isdir("staging")
            and not os.path.isdir("quarantine")
            and not os.path.isfile("changelog.csv")
            and not os.path.isfile("metadata.json")
        ):
            raise Exception(
                f"{os.getcwd()} doesn't seem to be initialised. Please run init command."
            )

    def _fail_if_file_exists(self, file_path, name, action) -> bool:
        # TODO: this might want to go to a utility class.
        if os.path.isfile(file_path):
            self._write_csv(
                action,
                os.path.abspath(file_path),
                os.path.abspath(file_path),
                self._calculate_sha256(os.path.abspath(file_path)),
                f"ABORTED: {name} already exists.",
            )
            return False
        return True

    def _calculate_sha256(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256().update(byte_block)
            return sha256().hexdigest()

    def change_state(
        self, state: "FileState", action: str, path_after_action: str, note: str = ""
    ) -> "FileState":
        timestamp = datetime.now().strftime(self.dt_format)
        path_before_action = state.current_path
        hash_before_action = state.current_hash or "N/A"
        hash_after_action = self._calculate_sha256(path_after_action)

        permitted_actions = [
            "CREATE_CHANGELOG",
            "CREATE_DUBLIN_CORE_JSON",
            "INGEST_FILE",
            "VALIDATE_FILETYPE",
            "COMPUTE_CHECKSUM",
            "EXTRACT_METADATA",
            "NORMALISE_FILENAME",
            "NORMALISE_METADATA",
            "CREATE_DIRECTORY",
            "MOVE",
            "QUARANTINE_FILE",
            "CREATE_BAG",
            "VALIDATE_BAG",
            "ERROR",
        ]
        if action not in permitted_actions:
            note = f"{action} is not a valid action type."
            action = "ERROR"

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

        match action:
            case "ERROR":
                new_status = "ERROR"
            case "INGEST FILE":
                new_status = "INGESTED"
            case "VALIDATE_FILE":
                new_status = "VALIDATED"
            case "QUARANTINE_FILE":
                new_status = "QUARANTINED"
            case _:
                new_status = state.status

        return replace(
            state,
            current_path=path_after_action,
            current_hash=hash_after_action,
            status=new_status,
        )

    # Create and write to CSV
    def _create_csv(self):
        # TODO: move to init
        if not self._fail_if_file_exists(
            self.log_file, "changelog", "CREATE_CHANGELOG"
        ):
            return

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "action_type",
                    "file_path_before",
                    "file_path_after",
                    "hash_before",
                    "hash_after",
                    "note",
                ]
            )
            f.flush()

            writer.writerow(
                [
                    datetime.now().strftime(self.dt_format),
                    "CREATE_CHANGELOG",
                    "N/A",
                    os.path.abspath(self.log_file),
                    "N/A",
                    self._calculate_sha256(os.path.abspath(self.log_file)),
                    "",
                ]
            )
            f.flush()

    def _write_csv(
        self,
        action_type: str,
        path_before: str,
        path_after: str,
        hash_before: str = "N/A",
        new_hash: str = "",
        note: str = "",
    ) -> None:
        # TODO: Remove once superfluous
        csv_exists = os.path.isfile(self.log_file)
        if not csv_exists:
            self._create_csv()

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)

            permitted_actions = [
                "CREATE_CHANGELOG",
                "CREATE_DUBLIN_CORE_JSON",
                "INGEST_FILE",
                "VALIDATE_FILETYPE",
                "COMPUTE_CHECKSUM",
                "EXTRACT_METADATA",
                "NORMALISE_FILENAME",
                "NORMALISE_METADATA",
                "CREATE_DIRECTORY",
                "MOVE",
                "QUARANTINE_FILE",
                "CREATE_BAG",
                "VALIDATE_BAG",
                "ERROR",
            ]
            if action_type not in permitted_actions:
                note = f"{action_type} is not a valid action type."
                action_type = "ERROR"

            if new_hash:
                pass
            else:
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

    def log_action(
        self, context: FileState, action: str, new_path: str, note: str = ""
    ):
        hash_before = context.current_hash or "N/A"
        new_hash = self._calculate_sha256(new_path)

        self._write_csv(
            action, context.current_path, new_path, hash_before, new_hash, note
        )

        return replace(context, current_path=new_path, current_hash=new_hash)


# ERROR REPORTING


# Project Initiation
class ProjectInitiator:
    def __init__(
        self,
        project_directory: str = os.getcwd(),
        project_name: str = "ProjectName",
        start_date: str = "YYYYmmdd",
    ) -> None:
        self.project_directory = project_directory
        self.project_name = project_name
        self.start_date = start_date
        self.metadata_json = "metadata.json"

    @property
    def project_directory(self):
        """The project_directory property."""
        return self._project_directory

    @project_directory.setter
    def project_directory(self, value):
        if not os.path.isdir(value):
            raise ValueError(f"{value} does not exist or is not a directory.")
        self._project_directory = value

    def _create_dublin_core_json(self) -> None:
        if not LogWriter(self.project_name)._fail_if_file_exists(
            f"{self.metadata_json}", "metadata JSON", "CREATE_DUBLIN_CORE_JSON"
        ):
            return

        dc_dict = dict(
            contributors=[
                "An entity responsible for making contributions to the resource."
            ],
            coverage=[
                "The spatial or temporal topic of the resource, spatial applicability of the resource, or jurisdiction under which the resource is relevant."
            ],
            creators=["An entity primarily responsible for making the resource."],
            dates=[
                f"A point or period of time associated with an event in the lifecycle of the resource. Probably {self.start_date}"
            ],
            descriptions=[
                "An account of the resource. Description may include but is not limited to: an abstract, a table of contents, a graphical representation, or a free-text account of the resource."
            ],
            formats=[
                "The file format, physical medium, or dimensions of the resource."
            ],
            identifiers=[
                f"An unambiguous reference to the resource within a given context. Recommended best practice is to identify the resource by means of a string conforming to a formal identification system. Probably {self.start_date + '_' + self.project_name}"
            ],
            languages=["A language of the resource."],
            publishers=["An entity responsible for making the resource available."],
            relations=[
                "A related resource. Recommended practice is to identify the related resource by means of a URI. If this is not possible or feasible, a string conforming to a formal identification system may be provided."
            ],
            rights=["Information about rights held in and over the resource."],
            sources=[
                "A related resource from which the described resource is derived."
            ],
            subject=[
                "The topic of the resource. Typically, the subject will be represented using keywords, key phrases, or classification codes. Recommended best practice is to use a controlled vocabulary."
            ],
            titles=["A name given to the resource."],
            types=["The nature or genre of the resource."],
        )

        with open("metadata.json", "w") as f:
            json.dump(dc_dict, f, sort_keys=False, indent=4, ensure_ascii=False)

        LogWriter(self.project_name)._write_csv(
            "CREATE_DUBLIN_CORE_JSON",
            "N/A",
            os.path.abspath(self.metadata_json),
            "N/A",
        )

    def init_directory(self):
        """Initiate archive directory by making a 'staging' and a 'quarantine' directory, creating a blank changelog csv if none exists, and creating a metadata JSON if none exists."""
        if (
            os.path.isdir("staging")
            and os.path.isdir("quarantine")
            and os.path.isfile("changelog.csv")
            and os.path.isfile("metadata.json")
        ):
            print(f"{os.getcwd()} has already been initialised.")
            return
        LogWriter(self.project_name)._create_csv()
        self._create_dublin_core_json()
        if not os.path.isdir("staging"):
            os.mkdir("staging")
            print("staging/ created.")
        if not os.path.isdir("quarantine"):
            os.mkdir("quarantine")
            print("quarantine/ created.")
        print(f"Directory initialised at {os.getcwd()}.")


# CREATE DATA SOURCE
class DataSource:
    """Create data source object."""

    def __init__(self, source_path: str):
        self.source_path = source_path

    @property
    def source_path(self):
        """The source_path property."""
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        if not os.path.exists(value):
            raise FileNotFoundError(f"{value} does not exist.")
        elif os.path.isfile(value):
            self.source_type = "file"
        elif os.path.isdir(value):
            self.source_type = "directory"
        self._source_path = os.path.abspath(value)


# INGESTION
class DataIngester:
    """This class takes a data source object as its input, and ingests all data from there using rsync."""

    def __init__(self, data_source, destination_directory: str = os.getcwd()):
        self.data_source = data_source
        self.path = self.data_source.source_path
        self.type = self.data_source.source_type
        self.destination_directory = destination_directory
        self.log_writer = LogWriter()
        self.staging_directory = destination_directory
        self.quarantine_directory = destination_directory

    @property
    def data_source(self):
        """The data_source property."""
        return self._data_source

    @data_source.setter
    def data_source(self, value):
        if not isinstance(value, DataSource):
            raise ValueError("data_source must be of type DataSource.")
        self._data_source = value

    @property
    def source_path(self):
        """The source_path property."""
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        self._source_path = value

    @property
    def destination_directory(self):
        """The destination_directory property."""
        return self._destination_directory

    @destination_directory.setter
    def destination_directory(self, value):
        self._destination_directory = value

    @property
    def staging_directory(self):
        """The destination_directory property."""
        return self._staging_directory

    @staging_directory.setter
    def staging_directory(self, value):
        if not os.path.isdir(value + "/staging/"):
            raise ValueError(
                f"{value}/staging/ does not exist or is not a directory. Have you initiated the directory?"
            )
        self._staging_directory = value + "/staging/"

    @property
    def quarantine_directory(self):
        """The destination_directory property."""
        return self._quarantine_directory

    @quarantine_directory.setter
    def quarantine_directory(self, value):
        if not os.path.isdir(value + "/quarantine/"):
            raise ValueError(
                f"{value}/quarantine/ does not exist or is not a directory. Have you initiated the directory?"
            )
        self._quarantine_directory = value + "/quarantine/"

    def _ingest_file(self, ingest_function):
        """Ingest a single file"""
        state = FileState(
            base_name=os.path.basename(self.path).split("/")[-1],
            source_path=self.path,
            current_path=self.path,
            current_hash=None,
        )

        staged_path = (
            f"{self.staging_directory}{os.path.basename(self.path).split('/')[-1]}"
        )
        res = subprocess.run(
            ingest_function, capture_output=True, text=True, encoding="utf8"
        )
        stdout = res.stdout.replace("\n", ". ")

        if not res.returncode:
            new_hash = LogWriter()._calculate_sha256(staged_path)
            state = replace(
                state,
                current_path=staged_path,
                current_hash=new_hash,
                status="INGESTED",
            )
            state = LogWriter().log_action(
                context=state,
                action="INGEST_FILE",
                new_path=state.current_path,
                note=stdout,
            )
        else:
            state = replace(state, status="NOT_INGESTED")
            state = LogWriter().log_action(
                state, "ERROR", state.source_path, note=stdout
            )

        if Utilities()._validate_file(state):
            state = replace(state, status="VALIDATED")
            state = LogWriter().log_action(
                state,
                "VALIDATE_FILETYPE",
                state.current_path,
                note="File validation successful.",
            )
            print(state)
            pass
            # TODO: extract metadata
        else:
            state = LogWriter().log_action(
                state,
                "VALIDATE_FILETYPE",
                state.current_path,
                note="File validation failed.",
            )
            Utilities()._quarantine_file(
                state.current_path,
                self.quarantine_directory,
                "file validation",
            )
            state = replace(
                state,
                current_path=f"{self.quarantine_directory}{state.base_name}",
                status="QUARANTINED",
            )

    def _ingest_directory(self, ingest_function, destination_subdir):
        """Walk tree and ingest every file"""
        # TODO: walk tree and call ingest file on every single file.
        pass

    def ingest(self, dry_run: bool = False):
        if dry_run:
            ingest_function = [
                "rsync",
                "-cain",
                self.path,
                f"{self.staging_directory}/",
            ]
        else:
            ingest_function = ["rsync", "-cai", self.path, f"{self.staging_directory}/"]

        if self.type == "file":
            self._ingest_file(ingest_function)
        elif self.type == "directory":
            self._ingest_directory(ingest_function, self.staging_directory)


# UTILITIES: FILE VALIDATION, QUARANTINE
class Utilities:
    def __init__(self):
        pass

    def _validate_file(self, file_state: FileState) -> bool:
        file_path = file_state.current_path
        magic = puremagic.from_file(file_path).lstrip(".")
        extension = file_path.rsplit(".", 1)[-1].lstrip(".")

        return magic == extension

    def _quarantine_file(
        self, file_path: str, quarantine_path: str, justification: str
    ) -> None:
        quarantined_path = (
            f"{quarantine_path}/{os.path.basename(file_path).split('/')[-1]}"
        )
        self._move_no_log(file_path, quarantine_path)
        LogWriter()._write_csv(
            "QUARANTINE_FILE",
            file_path,
            quarantined_path,
            note=f"This file was quarantined due to failed {justification}.",
        )

    def _move_no_log(self, file_path, destination_directory):
        if not os.path.isfile(file_path):
            raise ValueError(f"{file_path} doesn't exist or isn't a file.")
        elif not os.path.isdir(destination_directory):
            raise ValueError(
                f"{destination_directory} doesn't exist or isn't a directory."
            )
        filename = os.path.basename(file_path).split("/")[-1]
        shutil.move(file_path, f"{destination_directory}/{filename}")


# METADATA

# ORGANISE

# BAGIT

# Create cronjob or similar to check for corruption on a regular basis.

# CLEANUP AND REPORT
#

if __name__ == "__main__":
    ProjectInitiator().init_directory()
    DataIngester(DataSource("cli.py")).ingest()
