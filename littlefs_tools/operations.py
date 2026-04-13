"""Core filesystem operations for littlefs_tools."""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path

from colorama import Fore
from littlefs import LittleFS

from littlefs_tools._exceptions import (
    DestinationNotEmptyError,
    ImageTooSmallError,
    PathNotFoundError,
)
from littlefs_tools._helpers import (
    LFS_TYPE_DIR,
    LFS_TYPE_FILE,
    READ_CHUNK_SIZE,
    collect_entries,
    count_entries,
    logger,
    mount_image,
    resolve_params,
    save_image,
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


def do_list(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
    output_format: str = "tree",
) -> None:
    """List the contents of a littleFS image file.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes (``None`` to auto-detect).
        block_count: Number of blocks in the image (``None`` to auto-detect).
        offset: Byte offset where the LFS image starts in the file.
        output_format: Output format - ``"tree"`` (colored), ``"json"``, or ``"csv"``.

    Raises:
        FileNotFoundError: If *image* does not exist.
        LittleFSToolsError: On any LFS operation failure.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)

    if output_format == "json":
        entries = collect_entries(fs)
        print(json.dumps(entries, indent=2))
    elif output_format == "csv":
        entries = collect_entries(fs)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["path", "type", "size"])
        writer.writeheader()
        writer.writerows(entries)
        print(output.getvalue(), end="")
    else:
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
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
    destination: str = ".",
    force: bool = False,
) -> None:
    """Extract the contents of a littleFS image to a host directory.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes (``None`` to auto-detect).
        block_count: Number of blocks in the image (``None`` to auto-detect).
        offset: Byte offset where the LFS image starts in the file.
        destination: Directory to extract files into.
        force: If ``False`` and *destination* is non-empty, raise an error.

    Raises:
        FileNotFoundError: If *image* does not exist.
        DestinationNotEmptyError: If *destination* is non-empty and *force* is False.
    """
    if not force and os.path.exists(destination) and os.listdir(destination):
        raise DestinationNotEmptyError(
            f"{destination} is not empty (use --force to overwrite)"
        )

    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
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
    compact: bool = False,
) -> None:
    """Create a littleFS binary image from a source directory.

    Args:
        source: Path to the source directory.
        image: Output image file path.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Number of zero-padding bytes to prepend to the image.
        compact: If True, trim the image to used blocks only.

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

    buffer = fs.context.buffer
    if compact:
        used = fs.used_block_count
        buffer = buffer[:used * block_size]
        print(f"Compact mode: trimmed to {used} blocks ({sizeof_fmt(len(buffer))})")

    # Prepend zero-padding for offset if specified
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
# Info operation
# ---------------------------------------------------------------------------

def do_info(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> dict:
    """Return metadata about a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Returns:
        Dict with keys: image, disk_version, block_size, block_count,
        used_blocks, free_blocks, used_pct, total_size, used_size,
        free_size, file_count, dir_count, content_bytes, name_max,
        file_max, attr_max.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    stat = fs.fs_stat()
    used = fs.used_block_count
    file_count, dir_count, content_bytes = count_entries(fs)

    return {
        "image": image,
        "disk_version": f"{stat.disk_version >> 16}.{stat.disk_version & 0xFFFF}",
        "block_size": stat.block_size,
        "block_count": stat.block_count,
        "used_blocks": used,
        "free_blocks": stat.block_count - used,
        "used_pct": round(used / stat.block_count * 100, 1),
        "total_size": stat.block_size * stat.block_count,
        "used_size": stat.block_size * used,
        "free_size": stat.block_size * (stat.block_count - used),
        "file_count": file_count,
        "dir_count": dir_count,
        "content_bytes": content_bytes,
        "name_max": stat.name_max,
        "file_max": stat.file_max,
        "attr_max": stat.attr_max,
    }


# ---------------------------------------------------------------------------
# Cat operation
# ---------------------------------------------------------------------------

def do_cat(
    image: str,
    path: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> bytes:
    """Read and return the contents of a file inside a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        path: Path inside the image (e.g. "/dir/file.txt").
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Returns:
        The file contents as bytes.

    Raises:
        PathNotFoundError: If path does not exist in the image.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    try:
        with fs.open(path, "rb") as fh:
            return fh.read()
    except Exception as exc:
        raise PathNotFoundError(f"File not found in image: {path}") from exc


# ---------------------------------------------------------------------------
# Du (disk usage) operation
# ---------------------------------------------------------------------------

def do_du(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
    path: str = "/",
) -> list[dict]:
    """Compute disk usage per directory.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.
        path: Starting directory path.

    Returns:
        List of dicts with keys: path, files, dirs, bytes.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    results = []
    for root, dirs, files in fs.walk(path):
        dir_bytes = 0
        for fname in files:
            full = f"{root}/{fname}".replace("//", "/")
            st = fs.stat(full)
            dir_bytes += st.size
        results.append({
            "path": root,
            "files": len(files),
            "dirs": len(dirs),
            "bytes": dir_bytes,
        })
    return results


# ---------------------------------------------------------------------------
# Add operation
# ---------------------------------------------------------------------------

def do_add(
    image: str,
    sources: list[str],
    dest: str = "/",
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Add files or directories to an existing littleFS image.

    Args:
        image: Path to the littleFS binary image.
        sources: List of host file/directory paths to add.
        dest: Destination directory inside the image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Raises:
        FileNotFoundError: If image or any source does not exist.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)

    for src in sources:
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        if src_path.is_file():
            lfs_path = f"{dest}/{src_path.name}".replace("//", "/")
            with open(src, "rb") as host_fh:
                with fs.open(lfs_path, "wb") as lfs_fh:
                    while True:
                        chunk = host_fh.read(READ_CHUNK_SIZE)
                        if not chunk:
                            break
                        lfs_fh.write(chunk)
            logger.info("Added file: %s -> %s", src, lfs_path)
        elif src_path.is_dir():
            for root, subdirs, files in os.walk(src):
                for subdir in subdirs:
                    lfs_dir = os.path.join(
                        dest, root.removeprefix(src).lstrip(os.sep), subdir,
                    ).replace("\\", "/")
                    try:
                        fs.mkdir(lfs_dir)
                    except Exception:
                        pass  # directory may already exist
                    logger.info("Added directory: %s", lfs_dir)
                for name in files:
                    host_path = os.path.join(root, name)
                    lfs_path = os.path.join(
                        dest, root.removeprefix(src).lstrip(os.sep), name,
                    ).replace("\\", "/")
                    with open(host_path, "rb") as host_fh:
                        with fs.open(lfs_path, "wb") as lfs_fh:
                            while True:
                                chunk = host_fh.read(READ_CHUNK_SIZE)
                                if not chunk:
                                    break
                                lfs_fh.write(chunk)
                    logger.info("Added file: %s -> %s", host_path, lfs_path)

    save_image(fs, image, offset)
    print(f"Added {len(sources)} source(s) to {image}")


# ---------------------------------------------------------------------------
# Remove operation
# ---------------------------------------------------------------------------

def do_remove(
    image: str,
    paths: list[str],
    recursive: bool = False,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Remove files or directories from a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        paths: Paths inside the image to remove.
        recursive: If True, remove directories recursively.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Raises:
        PathNotFoundError: If a path does not exist in the image.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)

    for path in paths:
        try:
            fs.remove(path, recursive=recursive)
            logger.info("Removed: %s", path)
        except Exception as exc:
            raise PathNotFoundError(f"Cannot remove {path}: {exc}") from exc

    save_image(fs, image, offset)
    print(f"Removed {len(paths)} path(s) from {image}")


# ---------------------------------------------------------------------------
# Rename operation
# ---------------------------------------------------------------------------

def do_rename(
    image: str,
    src_path: str,
    dst_path: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Rename or move a file/directory within a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        src_path: Current path inside the image.
        dst_path: New path inside the image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Raises:
        PathNotFoundError: If src_path does not exist.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)

    try:
        fs.rename(src_path, dst_path)
    except Exception as exc:
        raise PathNotFoundError(
            f"Cannot rename {src_path} -> {dst_path}: {exc}"
        ) from exc

    save_image(fs, image, offset)
    print(f"Renamed {src_path} -> {dst_path} in {image}")
