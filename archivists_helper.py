import os
import subprocess
import shutil
import pathlib
from datetime import datetime
import csv
import json
from hashlib import sha256
import bagit


# CHANGELOG
class LogWriter:
    def __init__(
        self, project_name: str, dt_format: str = "%Y%m%d-%H:%M:%S.%f"
    ) -> None:
        self.project_name = project_name
        self.log_file = self.project_name + "_changelog.csv"
        self.dt_format = dt_format

    def _fail_if_file_exists(self, file_path, name, action) -> bool:
        if os.path.isfile(file_path):
            self._write_csv(
                action,
                os.path.abspath(file_path),
                os.path.abspath(file_path),
                self._calculate_sha256(os.path.abspath(file_path)),
                f"ACTION FAILED: {name} already exists.",
            )
            return False
        return True

    def _calculate_sha256(self, file_path):
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256().update(byte_block)
            return sha256().hexdigest()

    # Create and write to CSV
    def _create_csv(self):
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
        note: str = "",
    ) -> None:
        csv_exists = os.path.isfile(self.log_file)
        if not csv_exists:
            self._create_csv()

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)

            permitted_actions = [
                "CREATE_CHANGELOG",
                "CREATE_DUBLIN_CORE_JSON",
                "INGEST_FILE",
                "COMPUTE_CHECKSUM",
                "EXTRACT_METADATA",
                "NORMALISE_FILENAME",
                "NORMALISE_METADATA",
                "CREATE_DIRECTORY",
                "MOVE",
                "CREATE_BAG",
                "VALIDATE_BAG",
                "ERROR",
            ]
            if action_type not in permitted_actions:
                note = f"{action_type} is not a valid action type."
                action_type = "ERROR"

            writer.writerow(
                [
                    datetime.now().strftime(self.dt_format),
                    action_type,
                    path_before,
                    path_after,
                    hash_before,
                    self._calculate_sha256(path_after),
                    note,
                ]
            )
            f.flush()


# ERROR REPORTING


# Project Initiation
class ProjectInitiator:
    def __init__(
        self, project_name: str = "ProjectName", start_date: str = "YYYYmmdd"
    ) -> None:
        self.project_name = project_name
        self.start_date = start_date
        self.metadata_json = f"{self.project_name}_metadata.json"

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

        with open(f"{self.project_name}_metadata.json", "w") as f:
            json.dump(dc_dict, f, sort_keys=False, indent=4, ensure_ascii=False)

        LogWriter(self.project_name)._write_csv(
            "CREATE_DUBLIN_CORE_JSON",
            "N/A",
            os.path.abspath(self.metadata_json),
            "N/A",
        )

    def init_directory(self):
        LogWriter(self.project_name)._create_csv()
        self._create_dublin_core_json()
        if not os.path.isdir('staging'):
            os.mkdir('staging')
        if not os.path.isdir('quarantine'):
            os.mkdir('quarantine')
        print("Directory initialised.")


# CREATE DATA SOURCE
class DataSource:
    """Create data source object."""
    def __init__(self, source_path:str):
        self.source_path = source_path

    @property
    def source_path(self):
        """The source_path property."""
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        if not os.path.exists(value):
            raise FileNotFoundError(f'{value} does not exist.')
        elif os.path.isfile(value):
            self.source_type = "file"
        elif os.path.isdir(value):
            self.source_type = 'directory'
        self._source_path = os.path.abspath(value)

# INGESTION
class DataIngester:
    """This class takes a data source object as its input, and ingests all data from there using rsync."""
    def __init__(self, data_source):
        self.data_source = data_source
        self.path = self.data_source.source_path
        self.type = self.data_source.source_type

    @property
    def data_source(self):
        """The data_source property."""
        return self._data_source

    @data_source.setter
    def data_source(self, value):
        if not isinstance(value, DataSource):
            raise ValueError('data_source must be of type DataSource.')
        self._data_source = value

    @property
    def source_path(self):
        """The source_path property."""
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        self._source_path = value

    def _ingest_file(self, ingest_function):
        res = subprocess.run(ingest_function, capture_output=True)
        pass

    def _ingest_directory(self, ingest_function):
        #TODO: walk tree and call ingest file on every single file.
        pass

    def ingest(self, dry_run: bool = False):
        if dry_run:
            ingest_function = ['rsync','-cain', self.path, 'staging']
        else:
            ingest_function = ['rsync','-cai', self.path, 'staging']

        if self.type == 'file':
            self._ingest_file(ingest_function)
        elif self.type == 'directory':
            self._ingest_directory(ingest_function)

# FILE VALIDATION

# METADATA

# ORGANISE

# BAGIT

# Create cronjob or similar to check for corruption on a regular basis.

# CLEANUP AND REPORT
#

if __name__ == "__main__":
    ProjectInitiator("Test", "20260608").init_directory()
    #print(DataIngester(DataSource('cli.py')).path)
