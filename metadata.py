from datetime import datetime
from uuid import uuid4
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import DCTERMS
from pathlib import Path
from data_objects import FileState
from log_writer import LogWriter
from dataclasses import dataclass
from typing import Optional, Any, Callable
from enum import Enum
from utils import resolve_created_date


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


EXIF = Namespace("http://www.w3.org/2003/12/exif/ns#")
NFO = Namespace("http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#")
ARKIVAR = Namespace("https://arkivar.example/ns/technical#")


class Target(Enum):
    DUBLIN_CORE = "dublin_core"
    TECHNICAL = "technical"


@dataclass(frozen=True)
class FieldDefinition:
    exif_field: str  # exiftool's field name, e.g. "Date/Time Original"
    target: Target
    key: str  # DC key or technical predicate local name
    namespace: Optional[Namespace] = None  # only used when target is TECHNICAL
    transform: Optional[Callable[[str], Any]] = None  # optional value normalizer


def _parse_exif_datetime(value: str) -> str:
    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S").date().isoformat()


def _to_int(value: str | int | float) -> Optional[int]:
    try:
        return int(float(value))
    except ValueError, TypeError:
        return None


# not currently in use, but added to support future functionality.
def _to_float(value: str | int | float) -> Optional[float]:
    try:
        return float(value)
    except ValueError, TypeError:
        return None


