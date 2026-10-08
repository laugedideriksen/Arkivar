import uuid
from datetime import datetime
from urllib.parse import quote
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDFS
from pathlib import Path
from .data_objects import FileState
from .log_writer import LogWriter
from .schema import Schema, SchemaRegistry
from dataclasses import dataclass
from typing import Optional, Any, Callable
from typing import Literal as typingLiteral
from .utils import resolve_created_date


def metadata_template(
    schema_ids: list[str], registry: Optional[SchemaRegistry] = None
) -> dict:
    """Build a fresh metadata.json body for the given active schemas: every
    term each schema declares (plain and event alike), keyed by json_key,
    with its obligation level and label as placeholder text -- plus a
    per-project resource id for each active event type (see EventType /
    _event_subject below for why)."""
    registry = registry or SchemaRegistry()
    out: dict[str, Any] = {"schemas": list(schema_ids)}
    event_ids: dict[str, str] = {}

    for schema_id in schema_ids:
        schema = registry.get(schema_id)
        fields: dict[str, list[str]] = {}
        for json_key, (event_id, term) in schema.json_keys().items():
            fields[json_key] = [f"[{term.obligation}] {term.label}"]
        out[schema_id] = fields
        for event in schema.events.values():
            event_ids[f"{schema_id}.{event.id}"] = str(uuid.uuid4())

    if event_ids:
        out["_event_ids"] = event_ids
    return out


class Target:
    """Deprecated: kept only so any external code still importing
    Target.DUBLIN_CORE / Target.TECHNICAL fails loudly rather than
    silently. FieldDefinition now takes schema_id directly."""


