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
    load_config,
    logger,
    parse_offset,
    parse_size,
    sizeof_fmt,
)
from littlefs_tools.operations import (
    do_add,
    do_cat,
    do_create,
    do_diff,
    do_du,
    do_extract,
    do_gc,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_getattr,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_grow,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_info,
    do_list,
    do_remove,
    do_removeattr,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_rename,
    do_repair,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_setattr,  # noqa: F401 (used by Task 6 CLI dispatch)
    do_verify,
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
    parser.add_argument("--config", dest="config_file", help="JSON or YAML config file for default options")
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
    sp_create.add_argument(
        "--name-max", dest="name_max", type=int, default=0,
        help="max filename length (0=default 255)",
    )
    sp_create.add_argument(
        "--file-max", dest="file_max", type=int, default=0,
        help="max file size (0=unlimited)",
    )
    sp_create.add_argument(
        "--attr-max", dest="attr_max", type=int, default=0,
        help="max attribute size (0=default)",
    )
    sp_create.add_argument(
        "--read-size", dest="read_size", type=int, default=0,
        help="read size (0=default)",
    )
    sp_create.add_argument(
        "--prog-size", dest="prog_size", type=int, default=0,
        help="prog size (0=default)",
    )
    sp_create.add_argument(
        "--cache-size", dest="cache_size", type=int, default=0,
        help="cache size (0=default)",
    )
    sp_create.add_argument(
        "--lookahead-size", dest="lookahead_size", type=int, default=0,
        help="lookahead size (0=default)",
    )
    sp_create.add_argument(
        "--block-cycles", dest="block_cycles", type=int, default=-1,
        help="block cycles (-1=disable wear leveling)",
    )
    sp_create.add_argument(
        "--disk-version", dest="disk_version", type=int, default=0,
        help="disk version (0=latest)",
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
    sp_extract.add_argument(
        "--file",
        dest="extract_paths",
        nargs="*",
        help="specific file path(s) to extract",
    )
    sp_extract.add_argument(
        "--pattern",
        dest="extract_pattern",
        help="glob pattern to filter files (e.g. '*.txt')",
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

    # -- verify --------------------------------------------------------
    sp_verify = subparsers.add_parser(
        "verify",
        parents=[parent],
        help="validate image integrity",
        description="Check a littleFS image for corruption and consistency.",
    )
    sp_verify.add_argument(
        "-i", "--image",
        dest="image",
        help="image file name",
        required=True,
    )

    # -- diff ----------------------------------------------------------
    sp_diff = subparsers.add_parser(
        "diff",
        parents=[parent],
        help="compare two images",
        description="Compare two littleFS images and show differences.",
    )
    sp_diff.add_argument(
        "image1",
        help="first image file",
    )
    sp_diff.add_argument(
        "image2",
        help="second image file",
    )
    sp_diff.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
        help="output format",
    )

    # -- attr ----------------------------------------------------------
    sp_attr = subparsers.add_parser(
        "attr",
        parents=[parent],
        help="manage extended attributes",
        description="Get, set, or remove extended attributes on files "
        "in a littleFS image.",
    )
    sp_attr.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True,
    )
    sp_attr.add_argument(
        "--action", choices=["get", "set", "remove"], required=True,
        help="action to perform",
    )
    sp_attr.add_argument("--path", required=True, help="path inside the image")
    sp_attr.add_argument(
        "--type", dest="attr_type", type=int, required=True,
        help="attribute type ID (0-255)",
    )
    sp_attr.add_argument(
        "--data", dest="attr_data",
        help="attribute data as hex string (for set)",
    )

    # -- gc ------------------------------------------------------------
    sp_gc = subparsers.add_parser(
        "gc",
        parents=[parent],
        help="run garbage collection",
        description="Run garbage collection on a littleFS image.",
    )
    sp_gc.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True,
    )

    # -- grow ----------------------------------------------------------
    sp_grow = subparsers.add_parser(
        "grow",
        parents=[parent],
        help="grow image size",
        description="Grow a littleFS image to a larger size.",
    )
    sp_grow.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True,
    )
    sp_grow_size = sp_grow.add_mutually_exclusive_group(required=True)
    sp_grow_size.add_argument(
        "--new-block-count", dest="new_block_count", type=int,
        help="target block count",
    )
    sp_grow_size.add_argument(
        "--new-size", dest="new_size", help="target size (e.g. 512kb, 1mb)",
    )

    # -- repair --------------------------------------------------------
    sp_repair = subparsers.add_parser(
        "repair",
        parents=[parent],
        help="repair inconsistent image",
        description="Run mkconsistent on a littleFS image.",
    )
    sp_repair.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True,
    )

    args = parser.parse_args(argv)

    # Merge config file if specified
    if args.config_file:
        config = load_config(args.config_file)
        for key, value in config.items():
            key = key.replace("-", "_")
            # CLI args take precedence (non-default values)
            if not hasattr(args, key) or getattr(args, key) is None:
                setattr(args, key, value)

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
                    name_max=args.name_max,
                    file_max=args.file_max,
                    attr_max=args.attr_max,
                    read_size=args.read_size,
                    prog_size=args.prog_size,
                    cache_size=args.cache_size,
                    lookahead_size=args.lookahead_size,
                    block_cycles=args.block_cycles,
                    disk_version=args.disk_version,
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
                    paths=getattr(args, "extract_paths", None),
                    pattern=getattr(args, "extract_pattern", None),
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
            elif args.command == "verify":
                result = do_verify(
                    image=args.image,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
                if result["valid"]:
                    print(f"Image {args.image} is valid")
                    print(f"  Checks passed: {', '.join(result['checks_passed'])}")
                else:
                    print(f"Image {args.image} has errors:")
                    for err in result["errors"]:
                        print(f"  ERROR: {err}")
                    sys.exit(1)
            elif args.command == "diff":
                diff_result = do_diff(
                    image1=args.image1,
                    image2=args.image2,
                    block_size=block_size,
                    block_count=block_count,
                    offset=offset,
                )
                if args.output_format == "json":
                    import json
                    print(json.dumps(diff_result, indent=2))
                else:
                    if diff_result["only_in_1"]:
                        print(f"Only in {args.image1}:")
                        for p in diff_result["only_in_1"]:
                            print(f"  - {p}")
                    if diff_result["only_in_2"]:
                        print(f"Only in {args.image2}:")
                        for p in diff_result["only_in_2"]:
                            print(f"  + {p}")
                    if diff_result["different"]:
                        print("Modified:")
                        for p in diff_result["different"]:
                            print(f"  ~ {p}")
                    if (
                        not diff_result["only_in_1"]
                        and not diff_result["only_in_2"]
                        and not diff_result["different"]
                    ):
                        print("Images are identical")
            elif args.command == "attr":
                if args.action == "get":
                    data = do_getattr(
                        image=args.image, path=args.path,
                        attr_type=args.attr_type,
                        block_size=block_size, block_count=block_count,
                        offset=offset,
                    )
                    print(data.hex())
                elif args.action == "set":
                    if not args.attr_data:
                        print(
                            "Error: --data required for set action",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                    do_setattr(
                        image=args.image, path=args.path,
                        attr_type=args.attr_type,
                        data=bytes.fromhex(args.attr_data),
                        block_size=block_size, block_count=block_count,
                        offset=offset,
                    )
                    print(f"Set attr type {args.attr_type} on {args.path}")
                elif args.action == "remove":
                    do_removeattr(
                        image=args.image, path=args.path,
                        attr_type=args.attr_type,
                        block_size=block_size, block_count=block_count,
                        offset=offset,
                    )
                    print(
                        f"Removed attr type {args.attr_type} from {args.path}"
                    )
            elif args.command == "gc":
                used = do_gc(
                    image=args.image, block_size=block_size,
                    block_count=block_count, offset=offset,
                )
                print(f"Garbage collection complete. Used blocks: {used}")
            elif args.command == "grow":
                do_grow(
                    image=args.image,
                    new_block_count=getattr(args, "new_block_count", None),
                    new_size=getattr(args, "new_size", None),
                    block_size=block_size, block_count=block_count,
                    offset=offset,
                )
            elif args.command == "repair":
                do_repair(
                    image=args.image, block_size=block_size,
                    block_count=block_count, offset=offset,
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
