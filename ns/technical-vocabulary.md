# Arkivar Technical Metadata Vocabulary

**Namespace URI:** `https://laugedideriksen.github.io/arkivar/ns/technical/v1#`
**Preferred prefix:** `arkivar`
**Version:** 1.0.0
**Status:** Draft — subject to change before Arkivar's first public release
**License:** [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) (public domain dedication)

This document is a human-friendly description of the RDFS/Turtle definition found at [ns/technical.ttl][https://laugedideriksen.github.io/arkivar/ns/technical/v1#].

For each file it ingests, _Arkivar_ generates an RDF/XML sidecar with two kinds of metadata:

- **Descriptive metadata**, expressed using [Dublin Core Terms](http://purl.org/dc/terms/) (`dcterms:`): e.g. title, creator, date, and similar fields concerned with discovery and identification.
- **Technical metadata**, extracted from the file itself via [ExifTool](https://exiftool.org/): e.g. exposure time, page count, and sample rate, which describe the characteristics of the file rather than what it is about.

As far as possible, everything is labelled using existing vocabularies.
Specifically the [EXIF RDF Schema](http://www.w3.org/2003/12/exif/ns#) (`exif`) for camera/image properties, and the [Nepomuk File Ontology](http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#) (`nfo:`) for cross-format properties such as page count, word count, sample rate, and channel count. This vocabulary is a fallback option covering everything else. As metadata standards evovle, it will hopefully become obsolete.

Terms in a published version are permanent, but new terms may be added along the way.
In the case of a breaking change, that will be publihed as a new major version at a new URI, with the older version left in place.

All terms below are `rdf:Property` instances (not further typed as `owl:DatatypeProperty` / `owl:ObjectProperty`).
Ranges are informative; Arkivar does not currently validate sidecar output against them.

## Terms

| Term | Label | Range | Description |
|---|---|---|---|
| `arkivar:fileSize` | file size | `xsd:integer` | Size of the file, in bytes. |
| `arkivar:lensMake` | lens make | `xsd:string` | Manufacturer of the lens used to capture an image. |
| `arkivar:lensModel` | lens model | `xsd:string` | Model name of the lens used to capture an image. |
| `arkivar:colorSpace` | color space | `xsd:string` | The color space encoding of an image (e.g. sRGB, Adobe RGB). |
| `arkivar:dngVersion` | DNG version | `xsd:string` | The version of the Adobe Digital Negative (DNG) specification a raw image file conforms to. |
| `arkivar:colorType` | color type | `xsd:string` | The pixel color type of a lossless image file (e.g. RGB, RGBA, Grayscale, Indexed). |
| `arkivar:compression` | compression | `xsd:string` | The compression scheme applied to a file's encoded data. |
| `arkivar:producer` | producer | `xsd:string` | The software or service that produced a document file, as distinct from the tool used to author its content. |
| `arkivar:creatorTool` | creator tool | `xsd:string` | The software application used to author or create the content of a file. |
| `arkivar:pdfVersion` | PDF version | `xsd:string` | The version of the PDF specification a file conforms to. |
| `arkivar:characterEncoding` | character encoding | `xsd:string` | The character encoding used by a plain-text or structured-text file (e.g. UTF-8). |
| `arkivar:bitsPerSample` | bits per sample | `xsd:integer` | The number of bits per audio sample. |
| `arkivar:bitrate` | bitrate | `xsd:string` | The average bitrate of a compressed audio or video stream. |
| `arkivar:encoder` | encoder | `xsd:string` | The software used to encode a compressed audio file. |
| `arkivar:frameRate` | frame rate | `xsd:string` | Framerate. |
| `arkivar:videoCodec` | video codec | `xsd:string` | The compression codec used to encode a file's video stream. |
| `arkivar:audioCodec` | audio codec | `xsd:string` | The compression codec used to encode a file's audio stream. |
