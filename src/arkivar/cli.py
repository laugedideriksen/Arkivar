# PYTHON_ARGCOMPLETE_OK
import argparse
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator
from .init_dir import init_dir
from .main import ingest, bag_project, requeue_quarantine
from .schema import SchemaRegistry

try:  # optional: tab completion, see `pip install argcomplete`
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None

__version__ = "0.1.0"

# Version of the --json output format. Bump on breaking changes to field names
# or meanings; adding new fields is not breaking.
JSON_SCHEMA_VERSION = 1


@contextlib.contextmanager
def _stdout_reserved(args: argparse.Namespace) -> Iterator[None]:
    """In --json mode, stdout carries exactly one JSON document.

    The pipeline prints progress to stdout, so while it runs, send stdout to
    stderr instead -- both Python-level prints and anything written by child
    processes (exiftool, rsync) that inherit file descriptor 1.
    """
    if not args.json:
        yield
        return
    sys.stdout.flush()
    sys.stderr.flush()
    saved_fd = os.dup(1)
    try:
        os.dup2(2, 1)
        with contextlib.redirect_stdout(sys.stderr):
            yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_fd, 1)
        os.close(saved_fd)


def _payload(
    command: str,
    project: Path,
    exit_code: int,
    status: str,
    error: str | None = None,
    warnings: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "project": str(Path(project).resolve()),
        "error": error,
        "warnings": warnings or [],
        **extra,
    }


def _emit(args: argparse.Namespace, payload: dict[str, Any]) -> int:
    """Print the JSON document (in --json mode) and return the exit code."""
    if args.json:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    return payload["exit_code"]


def _fail(
    args: argparse.Namespace,
    command: str,
    project: Path,
    message: str,
    warnings: list[str] | None = None,
    **extra: Any,
) -> int:
    """Report that the command could not run (bad input or an exception)."""
    if not args.json:
        print(f"arkivar {command}: {message}", file=sys.stderr)
    return _emit(
        args,
        _payload(
            command, project, 1, "failed", error=message, warnings=warnings, **extra
        ),
    )


def _report_fields(report) -> dict[str, Any]:
    return {
        "ingested": [str(p) for p in report.ingested],
        "quarantined": [str(p) for p in report.quarantined],
        "errored": [{"path": str(p), "reason": r} for p, r in report.errored],
        "counts": {
            "ingested": len(report.ingested),
            "quarantined": len(report.quarantined),
            "errored": len(report.errored),
        },
    }


def cmd_init(args: argparse.Namespace) -> int:
    """Initialise a new Arkivar project directory."""
    warnings: list[str] = []
    requested: list[str] = args.schemas or []
    schema_ids: list[str] = list(dict.fromkeys(requested))
    duplicates = [sid for sid in schema_ids if requested.count(sid) > 1]
    if duplicates:
        warnings.append(
            f"schema(s) given more than once: {', '.join(duplicates)}. "
            f"Each is used only once."
        )
        if not args.json:
            print(f"arkivar init: {warnings[-1]}", file=sys.stderr)
    if schema_ids:
        available = SchemaRegistry().available()
        unknown = [sid for sid in schema_ids if sid not in available]
        if unknown:
            return _fail(
                args,
                "init",
                args.project_path,
                f"unknown schema(s): {', '.join(unknown)}. "
                f"Available: {', '.join(available)}",
                warnings=warnings,
                schemas=schema_ids,
            )

    try:
        with _stdout_reserved(args):
            init_dir(args.project_path, schema_ids=schema_ids or None)
    except Exception as e:
        return _fail(
            args,
            "init",
            args.project_path,
            f"failed to initialise {args.project_path}: {e}",
            warnings=warnings,
            schemas=schema_ids,
        )
    return _emit(
        args,
        _payload(
            "init",
            args.project_path,
            0,
            "ok",
            warnings=warnings,
            schemas=schema_ids,
        ),
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest a file or directory into an Arkivar project."""
    extra = {"source": str(args.source_path.resolve())}
    if not args.source_path.exists():
        return _fail(
            args,
            "ingest",
            args.project_path,
            f"source path does not exist: {args.source_path}",
            **extra,
        )

    try:
        with _stdout_reserved(args):
            report = ingest(args.source_path, args.project_path)
    except Exception as e:
        return _fail(
            args, "ingest", args.project_path, f"ingestion failed: {e}", **extra
        )

    if not args.json:
        if report.quarantined:
            print(
                f"arkivar ingest: {len(report.quarantined)} file(s) in quarantine/. "
                f"Fix them, then run: arkivar requeue {args.project_path}",
                file=sys.stderr,
            )
        for path, reason in report.errored:
            print(f"arkivar ingest: error: {path} ({reason})", file=sys.stderr)

    # Quarantined files are an expected outcome, so only errors fail the run.
    if report.errored:
        exit_code, status = 1, "errors"
    elif report.quarantined:
        exit_code, status = 0, "quarantined"
    else:
        exit_code, status = 0, "ok"
    return _emit(
        args,
        _payload(
            "ingest",
            args.project_path,
            exit_code,
            status,
            **extra,
            **_report_fields(report),
        ),
    )


def cmd_requeue(args: argparse.Namespace) -> int:
    """Re-validate quarantined files and pass any that now succeed through the pipeline."""
    if not args.project_path.exists():
        return _fail(
            args,
            "requeue",
            args.project_path,
            f"project path does not exist: {args.project_path}",
        )

    try:
        with _stdout_reserved(args):
            report = requeue_quarantine(args.project_path)
    except Exception as e:
        return _fail(args, "requeue", args.project_path, f"requeue failed: {e}")

    if not args.json:
        print(
            f"Requeue complete: {len(report.ingested)} files organised, "
            f"{len(report.errored)} still in quarantine or failed."
        )
        for path, reason in report.errored:
            print(f"arkivar requeue: {path} ({reason})", file=sys.stderr)

    # Note: requeue_quarantine reports files that still fail validation under
    # `errored` (reason "still fails validation"), not under `quarantined`.
    exit_code, status = (1, "errors") if report.errored else (0, "ok")
    return _emit(
        args,
        _payload(
            "requeue",
            args.project_path,
            exit_code,
            status,
            **_report_fields(report),
        ),
    )


def cmd_bag(args: argparse.Namespace) -> int:
    """Package a finished project directory as a BagIt bag."""
    extra = {"cleanup": args.cleanup}
    try:
        with _stdout_reserved(args):
            bag_path = bag_project(args.project_path, args.output, cleanup=args.cleanup)
    except Exception as e:
        return _fail(args, "bag", args.project_path, f"bagging failed: {e}", **extra)
    return _emit(
        args,
        _payload(
            "bag",
            args.project_path,
            0,
            "ok",
            bag_path=str(Path(bag_path).resolve()) if bag_path else None,
            **extra,
        ),
    )


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

    # Options shared by every subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        help=(
            "Write a single machine-readable JSON document to stdout (progress "
            "output goes to stderr). Exit codes are unchanged."
        ),
    )

    # --- init ---
    init_parser = subparsers.add_parser(
        "init",
        parents=[common],
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
        parents=[common],
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
        parents=[common],
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
        parents=[common],
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
        if args.json:
            return _emit(
                args,
                _payload(
                    args.command,
                    getattr(args, "project_path", Path.cwd()),
                    130,
                    "failed",
                    error="interrupted",
                ),
            )
        print("\narkivar: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
