"""CLI entry points for littlefs_tools."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys

from colorama import init

from littlefs_tools import __version__
from littlefs_tools._exceptions import LittleFSToolsError, ValidationError
from littlefs_tools._helpers import (
    _common_parser,
    _configure_logging,
    _legacy_parser,
    logger,
    parse_offset,
    parse_size,
    sizeof_fmt,
)
from littlefs_tools.operations import (
    do_add,  # noqa: F401 (used by Task 4 CLI dispatch)
    do_cat,
    do_create,
    do_du,
    do_extract,
    do_info,
    do_list,
    do_remove,  # noqa: F401 (used by Task 4 CLI dispatch)
    do_rename,  # noqa: F401 (used by Task 4 CLI dispatch)
)

# ---------------------------------------------------------------------------
# CLI: unified subcommand interface
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Unified CLI entry point: ``littlefs {create,list,extract}``."""
    init(autoreset=True)

    parent = _common_parser()

    parser = argparse.ArgumentParser(
        prog="littlefs",
        description="Tools to create, view, and extract littleFS filesystem images",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- create --------------------------------------------------------
    sp_create = subparsers.add_parser(
        "create",
        parents=[parent],
        help="create a littleFS image from a source directory",
        description="Package a directory into a littleFS binary image.",
    )
    sp_create.add_argument(
        "-s", "--source",
        dest="source",
        help="source directory path",
        required=True,
    )
    sp_create.add_argument(
        "-i", "--image",
        dest="image",
        help="output image file name",
        required=True,
    )
    sp_create.add_argument(
        "--compact",
        action="store_true",
        help="trim image to used blocks only",
    )

    # -- list ----------------------------------------------------------
    sp_list = subparsers.add_parser(
        "list",
        parents=[parent],
        help="list files in a littleFS image",
        description="Display the file tree of a littleFS binary image.",
    )
    sp_list.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_list.add_argument(
        "--format",
        dest="output_format",
        choices=["tree", "json", "csv"],
        default="tree",
        help="output format (default: tree)",
    )

    # -- extract -------------------------------------------------------
    sp_extract = subparsers.add_parser(
        "extract",
        parents=[parent],
        help="extract files from a littleFS image",
        description="Extract all files from a littleFS binary image to a directory.",
    )
    sp_extract.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_extract.add_argument(
        "-d", "--destination",
        dest="destination",
        help="destination directory to extract into",
        required=True,
    )
    sp_extract.add_argument(
        "-f", "--force",
        help="force extract even if destination is not empty",
        action="store_true",
    )

    # -- info ----------------------------------------------------------
    sp_info = subparsers.add_parser(
        "info",
        parents=[parent],
        help="show image metadata",
        description="Display metadata about a littleFS binary image.",
    )
    sp_info.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_info.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )

    # -- cat -----------------------------------------------------------
    sp_cat = subparsers.add_parser(
        "cat",
        parents=[parent],
        help="print file contents from image",
        description="Print the contents of a file inside a littleFS image to stdout.",
    )
    sp_cat.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_cat.add_argument(
        "path",
        help="path to file inside the image",
    )
    sp_cat.add_argument(
        "--binary",
        action="store_true",
        help="output raw bytes (no UTF-8 decode)",
    )

    # -- du ------------------------------------------------------------
    sp_du = subparsers.add_parser(
        "du",
        parents=[parent],
        help="show disk usage",
        description="Show per-directory disk usage for a littleFS image.",
    )
    sp_du.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_du.add_argument(
        "path",
        nargs="?",
        default="/",
        help="starting directory (default: /)",
    )
    sp_du.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )

    # -- add -----------------------------------------------------------
    sp_add = subparsers.add_parser(
        "add",
        parents=[parent],
        help="add files to an existing image",
        description="Add files or directories to an existing littleFS image.",
    )
    sp_add.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_add.add_argument(
        "-s", "--source",
        dest="sources",
        nargs="+",
        help="source file(s) or directory(ies) to add",
        required=True,
    )
    sp_add.add_argument(
        "--dest",
        dest="dest",
        default="/",
        help="destination directory inside image (default: /)",
    )

    # -- remove --------------------------------------------------------
    sp_remove = subparsers.add_parser(
        "remove",
        parents=[parent],
        help="remove files from an image",
        description="Remove files or directories from a littleFS image.",
    )
    sp_remove.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_remove.add_argument(
        "paths",
        nargs="+",
        help="path(s) inside the image to remove",
    )
    sp_remove.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="remove directories recursively",
    )

    # -- rename --------------------------------------------------------
    sp_rename = subparsers.add_parser(
        "rename",
        parents=[parent],
        help="rename/move within image",
        description="Rename or move a file/directory within a littleFS image.",
    )
    sp_rename.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    sp_rename.add_argument(
        "src",
        help="current path inside the image",
    )
    sp_rename.add_argument(
        "dst",
        help="new path inside the image",
    )

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    try:
        offset = parse_offset(args.offset)

        # Resolve --fs-size vs --block_count
        block_size = args.block_size
        block_count = args.block_count

        if args.fs_size is not None:
            if args.block_count is not None:
                raise ValidationError(
                    "Cannot specify both --block_count and --fs-size"
                )
            fs_bytes = parse_size(args.fs_size)
            bs = block_size if block_size is not None else 4096
            block_count = fs_bytes // bs

        ctx = contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext()
        with ctx:
            if args.command == "create":
                # Apply defaults for create (create always needs explicit values)
                if block_size is None:
                    block_size = 4096
                if block_count is None:
                    block_count = 64
                do_create(
                    source=args.source,
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                    compact=args.compact,
                )
            elif args.command == "list":
                do_list(
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                    output_format=args.output_format,
                )
            elif args.command == "extract":
                do_extract(
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                    destination=args.destination,
                    force=args.force,
                )
            elif args.command == "info":
                info = do_info(
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
                if args.output_format == "json":
                    import json
                    print(json.dumps(info, indent=2))
                else:
                    for key, val in info.items():
                        if key in ("total_size", "used_size", "free_size", "content_bytes"):
                            print(f"  {key:20s}: {sizeof_fmt(val)} ({val} bytes)")
                        elif key == "used_pct":
                            print(f"  {key:20s}: {val}%")
                        else:
                            print(f"  {key:20s}: {val}")
            elif args.command == "cat":
                data = do_cat(
                    image=args.image,
                    path=args.path,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
                if args.binary:
                    sys.stdout.buffer.write(data)
                else:
                    sys.stdout.write(data.decode("utf-8", errors="replace"))
            elif args.command == "du":
                results = do_du(
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                    path=args.path,
                )
                if args.output_format == "json":
                    import json
                    print(json.dumps(results, indent=2))
                else:
                    for entry in results:
                        print(
                            f"  {sizeof_fmt(entry['bytes']):>10s}  "
                            f"{entry['files']:3d} files  "
                            f"{entry['dirs']:3d} dirs  "
                            f"{entry['path']}"
                        )
            elif args.command == "add":
                do_add(
                    image=args.image,
                    sources=args.sources,
                    dest=args.dest,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
            elif args.command == "remove":
                do_remove(
                    image=args.image,
                    paths=args.paths,
                    recursive=args.recursive,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
            elif args.command == "rename":
                do_rename(
                    image=args.image,
                    src_path=args.src,
                    dst_path=args.dst,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
    except LittleFSToolsError as exc:
        logger.critical("%s", exc)
        sys.exit(1)
    except FileNotFoundError as exc:
        logger.critical("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error: %s", exc)
        logger.debug("Traceback:", exc_info=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Legacy CLI entry points (backward-compatible)
# ---------------------------------------------------------------------------

def create_image() -> None:
    """Legacy entry point for ``littlefs_create``."""
    init(autoreset=True)
    parser = _legacy_parser(
        "Tool to generate lfs images from a source folder",
        "littlefs_create",
    )
    parser.add_argument(
        "-i", "--image",
        dest="image",
        help="output image file name",
        required=True,
    )
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "-s", "--source",
        dest="source",
        help="source path",
        required=True,
    )
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        offset = parse_offset(args.offset)
        do_create(
            source=args.source,
            image=args.image,
            block_size=args.block_size or 4096,
            block_count=args.block_count or 64,
            offset=offset,
        )
    except (LittleFSToolsError, FileNotFoundError) as exc:
        logger.critical("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error: %s", exc)
        logger.debug("Traceback:", exc_info=True)
        sys.exit(2)


def list_files() -> None:
    """Legacy entry point for ``littlefs_list``."""
    init(autoreset=True)
    parser = _legacy_parser(
        "Tool to list files in a littlefs file image",
        "littlefs_list",
    )
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        offset = parse_offset(args.offset)
        do_list(
            image=args.image,
            block_size=args.block_size or 4096,
            block_count=args.block_count or 64,
            offset=offset,
        )
    except (LittleFSToolsError, FileNotFoundError) as exc:
        logger.critical("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error: %s", exc)
        logger.debug("Traceback:", exc_info=True)
        sys.exit(2)


def extract_files() -> None:
    """Legacy entry point for ``littlefs_extract``."""
    init(autoreset=True)
    parser = _legacy_parser(
        "Tool to extract files from a littlefs file image",
        "littlefs_extract",
    )
    parser.add_argument(
        "-f", "--force",
        help="force extract even if destination folder is not empty",
        action="store_true",
    )
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )
    required.add_argument(
        "-d", "--destination",
        dest="destination",
        help="destination directory to extract the contents into",
        required=True,
    )
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        offset = parse_offset(args.offset)
        do_extract(
            image=args.image,
            block_size=args.block_size or 4096,
            block_count=args.block_count or 64,
            offset=offset,
            destination=args.destination,
            force=args.force,
        )
    except (LittleFSToolsError, FileNotFoundError) as exc:
        logger.critical("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error: %s", exc)
        logger.debug("Traceback:", exc_info=True)
        sys.exit(2)
