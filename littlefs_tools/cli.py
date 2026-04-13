"""CLI entry points for littlefs_tools."""

from __future__ import annotations

import argparse
import sys

from colorama import init

from littlefs_tools import __version__
from littlefs_tools._exceptions import LittleFSToolsError
from littlefs_tools._helpers import (
    _common_parser,
    _configure_logging,
    _legacy_parser,
    logger,
    parse_offset,
)
from littlefs_tools.operations import do_create, do_extract, do_list

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

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    try:
        offset = parse_offset(args.offset)

        if args.command == "create":
            do_create(
                source=args.source,
                image=args.image,
                block_size=args.block_size,
                block_count=args.block_count,
                offset=offset,
            )
        elif args.command == "list":
            do_list(
                image=args.image,
                block_size=args.block_size,
                block_count=args.block_count,
                offset=offset,
            )
        elif args.command == "extract":
            do_extract(
                image=args.image,
                block_size=args.block_size,
                block_count=args.block_count,
                offset=offset,
                destination=args.destination,
                force=args.force,
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
            block_size=args.block_size,
            block_count=args.block_count,
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
            block_size=args.block_size,
            block_count=args.block_count,
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
            block_size=args.block_size,
            block_count=args.block_count,
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
