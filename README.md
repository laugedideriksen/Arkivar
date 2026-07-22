# Arkivar

`Arkivar` is a CLI tool for transparently ingesting and archiving files and directories.
On ingesting a file, _Arkivar_ validates its filetype, extracts its metadata, creates a sidecar file in RDF/XML, and organises it in a `BagIt` compliant file structure.
Every step is automatically documented in `changelog.csv`.
`Arkivar` can also archive a project in the `BagIt` format.
In that case, the changelog and project metadata files are included as tag-files.

Although it is primarily intended to be used as a CLI application, _Arkivar_ can also be imported as a Python module.

**NOTE**: Although functional, this tool is still under development, and many filetypes may still not parse correctly into RDF/XML.

## Intended Workflow

1. Create a project directory.
2. Initialise directory with `arkivar init [path_to_project]`; this will create three directories, `staging/`, `quarantine/`, and `data/`, as well as two files, `changelog.csv` and `metadata.json`.
If any of these already exists, they will not be overwritten.
3. Edit metadata.json with a text editor of your choice to contain all relevant project information.
Any unedited fields will be excluded from the generated sidecar files.
4. Run `arkivar ingest [path_to_data_source] [path_to_project]` on any file or directory.
If you need to ingest data from several sources, do it one at a time.
5. Once everything has been ingested, `arkivar requeue [path_to_project]` checks the `quarantine/` directory for any files that failed file validation.
Files that now pass, e.g. because their file extensions have been manually changed, are passed through the remaining pipeline.
6. To 'bag' a project, run `arkivar bag [path_to_project]`.
`arkivar bag` has the flag `--cleanup`, which takes one of three arguments: `none` (default), `scratch`, and `full`. 
`none` does nothing; `scratch` deletes `staging/` and `quarantine/` if they are empty; `full` deletes the entire ingest directory once the bagged version is validated.

## Quickstart

```bash
mkdir ~/project
arkivar init ~/project/
# edit ~/project/metadata.json
arkivar ingest /media/user/sd1/ ~/project/
arkivar bag ~/project/
```

## Namespace Selection

When Arkivar maps an extracted field to RDF, it follows this order of preference:

1. Use `dcterms:` if the field is descriptive (about the resource's identity or context), not technical.
2. Use `exif:` if the field is a standard EXIF 2.2 property.
3. Use `nfo:` if the field has a defined Nepomuk File Ontology equivalent.
4. Otherwise, use this vocabulary (`arkivar:`) as the fallback.

## Installation and requirements
`Arkivar` is currently only tested on Linux.
In addition to Python 3.10 or newer, `Arkivar` requires the modules `bagit`, `puremagic`, and `rdflib`.
It also requires the CLI tools `rsync` and `exiftool` to be available on `PATH`.
