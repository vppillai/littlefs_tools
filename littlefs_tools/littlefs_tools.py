"""Tools to create, view, and extract littleFS filesystem images.

Provides three operations:
- create: Package a directory into a littleFS binary image.
- list: Display the file tree of a littleFS binary image.
- extract: Extract all files from a littleFS binary image.

Can be invoked as ``littlefs create|list|extract`` (unified CLI)
or via the legacy commands ``littlefs_create``, ``littlefs_list``,
``littlefs_extract``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from colorama import Fore, init
from littlefs import LittleFS

from littlefs_tools import __version__

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LFS_TYPE_FILE: int = 1
LFS_TYPE_DIR: int = 2

READ_CHUNK_SIZE: int = 4096

logger = logging.getLogger("littlefs_tools")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LittleFSToolsError(Exception):
    """Base exception for littlefs_tools errors."""


class ImageTooSmallError(LittleFSToolsError):
    """Raised when the source contents exceed the image capacity."""


class ValidationError(LittleFSToolsError):
    """Raised when an argument fails validation."""


class DestinationNotEmptyError(LittleFSToolsError):
    """Raised when the extraction destination is not empty and --force is not set."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sizeof_fmt(num: float, suffix: str = "B") -> str:
    """Return a human-readable file size string.

    Args:
        num: Size in bytes.
        suffix: Unit suffix (default ``"B"``).

    Returns:
        Formatted size string, e.g. ``"4.0 KiB"``.
    """
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


def parse_offset(value: str) -> int:
    """Convert an offset string to an integer, supporting hex (``0x...``) notation.

    Args:
        value: Offset as a decimal or hex string.

    Returns:
        Integer offset value.

    Raises:
        ValidationError: If *value* cannot be parsed as an integer.
    """
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValidationError(f"Invalid offset value: {value!r}") from exc


def validate_block_size(block_size: int) -> None:
    """Validate that *block_size* is a positive power of two.

    Raises:
        ValidationError: If validation fails.
    """
    if block_size <= 0 or (block_size & (block_size - 1)) != 0:
        raise ValidationError(
            f"Block size must be a positive power of 2, got {block_size}"
        )


def validate_block_count(block_count: int) -> None:
    """Validate that *block_count* is a positive integer.

    Raises:
        ValidationError: If validation fails.
    """
    if block_count <= 0:
        raise ValidationError(
            f"Block count must be a positive integer, got {block_count}"
        )


def _configure_logging(verbose: bool) -> None:
    """Set up the module logger.

    Args:
        verbose: If ``True``, set level to DEBUG; otherwise WARNING.
    """
    logging.basicConfig(format="%(levelname)s - %(lineno)d - %(message)s")
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Shared argument parser
# ---------------------------------------------------------------------------

