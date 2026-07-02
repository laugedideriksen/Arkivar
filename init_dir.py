import os
import csv
import json
from log_writer import LogWriter
from datetime import datetime
from utils import dc_template


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

        dc_dict = dc_template()

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