@dataclass(frozen=True)
class FieldDefinition:
    exif_field: str
    schema_id: str
    key: str
    transform: Optional[Callable[[str], Any]] = None
    merge: typingLiteral["append", "replace"] = "append"


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
        FieldDefinition("File:FileName", "dcterms", "titles", merge="replace"),
        FieldDefinition("File:FileType", "dcterms", "formats"),
    ],
    "file_stats": [
        FieldDefinition(
            "File:FileSize",
            "arkivar",
            "fileSize",
            transform=_to_int,
        ),
    ],
    # --- images ---
    "image_dimensions": [
        FieldDefinition(
            "EXIF:ExifImageWidth",
            "nfo",
            "width",
            transform=_to_int,
        ),
        FieldDefinition(
            "EXIF:ExifImageHeight",
            "nfo",
            "height",
            transform=_to_int,
        ),
    ],
    "heif_dimensions": [  # container dimensions; EXIF block is optional
        FieldDefinition(
            "File:ImageWidth",
            "nfo",
            "width",
            transform=_to_int,
        ),
        FieldDefinition(
            "File:ImageHeight",
            "nfo",
            "height",
            transform=_to_int,
        ),
    ],
    "camera": [  # EXIF-bearing images: JPEG, TIFF, most RAW, HEIC
        FieldDefinition(
            "EXIF:DateTimeOriginal",
            "dcterms",
            "dates",
            transform=_parse_exif_datetime,
        ),
        FieldDefinition("EXIF:Artist", "dcterms", "creators"),
        FieldDefinition("Composite:ShutterSpeed", "exif", "shutterSpeed"),
        FieldDefinition("Composite:Aperture", "exif", "fNumber"),
        FieldDefinition(
            "EXIF:ISO",
            "exif",
            "ISO",
            transform=_to_int,
        ),
        FieldDefinition("EXIF:Flash", "exif", "flash"),
        FieldDefinition(
            "Composite:FocalLength35efl",
            "exif",
            "focalLengthIn35mmEquivalent",
            transform=_to_int,
        ),
        FieldDefinition("EXIF:Make", "exif", "cameraMake"),
        FieldDefinition("EXIF:Model", "exif", "cameraModel"),
        FieldDefinition("EXIF:LensMake", "arkivar", "lensMake"),
        FieldDefinition("EXIF:LensModel", "arkivar", "lensModel"),
    ],
    "raw_image": [  # extra fields on top of "camera", for CR2/CR3/NEF/ARW/ORF/RAF/DNG
        FieldDefinition(
            "BitsPerSample",
            "nfo",
            "colorDepth",
            transform=_to_int,
        ),
        FieldDefinition("ColorSpace", "arkivar", "colorSpace"),
        FieldDefinition("DNGVersion", "arkivar", "dngVersion"),
    ],
    "lossless_image": [  # PNG, TIFF, BMP, WebP — format facts, no EXIF exposure data
        FieldDefinition(
            "PNG:BitDepth",
            "nfo",
            "colorDepth",
            transform=_to_int,
        ),
        FieldDefinition("PNG:ColorType", "arkivar", "colorType"),
        FieldDefinition("PNG:Compression", "arkivar", "compression"),
    ],
    # --- documents ---
    "document": [
        FieldDefinition("XMP:Producer", "arkivar", "producer"),
        FieldDefinition("XMP:CreatorTool", "arkivar", "creatorTool"),
        FieldDefinition(
            "PDF:PageCount",
            "nfo",
            "pageCount",
            transform=_to_int,
        ),
        FieldDefinition("PDF:PDFVersion", "arkivar", "pdfVersion"),
    ],
    "office_document": [  # DOCX, ODT, RTF
        FieldDefinition("Author", "dcterms", "creators"),
        FieldDefinition(
            "XMLPages",
            "nfo",
            "pageCount",
            transform=_to_int,
        ),
        FieldDefinition(
            "XML:Words",
            "nfo",
            "wordCount",
            transform=_to_int,
        ),
        FieldDefinition(
            "XML:Characters",
            "nfo",
            "characterCount",
            transform=_to_int,
        ),
        FieldDefinition("XML:Application", "arkivar", "creatorTool"),
    ],
    "plain_text": [
        FieldDefinition(
            "File:MIMEEncoding",
            "arkivar",
            "characterEncoding",
        ),
        FieldDefinition(
            "File:WordCount",
            "nfo",
            "wordCount",
            transform=_to_int,
        ),
    ],
    "structured_text": [  # CSV, JSON, XML, HTML — usually just basic file facts
        FieldDefinition(
            "File:MIMEEncoding",
            "arkivar",
            "characterEncoding",
        ),
    ],
    # --- audio ---
    "audio_descriptive": [  # ID3-style tags — about the content, not the encoding
        FieldDefinition("ID3:Title", "dcterms", "titles"),
        FieldDefinition("ID3:Artist", "dcterms", "creators"),
        FieldDefinition("ID3:Album", "dcterms", "relations"),
        FieldDefinition("ID3:Year", "dcterms", "dates"),
        FieldDefinition("ID3:Genre", "dcterms", "subject"),
    ],
    "audio_technical": [  # shared by lossy and lossless
        FieldDefinition("Composite:Duration", "nfo", "duration"),
        FieldDefinition(
            "RIFF:SampleRate",
            "nfo",
            "sampleRate",
            transform=_to_int,
        ),
        FieldDefinition(
            "RIFF:NumChannels",
            "nfo",
            "channels",
            transform=_to_int,
        ),
        FieldDefinition(
            "RIFF:BitsPerSample",
            "arkivar",
            "bitsPerSample",
            transform=_to_int,
        ),
    ],
    "audio_lossy": [  # MP3, AAC, OGG, M4A — extra fields for compressed audio
        FieldDefinition("MPEG:AudioBitrate", "arkivar", "bitrate"),
        FieldDefinition("AudioBitrate", "arkivar", "bitrate"),
        FieldDefinition("MPEG:EncodedBy", "arkivar", "encoder"),
    ],
    # --- video --- (field names least verified — check against your own files)
    "video_technical": [
        FieldDefinition("Duration", "nfo", "duration"),
        FieldDefinition("ImageWidth", "nfo", "width", transform=_to_int),
        FieldDefinition("ImageHeight", "nfo", "height", transform=_to_int),
        FieldDefinition("VideoFrameRate", "arkivar", "frameRate"),
        FieldDefinition("CompressorID", "arkivar", "videoCodec"),
        FieldDefinition("AudioFormat", "arkivar", "audioCodec"),
        FieldDefinition("AvgBitrate", "arkivar", "bitrate"),
    ],
}

