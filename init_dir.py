import os
import csv
import json
from log_writer import LogWriter
from datetime import datetime


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
