"""Core filesystem operations for littlefs_tools."""

from __future__ import annotations

import os
from pathlib import Path

from colorama import Fore
from littlefs import LittleFS

from littlefs_tools._exceptions import (
    DestinationNotEmptyError,
    ImageTooSmallError,
)
from littlefs_tools._helpers import (
    LFS_TYPE_DIR,
    LFS_TYPE_FILE,
    READ_CHUNK_SIZE,
    logger,
    sizeof_fmt,
    validate_block_count,
    validate_block_size,
)

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