FILETYPE_GROUPS: dict[str, list[str]] = {
    # images: standard/lossy
    ".jpg": ["common", "file_stats", "image_dimensions", "camera"],
    ".jpeg": ["common", "file_stats", "image_dimensions", "camera"],
    ".heic": ["common", "file_stats", "heif_dimensions", "camera"],
    ".heif": ["common", "file_stats", "heif_dimensions", "camera"],
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


def exiftool_fields_for(suffix: str) -> list[str]:
    """Replaces type_specific_metadata() — what to request from exiftool."""
    if suffix not in FILETYPE_GROUPS:
        raise ValueError(f"No field mapping registered for {suffix!r}")
    return [
        fd.exif_field
        for group in FILETYPE_GROUPS[suffix]
        for fd in FIELD_REGISTRY[group]
    ]


def _apply_exif_fields(
    sidecar: dict[str, dict[str, list]],
    exif_data: dict,
    suffix: str,
) -> None:
    """Merge exiftool-extracted values into sidecar[schema_id][key], for
    whichever schema_id each FieldDefinition targets -- regardless of
    which schemas the project selected for manual documentation. Technical
    extraction (exif/nfo/arkivar) always runs; it isn't opt-in."""
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

            bucket = sidecar.setdefault(file_definition.schema_id, {})
            if file_definition.merge == "replace":
                bucket[file_definition.key] = [value]
            else:
                existing = bucket.setdefault(file_definition.key, [])
                if value not in existing:
                    existing.append(value)


def _write_project_title_to_is_part_of(
    sidecar: dict[str, dict[str, list]], project_metadata: dict
) -> None:
    project_titles = project_metadata.get("dcterms", {}).get("titles", [])
    existing = sidecar.setdefault("dcterms", {}).setdefault("isPartOf", [])
    for title in project_titles:
        if title and title not in existing:
            existing.append(title)


def _event_subject(
    schema: Schema, event_id: str, fields: dict[str, list], project_metadata: dict
) -> URIRef:
    """One resource per event *type* per *project* (not per file, not
    repeatable -- see schema.py's module docstring for why). Preferably
    seeded from the event's own identifying field, so the same
    human-assigned id (e.g. a case number) determines the resource's URI;
    falling back to a UUID minted once at `init` time and cached in
    metadata.json under "_event_ids" for events left unfilled."""
    event = schema.events[event_id]
    if event.identifier_term:
        id_key = f"{event_id}.{event.identifier_term}"
        id_values = fields.get(id_key)
        if id_values and id_values[0]:
            return URIRef(
                f"urn:arkivar:{schema.id}:{event_id}:{quote(str(id_values[0]), safe='')}"
            )
    cached = project_metadata.get("_event_ids", {}).get(f"{schema.id}.{event_id}")
    if cached:
        return URIRef(f"urn:uuid:{cached}")
    return URIRef(f"urn:uuid:{uuid.uuid4()}")


def build_sidecar(
    project_metadata: dict,
    exif_data: dict,
    suffix: str,
    registry: Optional[SchemaRegistry] = None,
) -> dict:
    """project_metadata's own "schemas" list decides which manually-entered
    vocabularies are active for this project (default: just dcterms, for
    backwards compatibility with pre-schema-registry metadata.json files).
    Exiftool-derived technical schemas (exif/nfo/arkivar) are layered in
    regardless, exactly as before."""
    registry = registry or SchemaRegistry()
    schema_ids = project_metadata.get("schemas", ["dcterms"])

    sidecar: dict[str, dict[str, list]] = {
        sid: {k: list(v) for k, v in project_metadata.get(sid, {}).items()}
        for sid in schema_ids
    }

    _apply_exif_fields(sidecar, exif_data, suffix)
    _write_project_title_to_is_part_of(sidecar, project_metadata)

    event_subjects: dict[str, str] = {}
    for sid, fields in sidecar.items():
        schema = registry.get(sid)
        for event_id in schema.events:
            event_subjects[f"{sid}.{event_id}"] = str(
                _event_subject(schema, event_id, fields, project_metadata)
            )

    return {"fields": sidecar, "event_subjects": event_subjects}


def build_sidecar_graph(
    data_source: FileState, sidecar: dict, registry: Optional[SchemaRegistry] = None
) -> Graph:
    registry = registry or SchemaRegistry()
    g = Graph()
    g.bind("rdfs", RDFS)

    subject = URIRef(f"urn:uuid:{data_source.uri}")
    event_subjects = {
        k: URIRef(v) for k, v in sidecar.get("event_subjects", {}).items()
    }
    labeled_events: set[str] = set()

    for schema_id, fields in sidecar["fields"].items():
        schema = registry.get(schema_id)
        g.bind(schema.prefix, schema.namespace)
        keys = schema.json_keys()

        for json_key, values in fields.items():
            if json_key not in keys:
                continue  # stale/unrecognised key left over from an old schema version
            event_id, term = keys[json_key]
            predicate = schema.predicate_for(term)

            if event_id is None:
                target_subject = subject
            else:
                event_key = f"{schema_id}.{event_id}"
                target_subject = event_subjects[event_key]
                if event_key not in labeled_events:
                    event = schema.events[event_id]
                    g.add(
                        (
                            subject,
                            schema.namespace[event.predicate_local_name],
                            target_subject,
                        )
                    )
                    g.add((target_subject, RDFS.label, Literal(event.label)))
                    labeled_events.add(event_key)

            for value in values:
                if value:
                    g.add((target_subject, predicate, Literal(value)))

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
