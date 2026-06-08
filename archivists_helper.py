import csv
import json
import os
from hashlib import sha256
import pathlib
import bagit
from datetime import datetime


# CHANGELOG
class LogWriter:
    def __init__(
        self, project_name: str, dt_format: str = "%Y%m%d-%H:%M:%S.%f"
    ) -> None:
        self.project_name = project_name
        self.log_file = self.project_name + "_changelog.csv"
        self.dt_format = dt_format

    def _calculate_sha256(self, file_path):
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256().update(byte_block)
            return sha256().hexdigest()

    # Create and write to CSV

    def _create_csv(self):
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
                ]
            )
            f.flush()

    def _write_csv(
        self,
        action_type: str,
        path_before: str,
        path_after: str,
        hash_before: str = "N/A",
    ):
        file_exists = os.path.isfile(self.log_file)

        with open(self.log_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                self._create_csv()

            permitted_actions = [
                "CREATE_CHANGELOG",
                "INGEST_FILE",
                "COMPUTE_CHECKSUM",
                "EXTRACT_METADATA",
                "NORMALISE_FILENAME",
                "NORMALISE_METADATA",
                "CREATE_DIRECTORY",
                "MOVE",
                "CREATE_BAG",
                "VALIDATE_BAG",
            ]
            if action_type not in permitted_actions:
                action_type = "ERROR"

            writer.writerow(
                [
                    datetime.now().strftime(self.dt_format),
                    action_type,
                    path_before,
                    path_after,
                    hash_before,
                    self._calculate_sha256(path_after),
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

    def _create_dublin_core_json(self):
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

    def init_folder(self):
        LogWriter(self.project_name)._create_csv()
        self._create_dublin_core_json()


# CREATE DATA OBJECT

# INGESTION

# FILE VALIDATION

# METADATA

# ORGANISE

# BAGIT

# Create cronjob or similar to check for corruption on a regular basis.

# CLEANUP AND REPORT
#


if __name__ == "__main__":
    ProjectInitiator("Test", "20260608").init_folder()
