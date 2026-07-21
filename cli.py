"""Command-line interface for Arkivar.

Typical workflow:
    1. arkivar init PROJECT        Set up a new project directory.
    2. Manually fill out PROJECT/metadata.json.
    3. arkivar ingest SOURCE PROJECT   Ingest a file or directory into the project.
    4. arkivar bag PROJECT         Package the finished project as a BagIt bag.
"""

import argparse
import sys
from pathlib import Path

from init_dir import init_dir
from main import ingest, bag_project

__version__ = "0.1.0"


def cmd_init(args: argparse.Namespace) -> int:
    """Initialise a new Arkivar project directory."""
    try:
        init_dir(args.project_path)
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
        ingest(args.source_path, args.project_path)
    except Exception as e:
        print(f"arkivar ingest: ingestion failed: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_bag(args: argparse.Namespace) -> int:
    """Package a finished project directory as a BagIt bag."""
    try:
        bag_project(args.project_path)
    except Exception as e:
        print(f"arkivar bag: bagging failed: {e}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkivar",
        description=(
            "Arkivar: ingest, validate, and archive files with Dublin Core / RDF sidecars.\n\n"
            "Typical workflow:\n"
            "  1. arkivar init PROJECT\n"
            "  2. Manually fill out PROJECT/metadata.json\n"
            "  3. arkivar ingest SOURCE PROJECT\n"
            "  4. arkivar bag PROJECT"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"arkivar {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    # --- init ---
    init_parser = subparsers.add_parser(
        "init",
        help="Initialise a new project directory (staging/, quarantine/, data/, changelog.csv, metadata.json).",
        description="Create and initialise an Arkivar project directory.",
    )
    init_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory to initialise (default: current directory).",
    )
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
        "requeue-quarantine",
        help="Reevaluate all quarantined files, e.g. after manually renaming, and pass through the remaining pipeline after successful validation",
        description="Reevaluate quarantined files.",
    )
    requeue_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        defauslt=Path.cwd(),
        help="Project directory to bag (default: current directory).",
    )

    # --- bag ---
    bag_parser = subparsers.add_parser(
        "bag",
        help="Package a finished project directory as a BagIt bag. (Not yet implemented.)",
        description="Package a finished project directory as a BagIt bag.",
    )
    bag_parser.add_argument(
        "project_path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory to bag (default: current directory).",
    )
    bag_parser.set_defaults(func=cmd_bag)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\narkivar: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
