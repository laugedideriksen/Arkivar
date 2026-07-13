import os
import json
import puremagic
from data_objects import FileState
import subprocess
from typing import Any
from pathlib import Path


def validate_file(file_state: FileState) -> bool:
    file_path = str(file_state.current_path)
    magic = puremagic.from_file(file_path).lstrip(".")
    extension = file_path.rsplit(".", 1)[-1].lstrip(".")

    match extension:  # Some markdown files have are identified as txt files. This makes sure they don't fail to validate
        case "md":
            extension = "txt"
        case _:
            pass

    return magic.lower() == extension.lower()


def run_rsync(
    source: Path, destination: Path, dry_run: bool = False
) -> tuple[bool, str]:
    flags = ["-ca", "--itemize-changes"]  # TODO: check with my earlier version
    if dry_run:
        flags.append("-n")

    cmd = ["rsync"] + flags + [str(source), str(destination)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf8")
        return (res.returncode == 0, res.stdout)
    except Exception as e:
        return (False, str(e))


def run_exiftool(file_path: Path) -> tuple[bool, Any]:
    cmd = ["exiftool", "-j", "-n", "-G", "-api", "LargeFileSupport=1", file_path]
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding="utf8"
        )
        data = json.loads(res.stdout)
        return (res.returncode == 0, data[0]) if data else (res.returncode == 0, {})
    except subprocess.CalledProcessError as e:
        return (False, str(e))


def dc_template() -> dict:
    return dict(
        contributors=[
            "An entity responsible for making contributions to the resource."
        ],
        coverage=[
            "The spatial or temporal topic of the resource, spatial applicability of the resource, or jurisdiction under which the resource is relevant."
        ],
        creators=["An entity primarily responsible for making the resource."],
        dates=[
            "A point or period of time associated with an event in the lifecycle of the resource."
        ],
        descriptions=[
            "An account of the resource. Description may include but is not limited to: an abstract, a table of contents, a graphical representation, or a free-text account of the resource."
        ],
        formats=["The file format, physical medium, or dimensions of the resource."],
        identifiers=[
            "An unambiguous reference to the resource within a given context. Recommended best practice is to identify the resource by means of a string conforming to a formal identification system."
        ],
        languages=["A language of the resource."],
        publishers=["An entity responsible for making the resource available."],
        relations=[
            "A related resource. Recommended practice is to identify the related resource by means of a URI. If this is not possible or feasible, a string conforming to a formal identification system may be provided."
        ],
        rights=["Information about rights held in and over the resource."],
        sources=["A related resource from which the described resource is derived."],
        subject=[
            "The topic of the resource. Typically, the subject will be represented using keywords, key phrases, or classification codes. Recommended best practice is to use a controlled vocabulary."
        ],
        titles=["A name given to the resource."],
        types=["The nature or genre of the resource."],
    )


def metadata_map() -> dict:
    """Returns a dictionary mapping exiftool entries to Dublin Core fields."""
    return {
        "File Name": "titles",
        "Date/Time Original": "dates",
        "File Type": "types",
        "Artist": "creator",
        "Author": "creator",
        "Image Description": "description",
        "Description": "description",
    }


def type_specific_metadata(suffix) -> dict:
    """Returns a list of exiftool entries for specific file types."""
    entries = {
        ".jpg": ["File Size", "Image Width", "Image Height"],
        "exposure": [
            "Exposure Time",
            "F Number",
            "ISO",
            "Focal Length In 35mm Format",
        ],
        "camera": ["Make", "Camera Model Name", "Lens Make", "Lens Model"],
        ".pdf": [
            "File Size",
            "PDF Version",
            "Page Count",
            "Creator",
            "Producer",
            "Creator Tool",
        ],
        ".wav": ["File Size", "Duration", "Sample Rate", "Num Channels"],
        ".mp3": [
            "File Size",
            "Duration",
            "Title",
            "Album",
            "Year",
            "Artist",
            "Band",
            "Track",
            "Media",
        ],
        ".txt": ["File:WordCount", "File:MIMEEncoding"],
    }

    filetype_map = {
        ".jpg": {
            "file": entries[".jpg"],
            "exposure": entries["exposure"],
            "camera": entries["camera"],
        },
        ".txt": {"file": entries[".txt"]},
        ".md": {"file": entries[".txt"]},
    }

    return filetype_map[suffix]