FIELD_REGISTRY: dict[str, list[FieldDefinition]] = {
    # --- shared across (almost) everything ---
    "common": [
        FieldDefinition("File:FileName", Target.DUBLIN_CORE, "titles"),
        FieldDefinition("File:FileType", Target.DUBLIN_CORE, "formats"),
    ],
    "file_stats": [
        FieldDefinition(
            "File:FileSize",
            Target.TECHNICAL,
            "fileSize",
            namespace=ARKIVAR,
            transform=_to_int,
        ),
    ],
    # --- images ---
    "image_dimensions": [
        FieldDefinition(
            "EXIF:ExifImageWidth",
            Target.TECHNICAL,
            "width",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "EXIF:ExifImageHeight",
            Target.TECHNICAL,
            "height",
            namespace=NFO,
            transform=_to_int,
        ),
    ],
    "camera": [  # EXIF-bearing images: JPEG, TIFF, most RAW, HEIC
        FieldDefinition(
            "EXIF:DateTimeOriginal",
            Target.DUBLIN_CORE,
            "dates",
            transform=_parse_exif_datetime,
        ),
        FieldDefinition("EXIF:Artist", Target.DUBLIN_CORE, "creators"),
        FieldDefinition(
            "Composite:ShutterSpeed", Target.TECHNICAL, "shutterSpeed", namespace=EXIF
        ),
        FieldDefinition(
            "Composite:Aperture", Target.TECHNICAL, "fNumber", namespace=EXIF
        ),
        FieldDefinition(
            "EXIF:ISO",
            Target.TECHNICAL,
            "ISO",
            namespace=EXIF,
            transform=_to_int,
        ),
        FieldDefinition("EXIF:Flash", Target.TECHNICAL, "flash", namespace=EXIF),
        FieldDefinition(
            "Composite:FocalLength35efl",
            Target.TECHNICAL,
            "focalLengthIn35mmEquivalent",
            namespace=EXIF,
            transform=_to_int,
        ),
        FieldDefinition("EXIF:Make", Target.TECHNICAL, "cameraMake", namespace=EXIF),
        FieldDefinition("EXIF:Model", Target.TECHNICAL, "cameraModel", namespace=EXIF),
        FieldDefinition(
            "EXIF:LensMake", Target.TECHNICAL, "lensMake", namespace=ARKIVAR
        ),
        FieldDefinition(
            "EXIF:LensModel", Target.TECHNICAL, "lensModel", namespace=ARKIVAR
        ),
    ],
    "raw_image": [  # extra fields on top of "camera", for CR2/CR3/NEF/ARW/ORF/RAF/DNG
        FieldDefinition(
            "Bits Per Sample",
            Target.TECHNICAL,
            "colorDepth",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "Color Space", Target.TECHNICAL, "colorSpace", namespace=ARKIVAR
        ),
        FieldDefinition(
            "DNG Version", Target.TECHNICAL, "dngVersion", namespace=ARKIVAR
        ),
    ],
    "lossless_image": [  # PNG, TIFF, BMP, WebP — format facts, no EXIF exposure data
        FieldDefinition(
            "Bit Depth",
            Target.TECHNICAL,
            "colorDepth",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition("Color Type", Target.TECHNICAL, "colorType", namespace=ARKIVAR),
        FieldDefinition(
            "Compression", Target.TECHNICAL, "compression", namespace=ARKIVAR
        ),
    ],
    # --- documents ---
    "document": [
        FieldDefinition("PDF:Creator", Target.DUBLIN_CORE, "creators"),
        FieldDefinition(
            "XMP:Producer", Target.TECHNICAL, "producer", namespace=ARKIVAR
        ),
        FieldDefinition(
            "XMP:CreatorTool", Target.TECHNICAL, "creatorTool", namespace=ARKIVAR
        ),
        FieldDefinition(
            "PDF:PageCount",
            Target.TECHNICAL,
            "pageCount",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "PDF:PDFVersion", Target.TECHNICAL, "pdfVersion", namespace=ARKIVAR
        ),
    ],
    "office_document": [  # DOCX, ODT, RTF
        FieldDefinition("Author", Target.DUBLIN_CORE, "creators"),
        FieldDefinition(
            "Page Count",
            Target.TECHNICAL,
            "pageCount",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "Word Count",
            Target.TECHNICAL,
            "wordCount",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "Character Count",
            Target.TECHNICAL,
            "characterCount",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "Application", Target.TECHNICAL, "creatorTool", namespace=ARKIVAR
        ),
    ],
    "plain_text": [
        FieldDefinition(
            "File:MIMEEncoding",
            Target.TECHNICAL,
            "characterEncoding",
            namespace=ARKIVAR,
        ),
        FieldDefinition(
            "File:WordCount",
            Target.TECHNICAL,
            "wordCount",
            namespace=NFO,
            transform=_to_int,
        ),
    ],
    "structured_text": [  # CSV, JSON, XML, HTML — usually just basic file facts
        FieldDefinition(
            "File:MIMEEncoding",
            Target.TECHNICAL,
            "characterEncoding",
            namespace=ARKIVAR,
        ),
    ],
    # --- audio ---
    "audio_descriptive": [  # ID3-style tags — about the content, not the encoding
        FieldDefinition("ID3:Title", Target.DUBLIN_CORE, "titles"),
        FieldDefinition("ID3:Artist", Target.DUBLIN_CORE, "creators"),
        FieldDefinition("ID3:Album", Target.DUBLIN_CORE, "relations"),
        FieldDefinition("ID3:Year", Target.DUBLIN_CORE, "dates"),
        FieldDefinition("ID3:Genre", Target.DUBLIN_CORE, "subject"),
    ],
    "audio_technical": [  # shared by lossy and lossless
        FieldDefinition(
            "Composite:Duration", Target.TECHNICAL, "duration", namespace=NFO
        ),
        FieldDefinition(
            "RIFF:SampleRate",
            Target.TECHNICAL,
            "sampleRate",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "RIFF:NumChannels",
            Target.TECHNICAL,
            "channels",
            namespace=NFO,
            transform=_to_int,
        ),
        FieldDefinition(
            "RIFF:BitsPerSample",
            Target.TECHNICAL,
            "bitsPerSample",
            namespace=ARKIVAR,
            transform=_to_int,
        ),
    ],
    "audio_lossy": [  # MP3, AAC, OGG, M4A — extra fields for compressed audio
        FieldDefinition(
            "MPEG:AudioBitrate", Target.TECHNICAL, "bitrate", namespace=ARKIVAR
        ),
        FieldDefinition("AudioBitrate", Target.TECHNICAL, "bitrate", namespace=ARKIVAR),
        FieldDefinition(
            "MPEG:EncodedBy", Target.TECHNICAL, "encoder", namespace=ARKIVAR
        ),
    ],
    # --- video --- (field names least verified — check against your own files)
    "video_technical": [
        FieldDefinition("Duration", Target.TECHNICAL, "duration", namespace=NFO),
        FieldDefinition(
            "Image Width", Target.TECHNICAL, "width", namespace=NFO, transform=_to_int
        ),
        FieldDefinition(
            "Image Height", Target.TECHNICAL, "height", namespace=NFO, transform=_to_int
        ),
        FieldDefinition(
            "Video Frame Rate", Target.TECHNICAL, "frameRate", namespace=ARKIVAR
        ),
        FieldDefinition(
            "Compressor ID", Target.TECHNICAL, "videoCodec", namespace=ARKIVAR
        ),
        FieldDefinition(
            "Audio Format", Target.TECHNICAL, "audioCodec", namespace=ARKIVAR
        ),
        FieldDefinition("Avg Bitrate", Target.TECHNICAL, "bitrate", namespace=ARKIVAR),
    ],
}

FILETYPE_GROUPS: dict[str, list[str]] = {
    # images: standard/lossy
    ".jpg": ["common", "file_stats", "image_dimensions", "camera"],
    ".jpeg": ["common", "file_stats", "image_dimensions", "camera"],
    ".heic": ["common", "file_stats", "image_dimensions", "camera"],
    # images: lossless
    ".png": ["common", "file_stats", "image_dimensions", "lossless_image"],
    ".tif": ["common", "file_stats", "image_dimensions", "camera", "lossless_image"],
    ".tiff": ["common", "file_stats", "image_dimensions", "camera", "lossless_image"],
    ".bmp": ["common", "file_stats", "image_dimensions", "lossless_image"],
    ".webp": ["common", "file_stats", "image_dimensions", "lossless_image"],
    ".gif": ["common", "file_stats", "image_dimensions"],
    # images: RAW
    ".cr2": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".cr3": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".nef": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".arw": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".orf": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".raf": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    ".dng": ["common", "file_stats", "image_dimensions", "camera", "raw_image"],
    # documents
    ".pdf": ["common", "file_stats", "document"],
    ".docx": ["common", "file_stats", "office_document"],
    ".odt": ["common", "file_stats", "office_document"],
    ".rtf": ["common", "file_stats", "office_document"],
    # text
    ".txt": ["common", "file_stats", "plain_text"],
    ".md": ["common", "file_stats", "plain_text"],
    ".csv": ["common", "file_stats", "structured_text"],
    ".json": ["common", "file_stats", "structured_text"],
    ".xml": ["common", "file_stats", "structured_text"],
    ".html": ["common", "file_stats", "structured_text"],
    # audio: lossy
    ".mp3": [
        "common",
        "file_stats",
        "audio_descriptive",
        "audio_technical",
        "audio_lossy",
    ],
    ".m4a": [
        "common",
        "file_stats",
        "audio_descriptive",
        "audio_technical",
        "audio_lossy",
    ],
    ".aac": [
        "common",
        "file_stats",
        "audio_descriptive",
        "audio_technical",
        "audio_lossy",
    ],
    ".ogg": [
        "common",
        "file_stats",
        "audio_descriptive",
        "audio_technical",
        "audio_lossy",
    ],
    # audio: lossless
    ".wav": ["common", "file_stats", "audio_technical"],
    ".flac": ["common", "file_stats", "audio_descriptive", "audio_technical"],
    ".aiff": ["common", "file_stats", "audio_technical"],
    ".aif": ["common", "file_stats", "audio_technical"],
    # video
    ".mp4": ["common", "file_stats", "video_technical"],
    ".mov": ["common", "file_stats", "video_technical"],
    ".mkv": ["common", "file_stats", "video_technical"],
    ".avi": ["common", "file_stats", "video_technical"],
    ".webm": ["common", "file_stats", "video_technical"],
}


DC_TEMPLATE_TO_DCTERMS = {
    "contributors": DCTERMS.contributor,
    "coverage": DCTERMS.coverage,
    "creators": DCTERMS.creator,
    "dates": DCTERMS.date,
    "descriptions": DCTERMS.description,
    "formats": DCTERMS.format,
    "identifiers": DCTERMS.identifier,
    "languages": DCTERMS.language,
    "publishers": DCTERMS.publisher,
    "relations": DCTERMS.relation,
    "rights": DCTERMS.rights,
    "sources": DCTERMS.source,
    "subject": DCTERMS.subject,
    "titles": DCTERMS.title,
    "types": DCTERMS.type,
}


def exiftool_fields_for(suffix: str) -> list[str]:
    """Replaces type_specific_metadata() — what to request from exiftool."""
    if suffix not in FILETYPE_GROUPS:
        raise ValueError(f"No field mapping registered for {suffix!r}")
    return [
        fd.exif_field
        for group in FILETYPE_GROUPS[suffix]
        for fd in FIELD_REGISTRY[group]
    ]


def build_sidecar(project_metadata: dict, exif_data: dict, suffix: str) -> dict:
    dc = dict(project_metadata)
    technical = {}

    for group in FILETYPE_GROUPS[suffix]:
        for file_definition in FIELD_REGISTRY[group]:
            raw_exif_value = exif_data.get(file_definition.exif_field)
            if raw_exif_value is None:
                continue
            value = (
                file_definition.transform(raw_exif_value)
                if file_definition.transform
                else raw_exif_value
            )
            if value is None:
                continue

            if file_definition.target is Target.DUBLIN_CORE:
                dc[file_definition.key] = [str(value)]
            else:
                technical[(file_definition.namespace, file_definition.key)] = value

    return {"dublin_core": dc, "technical_information": technical}


def build_sidecar_graph(data_source: FileState, sidecar: dict) -> Graph:
    g = Graph()
    g.bind("dcterms", DCTERMS)
    g.bind("exif", EXIF)
    g.bind("nfo", NFO)
    g.bind("arkivar", ARKIVAR)

    subject = URIRef(f"urn:uuid:{data_source.uri}")

    for key, values in sidecar["dublin_core"].items():
        predicate = DC_TEMPLATE_TO_DCTERMS[key]
        for value in values:
            if value:
                g.add((subject, predicate, Literal(value)))

    for (namespace, local_name), value in sidecar["technical_information"].items():
        g.add((subject, namespace[local_name], Literal(value)))

    return g


def write_sidecar(
    data_source: FileState,
    logger: LogWriter,
    sidecar: dict,
) -> FileState:
    g = build_sidecar_graph(data_source, sidecar)

    data_source_path = data_source.current_path
    sidecar_path = data_source_path.with_suffix(data_source_path.suffix + ".rdf.xml")
    g.serialize(destination=str(sidecar_path), format="pretty-xml")

    valid, msg = validate_sidecar(sidecar_path, expected_graph=g)
    if not valid:
        return logger.change_state(
            data_source,
            "ERROR",
            data_source.current_path,
            note=f"Sidecar validation failed: {msg}",
        )

    created_date, date_source = resolve_created_date(sidecar, data_source_path)
    if created_date:
        note = f"{msg}; create date capture via {date_source}"
    else:
        note = f"{msg}; no capture date resolved."

    return logger.change_state(
        data_source,
        "CREATE_SIDECAR",
        data_source.current_path,
        sidecar_path=sidecar_path,
        created_date=created_date,
        note=note,
    )


def validate_sidecar(sidecar_path: Path, expected_graph: Graph) -> tuple[bool, str]:
    try:
        reparsed = Graph()
        reparsed.parse(str(sidecar_path), format="xml")
    except Exception as e:
        return False, f"Invalid RDF/XML: {e}"

    if set(reparsed) != set(expected_graph):
        missing = set(expected_graph) - set(reparsed)
        extra = set(reparsed) - set(expected_graph)
        return (
            False,
            f"Mismatch between written and expected XML: missing: {missing}, unexpected: {extra}",
        )

    return True, f"Valid XML: {len(reparsed)} triples"