def _common_parser() -> argparse.ArgumentParser:
    """Return a parent parser containing arguments shared by all subcommands.

    Shared arguments: ``-b/--block_size``, ``-c/--block_count``,
    ``-o/--offset``, ``-v/--verbose``.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-b", "--block_size",
        dest="block_size",
        help="block size of the LFS image (defaults to 4096)",
        type=int,
        default=4096,
    )
    parser.add_argument(
        "-c", "--block_count",
        dest="block_count",
        help="block count of the LFS image (defaults to 64)",
        type=int,
        default=64,
    )
    parser.add_argument(
        "-o", "--offset",
        dest="offset",
        help=(
            "offset (in bytes) from which the littlefs image starts "
            "(defaults to 0). Hex values are supported (e.g. 0x80000)"
        ),
        type=str,
        default="0",
    )
    parser.add_argument(
        "-v", "--verbose",
        help="enable verbose/debug output",
        action="store_true",
    )
    return parser


# ---------------------------------------------------------------------------
# List operation
# ---------------------------------------------------------------------------

def print_tree(fs: LittleFS, path: str) -> None:
    """Recursively print the filesystem tree starting at *path*.

    Directories are printed in cyan, files in yellow with a red marker
    and their human-readable size.

    Args:
        fs: A mounted ``LittleFS`` instance.
        path: Root path to start the tree listing from.
    """
    depth = path.count("/") - 1
    for item in fs.scandir(path):
        logger.debug("entry: %s type=%d", item.name, item.type)
        if item.type == LFS_TYPE_DIR:
            print(f"  {'    ' * depth}{Fore.CYAN}{item.name}")
            print_tree(fs, f"{path}/{item.name}")
        elif item.type == LFS_TYPE_FILE:
            size_str = f" ({sizeof_fmt(item.size)})"
            print(f"  {'    ' * depth}{Fore.RED}*---{Fore.YELLOW}{item.name}{size_str}")


def do_list(image: str, block_size: int, block_count: int, offset: int) -> None:
    """List the contents of a littleFS image file.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Byte offset where the LFS image starts in the file.

    Raises:
        FileNotFoundError: If *image* does not exist.
        LittleFSToolsError: On any LFS operation failure.
    """
    validate_block_size(block_size)
    validate_block_count(block_count)

    if not os.path.isfile(image):
        raise FileNotFoundError(f"Image file not found: {image}")

    fs = LittleFS(block_size=block_size, block_count=block_count, mount=False)
    with open(image, "rb") as fh:
        fh.seek(offset)
        fs.context.buffer = bytearray(fh.read())
    fs.mount()
    print(f"{Fore.GREEN}{image}")
    print_tree(fs, "/")


# ---------------------------------------------------------------------------
# Extract operation
# ---------------------------------------------------------------------------

def _walk_and_extract(fs: LittleFS, path: str, destination: str) -> None:
    """Recursively extract all files/directories from *path* to *destination*.

    Args:
        fs: A mounted ``LittleFS`` instance.
        path: Current path inside the LFS image.
        destination: Host filesystem destination root.
    """
    for item in fs.scandir(path):
        logger.debug("entry: %s type=%d", item.name, item.type)
        if item.type == LFS_TYPE_FILE:
            with fs.open(f"{path}/{item.name}", "rb") as src:
                host_path = os.path.join(destination, path.lstrip("/"), item.name)
                with open(host_path, "wb") as dst:
                    dst.write(src.read())
        elif item.type == LFS_TYPE_DIR:
            dir_path = os.path.join(destination, path.lstrip("/"), item.name)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            _walk_and_extract(fs, f"{path}/{item.name}", destination)


def do_extract(
    image: str,
    block_size: int,
    block_count: int,
    offset: int,
    destination: str,
    force: bool = False,
) -> None:
    """Extract the contents of a littleFS image to a host directory.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Byte offset where the LFS image starts in the file.
        destination: Directory to extract files into.
        force: If ``False`` and *destination* is non-empty, raise an error.

    Raises:
        FileNotFoundError: If *image* does not exist.
        DestinationNotEmptyError: If *destination* is non-empty and *force* is False.
    """
    validate_block_size(block_size)
    validate_block_count(block_count)

    if not os.path.isfile(image):
        raise FileNotFoundError(f"Image file not found: {image}")

    if not force and os.path.exists(destination) and os.listdir(destination):
        raise DestinationNotEmptyError(
            f"{destination} is not empty (use --force to overwrite)"
        )

    fs = LittleFS(block_size=block_size, block_count=block_count, mount=False)
    with open(image, "rb") as fh:
        fh.seek(offset)
        fs.context.buffer = bytearray(fh.read())
    fs.mount()
    Path(destination).mkdir(parents=True, exist_ok=True)
    _walk_and_extract(fs, "/", destination)
    print(f"Extracted files to {destination}")


# ---------------------------------------------------------------------------
# Create operation
# ---------------------------------------------------------------------------

def do_create(
    source: str,
    image: str,
    block_size: int,
    block_count: int,
    offset: int,
) -> None:
    """Create a littleFS binary image from a source directory.

    Args:
        source: Path to the source directory.
        image: Output image file path.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Number of zero-padding bytes to prepend to the image.

    Raises:
        FileNotFoundError: If *source* does not exist.
        ImageTooSmallError: If contents exceed the image capacity.
    """
    validate_block_size(block_size)
    validate_block_count(block_count)

    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source directory not found: {source}")

    fs = LittleFS(block_size=block_size, block_count=block_count)
    content_size = 0

    for path, subdirs, files in os.walk(source):
        for subdir in subdirs:
            lfs_dir = os.path.join(
                "/", path.removeprefix(source), subdir,
            ).replace("\\", "/")
            if lfs_dir != "/":
                logger.info("LFS Directory : %s", lfs_dir)
                fs.mkdir(lfs_dir)

        for name in files:
            file_path = os.path.join(path, name)
            lfs_path = os.path.join(
                "/", file_path.removeprefix(source),
            ).replace("\\", "/")

            file_size = os.path.getsize(file_path)
            content_size += file_size

            if content_size > block_size * (block_count - 2):
                raise ImageTooSmallError(
                    f"Contents ({sizeof_fmt(content_size)}) exceed image capacity "
                    f"[{block_size} x {block_count}] = "
                    f"{sizeof_fmt(block_size * block_count)}. "
                    "Increase block size or block count."
                )

            with open(file_path, "rb") as src:
                with fs.open(lfs_path, "wb") as dst:
                    logger.info("LFS File   : %s (%d bytes)", lfs_path, file_size)
                    while True:
                        chunk = src.read(READ_CHUNK_SIZE)
                        if not chunk:
                            break
                        dst.write(chunk)

    print(f"\nTotal contents size = {sizeof_fmt(content_size)}")

    # Prepend zero-padding for offset if specified
    buffer = fs.context.buffer
    if offset > 0:
        print(f"Padding image with {sizeof_fmt(offset)} at the beginning")
        buffer = bytearray(offset) + buffer

    with open(image, "wb") as fh:
        fh.write(buffer)

    if offset > 0:
        total = sizeof_fmt((block_size * block_count) + offset)
        print(
            f"Created `{image}` of size "
            f"[({sizeof_fmt(block_size)} x {block_count}) + {sizeof_fmt(offset)}] = {total}"
        )
    else:
        print(
            f"Created `{image}` of size "
            f"[{sizeof_fmt(block_size)} x {block_count}] = {sizeof_fmt(block_size * block_count)}"
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

def _legacy_parser(description: str, prog: str) -> argparse.ArgumentParser:
    """Build a standalone parser for a legacy entry point.

    Args:
        description: Parser description text.
        prog: Program name for help output.

    Returns:
        Configured ``ArgumentParser``.
    """
    parent = _common_parser()
    return argparse.ArgumentParser(
        description=description,
        prog=prog,
        parents=[parent],
    )


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
