"""Schema registry: pluggable metadata vocabularies for Arkivar.

A *schema* is a named RDF vocabulary Arkivar knows how to write project or
file metadata into. Dublin Core Terms, and the metadata standard for
conservation-restoration documentation (KuR-MDS), are both just schemas --
nothing about Dublin Core is special-cased in code any more.

Two kinds of fields exist:

- Plain terms (``Schema.terms``): literal-valued properties of the *file*
  itself -- a title, a creator, a material. This is the only shape Dublin
  Core, EXIF, NFO, and the arkivar: fallback vocabulary need.

- Event terms (``Schema.events``): fields describing something that
  happened to or with the object -- a condition assessment, a conservation
  measure -- rather than being a direct property of the file. These get
  their own RDF resource, linked from every file's subject in the project
  via ``EventType.predicate_local_name``.

  Arkivar deliberately does *not* model repeated events (e.g. several
  condition assessments for one object over time): a project holds at most
  one instance of each active event type. Document differently-treated
  material as separate projects instead (see schemas/kur_mds.json).

Adding or updating a schema is a data change, not a code change: drop a
``<schema_id>.json`` file into ``schemas/`` (or a project-local override
directory) following the shape below, and it's available to
``arkivar init --schema <schema_id>``.

JSON shape::

    {
      "id": "kur_mds",
      "prefix": "kur",
      "namespace_uri": "https://www.w3id.org/conservation/terms/metadata/",
      "terms": [
        {"local_name": "...", "label": "...", "obligation": "mandatory",
         "repeatable": true, "term_uri": "https://... (optional)"}
      ],
      "events": [
        {"id": "...", "label": "...", "predicate_local_name": "...",
         "identifier_term": "... (optional, local_name of the term below "
                             "that uniquely identifies each instance)",
         "terms": [ {same shape as above} ]}
      ]
    }

``local_name`` may contain dots to mirror a schema's own nested grouping
(e.g. ``"zustandsbeschreibung.physischerObjektzustand.aktuelleMasse"``);
dots become underscores in the derived RDF predicate's local name. Give a
term an explicit ``term_uri`` whenever the schema already publishes one
(KuR-MDS does, for every field) rather than relying on namespace + derived
local name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from rdflib import Namespace, URIRef

# Free-form, not a fixed enum: each schema states obligation in its own
# vocabulary and language (dcterms.json/exif.json/nfo.json/arkivar.json use
# "mandatory"/"conditional"/"recommended"/"optional"; kur_mds.json uses the
# whitepaper's own German terms -- "Pflicht"/"bedingte Pflicht"/"empfohlen"/
# "optional"). Only ever displayed (see metadata_template()), never matched
# on, so any short string a schema author chooses is safe to use here.
Obligation = str

BUNDLED_SCHEMA_DIR = Path(__file__).parent / "schemas"


@dataclass(frozen=True)
class SchemaTerm:
    local_name: str
    label: str
    obligation: Obligation = "optional"
    repeatable: bool = True
    term_uri: Optional[str] = None

    @property
    def predicate_local_name(self) -> str:
        return self.local_name.replace(".", "_")


@dataclass(frozen=True)
class EventType:
    id: str
    label: str
    predicate_local_name: str
    terms: dict[str, SchemaTerm]
    identifier_term: Optional[str] = None  # local_name of the identifying term, if any


@dataclass(frozen=True)
class Schema:
    id: str
    prefix: str
    namespace_uri: str
    terms: dict[str, SchemaTerm] = field(default_factory=dict)
    events: dict[str, EventType] = field(default_factory=dict)

    @property
    def namespace(self) -> Namespace:
        return Namespace(self.namespace_uri)

    def predicate_for(self, term: SchemaTerm) -> URIRef:
        if term.term_uri:
            return URIRef(term.term_uri)
        return self.namespace[term.predicate_local_name]

    def json_keys(self) -> dict[str, tuple[Optional[str], SchemaTerm]]:
        """Every field this schema can hold in metadata.json, as
        {json_key: (event_id_or_None, term)}. A plain term's json_key is
        just its local_name; an event term's is "<event_id>.<local_name>"."""
        out: dict[str, tuple[Optional[str], SchemaTerm]] = {
            term.local_name: (None, term) for term in self.terms.values()
        }
        for event in self.events.values():
            for term in event.terms.values():
                out[f"{event.id}.{term.local_name}"] = (event.id, term)
        return out


def _term_from_dict(d: dict) -> SchemaTerm:
    return SchemaTerm(
        local_name=d["local_name"],
        label=d["label"],
        obligation=d.get("obligation", "optional"),
        repeatable=d.get("repeatable", True),
        term_uri=d.get("term_uri"),
    )


def _schema_from_dict(d: dict) -> Schema:
    terms = {t["local_name"]: _term_from_dict(t) for t in d.get("terms", [])}
    events: dict[str, EventType] = {}
    for e in d.get("events", []):
        event_terms = {t["local_name"]: _term_from_dict(t) for t in e["terms"]}
        events[e["id"]] = EventType(
            id=e["id"],
            label=e["label"],
            predicate_local_name=e["predicate_local_name"],
            terms=event_terms,
            identifier_term=e.get("identifier_term"),
        )
    return Schema(
        id=d["id"],
        prefix=d["prefix"],
        namespace_uri=d["namespace_uri"],
        terms=terms,
        events=events,
    )


class SchemaRegistry:
    """Loads Schema definitions from JSON files under `search_dirs`, in
    order -- later directories can override earlier ones by schema id, so a
    project- or user-local directory can be passed ahead of the bundled
    one to add or override schemas without touching the Arkivar install."""

    def __init__(self, search_dirs: Optional[list[Path]] = None):
        self.search_dirs = search_dirs or [BUNDLED_SCHEMA_DIR]
        self._cache: dict[str, Schema] = {}

    def available(self) -> list[str]:
        ids: set[str] = set()
        for d in self.search_dirs:
            if d.is_dir():
                ids.update(p.stem for p in d.glob("*.json"))
        return sorted(ids)

    def get(self, schema_id: str) -> Schema:
        if schema_id in self._cache:
            return self._cache[schema_id]
        for d in reversed(self.search_dirs):
            path = d / f"{schema_id}.json"
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    schema = _schema_from_dict(json.load(f))
                self._cache[schema_id] = schema
                return schema
        raise ValueError(
            f"No schema named {schema_id!r} found in "
            f"{[str(d) for d in self.search_dirs]}. "
            f"Available: {self.available()}"
        )

    def load(self, schema_ids: list[str]) -> dict[str, Schema]:
        return {sid: self.get(sid) for sid in schema_ids}
