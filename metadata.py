import re
from uuid import uuid4
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import DCTERMS
from pathlib import Path
from data_objects import FileState
from log_writer import LogWriter

EXIF = Namespace("http://www.w3.org/2003/12/exif/ns#")
NFO = Namespace("http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#")

TECHNICAL_FIELD_MAP = {
    # EXIF—camera/image specific namespace
    "Exposure Time": EXIF.exposureTime,
    "F Number": EXIF.fNumber,
    "ISO": EXIF.isoSpeedRatings,
    "Focal Length In 35mm Format": EXIF.focalLengthIn35mmFilm,
    "Make": EXIF.make,
    "Camera Model Name": EXIF.model,
    "Image Width": EXIF.pixelXDimension,
    "Image Height": EXIF.pixelYDimension,
    # NFO—cross-format namespace for technical properties
    "Page Count": NFO.pageCount,
    "File:WordCount": NFO.wordCount,
    "Duration": NFO.duration,
    "Sample Rate": NFO.sampleRate,
    "Num Channels": NFO.channels,
}


def build_sidecar_graph(
    data_source: FileState, dc_fields: dict, technical_information: dict
) -> Graph:
    g = Graph()
    g.bind("dcterms", DCTERMS)
    g.bind("exif", EXIF)
    g.bind("nfo", NFO)

    subject = URIRef(f"urn:uuid:{data_source.uri}")

    for field_name, values in dc_fields.items():
        predicate = DCTERMS[field_name.rstrip("s")]
        for value in values:
            if value:
                g.add((subject, predicate, Literal(value)))

    for field_name, value in technical_information.items():
        predicate = TECHNICAL_FIELD_MAP[field_name]
        g.add((subject, predicate, Literal(value)))

    return g


def write_sidecar(
    data_source: FileState,
    logger: LogWriter,
    dc_fields: dict,
    technical_information: dict,
) -> None:
    g = build_sidecar_graph(data_source, dc_fields, technical_information)

    data_source_path = Path(data_source.current_path)
    sidecar_path = data_source_path.with_suffix(data_source_path.suffix + ".rdf.xml")
    g.serialize(destination=str(sidecar_path), format="pretty-xml")

    logger._write_log_entry(
        action_type="CREATE_SIDECAR", path_before=None, path_after=sidecar_path, note=""
    )


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
