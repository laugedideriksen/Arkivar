# PYTHON_ARGCOMPLETE_OK
import argparse
import sys
from pathlib import Path
from .init_dir import init_dir
from .main import ingest, bag_project, requeue_quarantine
from .schema import SchemaRegistry

try:  # optional: tab completion, see `pip install argcomplete`
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None

__version__ = "0.1.0"


def cmd_init(args: argparse.Namespace) -> int:
    """Initialise a new Arkivar project directory."""
    requested: list[str] = args.schemas or []
    schema_ids: list[str] = list(dict.fromkeys(requested))
    duplicates = [sid for sid in schema_ids if requested.count(sid) > 1]
    if duplicates:
        print(
            f"arkivar init: schema(s) given more than once: {', '.join(duplicates)}. "
            f"Each is used only once.",
            file=sys.stderr,
        )
    if schema_ids:
        available = SchemaRegistry().available()
        unknown = [sid for sid in schema_ids if sid not in available]
        if unknown:
            print(
                f"arkivar init: unknown schema(s): {', '.join(unknown)}. "
                f"Available: {', '.join(available)}",
                file=sys.stderr,
            )
            return 1

    try:
        init_dir(args.project_path, schema_ids=schema_ids or None)
    except Exception as e:
        print(
            f"arkivar init: failed to initialise {args.project_path}: {e}",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest a file or directory into an Arkivar project."""
    if not args.source_path.exists():
        print(
            f"arkivar ingest: source path does not exist: {args.source_path}",
            file=sys.stderr,
        )
        return 1

    try:
        report = ingest(args.source_path, args.project_path)
    except Exception as e:
        print(f"arkivar ingest: ingestion failed: {e}", file=sys.stderr)
        return 1

    if report.quarantined:
        print(
            f"arkivar ingest: {len(report.quarantined)} file(s) in quarantine/. "
            f"Fix them, then run: arkivar requeue {args.project_path}",
            file=sys.stderr,
        )
    for path, reason in report.errored:
        print(f"arkivar ingest: error: {path} ({reason})", file=sys.stderr)
    # Quarantined files are an expected outcome, so only errors fail the run.
    return 1 if report.errored else 0


def cmd_requeue(args: argparse.Namespace) -> int:
    """Re-validate quarantined files and pass any that now succeed through the pipeline."""
    if not args.project_path.exists():
        print(
            f"arkivar requeue: project path does not exist: {args.project_path}",
            file=sys.stderr,
        )
        return 1

    try:
        report = requeue_quarantine(args.project_path)
    except Exception as e:
        print(f"arkivar requeue: requeue failed: {e}", file=sys.stderr)
        return 1

    print(
        f"Requeue complete: {len(report.ingested)} files organised, "
        f"{len(report.errored)} still in quarantine or failed."
    )
    for path, reason in report.errored:
        print(f"arkivar requeue: {path} ({reason})", file=sys.stderr)
    return 1 if report.errored else 0


def cmd_bag(args: argparse.Namespace) -> int:
    """Package a finished project directory as a BagIt bag."""
    try:
        bag_project(args.project_path, args.output, cleanup=args.cleanup)
    except Exception as e:
        print(f"arkivar bag: bagging failed: {e}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkivar",
        description=(
            "Arkivar: ingest, validate, and archive files with RDF/XML sidecars and BagIt packaging.\n\n"
            "Typical workflow:\n"
            "  1. arkivar init PROJECT\n"
            "  2. Manually fill out PROJECT/metadata.json\n"
            "  3. arkivar ingest SOURCE PROJECT\n"
            "  4. arkivar requeue PROJECT   (only if files were quarantined)\n"
            "  5. arkivar bag PROJECT"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"arkivar {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    # --- init ---
    init_parser = subparsers.add_parser(
        "init",
        help="Initialise a new project directory (staging/, quarantine/, data/, changelog.csv, metadata.json).",
        description=(
            "Create and initialise an Arkivar project directory. Existing files and "
            "directories are not overwritten."
        ),
    )
    init_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory to initialise (default: current directory).",
    )
    schema_arg = init_parser.add_argument(
        "-s",
        "--schema",
        dest="schemas",
        action="append",
        metavar="SCHEMA_ID",
        default=None,
        help=(
            "Metadata schema to include in metadata.json. Repeat to combine "
            "several (default: dcterms). Available: "
            + ", ".join(SchemaRegistry().available())
            + ". Ignored if metadata.json already exists."
        ),
    )
    # Evaluated at TAB time, so newly added schemas/*.json show up immediately.
    schema_arg.completer = lambda **_: SchemaRegistry().available()  # type: ignore[attr-defined]
    init_parser.set_defaults(func=cmd_init)

    # --- ingest ---
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest a file or directory: stage, validate, extract metadata, build a sidecar, and organise.",
        description="Ingest a file or directory into an Arkivar project.",
    )
    ingest_parser.add_argument(
        "source_path",
        type=Path,
        help="File or directory to ingest.",
    )
    ingest_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Target project directory (default: current directory).",
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # --- requeue ---
    requeue_parser = subparsers.add_parser(
        "requeue",
        help="Re-validate quarantined files (e.g. after renaming them) and pass any that now succeed through the rest of the pipeline.",
        description=(
            "Re-evaluate every file in quarantine/. Files that now pass validation "
            "are processed and organised into data/; files that still fail are left in place."
        ),
    )
    requeue_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory whose quarantine/ to re-evaluate (default: current directory).",
    )
    requeue_parser.set_defaults(func=cmd_requeue)

    # --- bag ---
    bag_parser = subparsers.add_parser(
        "bag",
        help="Package a finished project as a BagIt bag (data/ as payload; metadata.json and changelog.csv as tag files).",
        description=(
            "Package a finished project directory as a BagIt bag. The bag is created "
            "next to the project directory as PROJECT_bag unless --output is given."
        ),
    )
    bag_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory to bag (default: current directory).",
    )
    bag_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Where to create the bag (default: PROJECT_bag next to the project directory). Must not already exist.",
    )
    bag_parser.add_argument(
        "--cleanup",
        choices=["none", "scratch", "full"],
        default="none",
        help="What to remove after a successful bag: 'none' leaves staging/, quarantine/, and the project directory untouched (default); 'scratch' removes staging/ and quarantine/ only if they're already empty; 'full' deletes the entire project directory, including metadata.json and changelog.csv, once the bag has been validated.",
    )
    bag_parser.set_defaults(func=cmd_bag)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argcomplete is not None:
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\narkivar: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
