"""Core filesystem operations for littlefs_tools."""

from __future__ import annotations

import csv
import fnmatch
import io
import json
import os
from collections.abc import Callable
from pathlib import Path

from colorama import Fore
from littlefs import LittleFS

from littlefs_tools._exceptions import (
    AutoDetectError,
    DestinationNotEmptyError,
    ImageTooSmallError,
    PathNotFoundError,
    ValidationError,
)
from littlefs_tools._helpers import (
    LFS_TYPE_DIR,
    LFS_TYPE_FILE,
    READ_CHUNK_SIZE,
    auto_detect,
    collect_entries,
    count_entries,
    logger,
    mount_image,
    parse_size,
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

def _walk_and_extract(
    fs: LittleFS,
    path: str,
    destination: str,
    filter_fn: Callable[[str], bool] | None = None,
) -> None:
    """Recursively extract files/directories, optionally filtered.

    Args:
        fs: A mounted ``LittleFS`` instance.
        path: Current path inside the LFS image.
        destination: Host filesystem destination root.
        filter_fn: Optional callable that receives a full LFS path and returns
            ``True`` if the file should be extracted.  Directories are always
            traversed so that nested matches are not missed.
    """
    for item in fs.scandir(path):
        logger.debug("entry: %s type=%d", item.name, item.type)
        full_path = f"{path}/{item.name}".replace("//", "/")
        if item.type == LFS_TYPE_FILE:
            if filter_fn and not filter_fn(full_path):
                continue
            with fs.open(full_path, "rb") as src:
                host_path = os.path.join(destination, path.lstrip("/"), item.name)
                Path(os.path.dirname(host_path)).mkdir(parents=True, exist_ok=True)
                with open(host_path, "wb") as dst:
                    dst.write(src.read())
        elif item.type == LFS_TYPE_DIR:
            dir_path = os.path.join(destination, path.lstrip("/"), item.name)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            _walk_and_extract(fs, full_path, destination, filter_fn)


def do_extract(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
    destination: str = ".",
    force: bool = False,
    paths: list[str] | None = None,
    pattern: str | None = None,
) -> None:
    """Extract the contents of a littleFS image to a host directory.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes (``None`` to auto-detect).
        block_count: Number of blocks in the image (``None`` to auto-detect).
        offset: Byte offset where the LFS image starts in the file.
        destination: Directory to extract files into.
        force: If ``False`` and *destination* is non-empty, raise an error.
        paths: If set, extract only these specific file paths.
        pattern: If set, extract only files whose name matches this glob pattern.

    Raises:
        FileNotFoundError: If *image* does not exist.
        DestinationNotEmptyError: If *destination* is non-empty and *force* is False.
    """
    if not force and os.path.exists(destination) and os.listdir(destination):
        raise DestinationNotEmptyError(
            f"{destination} is not empty (use --force to overwrite)"
        )

    # Build filter function
    filter_fn: Callable[[str], bool] | None = None
    if paths is not None:
        path_set = set(paths)
        filter_fn = lambda p: p in path_set  # noqa: E731
    elif pattern is not None:
        filter_fn = lambda p: fnmatch.fnmatch(p.split("/")[-1], pattern)  # noqa: E731

    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    Path(destination).mkdir(parents=True, exist_ok=True)
    _walk_and_extract(fs, "/", destination, filter_fn)
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
    name_max: int = 0,
    file_max: int = 0,
    attr_max: int = 0,
    read_size: int = 0,
    prog_size: int = 0,
    cache_size: int = 0,
    lookahead_size: int = 0,
    block_cycles: int = -1,
    disk_version: int = 0,
) -> None:
    """Create a littleFS binary image from a source directory.

    Args:
        source: Path to the source directory.
        image: Output image file path.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Number of zero-padding bytes to prepend to the image.
        compact: If True, trim the image to used blocks only.
        name_max: Max filename length (0 = library default 255).
        file_max: Max file size (0 = unlimited).
        attr_max: Max attribute size (0 = library default).
        read_size: Minimum read size (0 = library default).
        prog_size: Minimum prog size (0 = library default).
        cache_size: Cache size (0 = library default).
        lookahead_size: Lookahead buffer size (0 = library default).
        block_cycles: Block cycles before eviction (-1 = disable wear leveling).
        disk_version: On-disk format version (0 = latest).

    Raises:
        FileNotFoundError: If *source* does not exist.
        ImageTooSmallError: If contents exceed the image capacity.
    """
    validate_block_size(block_size)
    validate_block_count(block_count)

    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source directory not found: {source}")

    # Build kwargs, only passing non-default LFS config options
    lfs_kwargs: dict = {
        "block_size": block_size,
        "block_count": block_count,
    }
    if name_max > 0:
        lfs_kwargs["name_max"] = name_max
    if file_max > 0:
        lfs_kwargs["file_max"] = file_max
    if attr_max > 0:
        lfs_kwargs["attr_max"] = attr_max
    if read_size > 0:
        lfs_kwargs["read_size"] = read_size
    if prog_size > 0:
        lfs_kwargs["prog_size"] = prog_size
    if cache_size > 0:
        lfs_kwargs["cache_size"] = cache_size
    if lookahead_size > 0:
        lfs_kwargs["lookahead_size"] = lookahead_size
    if block_cycles >= 0:
        lfs_kwargs["block_cycles"] = block_cycles
    if disk_version > 0:
        lfs_kwargs["disk_version"] = disk_version
    fs = LittleFS(**lfs_kwargs)
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

    if compact:
        used = fs.used_block_count
        # Rebuild with exact block_count so the superblock is consistent
        fs_compact = LittleFS(block_size=block_size, block_count=used)
        for path_w, subdirs_w, files_w in os.walk(source):
            for subdir in subdirs_w:
                lfs_dir = os.path.join(
                    "/", path_w.removeprefix(source), subdir,
                ).replace("\\", "/")
                if lfs_dir != "/":
                    fs_compact.mkdir(lfs_dir)
            for name_w in files_w:
                file_path_w = os.path.join(path_w, name_w)
                lfs_path_w = os.path.join(
                    "/", file_path_w.removeprefix(source),
                ).replace("\\", "/")
                with open(file_path_w, "rb") as src_w:
                    with fs_compact.open(lfs_path_w, "wb") as dst_w:
                        while True:
                            chunk = src_w.read(READ_CHUNK_SIZE)
                            if not chunk:
                                break
                            dst_w.write(chunk)
        buffer = fs_compact.context.buffer
        print(f"Compact mode: trimmed to {used} blocks ({sizeof_fmt(len(buffer))})")
    else:
        buffer = fs.context.buffer

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


# ---------------------------------------------------------------------------
# Verify operation
# ---------------------------------------------------------------------------

def do_verify(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> dict:
    """Validate the integrity of a littleFS image.

    Checks: superblock magic, mountability, all files traversable,
    file stat sizes match actual read sizes.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Returns:
        Dict with keys: valid (bool), checks_passed (list[str]), errors (list[str]).
    """
    result: dict = {"valid": True, "checks_passed": [], "errors": []}

    # Check 1: superblock magic
    try:
        auto_detect(image, offset)
        result["checks_passed"].append("superblock_magic")
    except (AutoDetectError, FileNotFoundError) as exc:
        result["valid"] = False
        result["errors"].append(f"superblock: {exc}")
        return result

    # Check 2: mount
    try:
        bs, bc = resolve_params(image, block_size, block_count, offset)
        fs = mount_image(image, bs, bc, offset)
        result["checks_passed"].append("mount")
    except Exception as exc:
        result["valid"] = False
        result["errors"].append(f"mount: {exc}")
        return result

    # Check 3: walk all files, verify sizes
    try:
        for root, _dirs, files in fs.walk("/"):
            for fname in files:
                fpath = f"{root}/{fname}".replace("//", "/")
                st = fs.stat(fpath)
                with fs.open(fpath, "rb") as fh:
                    data = fh.read()
                if len(data) != st.size:
                    result["errors"].append(
                        f"size mismatch: {fpath} stat={st.size} actual={len(data)}"
                    )
                    result["valid"] = False
        result["checks_passed"].append("file_integrity")
    except Exception as exc:
        result["valid"] = False
        result["errors"].append(f"walk: {exc}")

    return result


# ---------------------------------------------------------------------------
# Diff operation
# ---------------------------------------------------------------------------

def do_diff(
    image1: str,
    image2: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> dict:
    """Compare two littleFS images.

    Args:
        image1: Path to the first image.
        image2: Path to the second image.
        block_size: LFS block size (auto-detected per image if None).
        block_count: Number of blocks (auto-detected per image if None).
        offset: Byte offset for both images.

    Returns:
        Dict with keys: only_in_1, only_in_2, different, identical (all lists of paths).
    """
    bs1, bc1 = resolve_params(image1, block_size, block_count, offset)
    bs2, bc2 = resolve_params(image2, block_size, block_count, offset)

    fs1 = mount_image(image1, bs1, bc1, offset)
    fs2 = mount_image(image2, bs2, bc2, offset)

    entries1 = {e["path"]: e for e in collect_entries(fs1)}
    entries2 = {e["path"]: e for e in collect_entries(fs2)}

    paths1 = set(entries1.keys())
    paths2 = set(entries2.keys())

    result: dict = {
        "only_in_1": sorted(paths1 - paths2),
        "only_in_2": sorted(paths2 - paths1),
        "different": [],
        "identical": [],
    }

    for path in sorted(paths1 & paths2):
        e1, e2 = entries1[path], entries2[path]
        if e1["type"] == "file" and e2["type"] == "file":
            with fs1.open(path, "rb") as f1, fs2.open(path, "rb") as f2:
                if f1.read() == f2.read():
                    result["identical"].append(path)
                else:
                    result["different"].append(path)
        else:
            result["identical"].append(path)

    return result


# ---------------------------------------------------------------------------
# Extended attribute operations
# ---------------------------------------------------------------------------

def do_getattr(
    image: str,
    path: str,
    attr_type: int,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> bytes:
    """Get an extended attribute from a file/directory in a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        path: Path inside the image.
        attr_type: Attribute type ID (0-255).
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Returns:
        The attribute data as bytes.

    Raises:
        PathNotFoundError: If path or attribute does not exist.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    try:
        return fs.getattr(path, attr_type)
    except Exception as exc:
        raise PathNotFoundError(f"Cannot get attr type {attr_type} on {path}: {exc}") from exc


def do_setattr(
    image: str,
    path: str,
    attr_type: int,
    data: bytes,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Set an extended attribute on a file/directory in a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        path: Path inside the image.
        attr_type: Attribute type ID (0-255).
        data: Attribute data bytes.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    try:
        fs.setattr(path, attr_type, data)
    except Exception as exc:
        raise PathNotFoundError(f"Cannot set attr type {attr_type} on {path}: {exc}") from exc
    save_image(fs, image, offset)


def do_removeattr(
    image: str,
    path: str,
    attr_type: int,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Remove an extended attribute from a file/directory in a littleFS image.

    Args:
        image: Path to the littleFS binary image.
        path: Path inside the image.
        attr_type: Attribute type ID (0-255).
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    try:
        fs.removeattr(path, attr_type)
    except Exception as exc:
        raise PathNotFoundError(f"Cannot remove attr type {attr_type} on {path}: {exc}") from exc
    save_image(fs, image, offset)


# ---------------------------------------------------------------------------
# Maintenance operations
# ---------------------------------------------------------------------------

def do_gc(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> int:
    """Run garbage collection on a littleFS image.

    Returns:
        Number of used blocks after GC.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    fs.fs_gc()
    used = fs.used_block_count
    save_image(fs, image, offset)
    return used


def do_grow(
    image: str,
    new_block_count: int | None = None,
    new_size: str | None = None,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Grow a littleFS image to a larger size.

    Args:
        image: Path to the littleFS binary image.
        new_block_count: Target block count.
        new_size: Target size as human-readable string (alternative to new_block_count).
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.

    Raises:
        ValidationError: If new size is not larger than current.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)

    if new_size is not None:
        target_bytes = parse_size(new_size)
        new_bc = target_bytes // bs
    elif new_block_count is not None:
        new_bc = new_block_count
    else:
        raise ValidationError("Must specify new_block_count or new_size")

    if new_bc <= bc:
        raise ValidationError(f"New block count ({new_bc}) must exceed current ({bc})")

    fs = mount_image(image, bs, bc, offset)

    # Extend the buffer with 0xFF (erased flash state)
    old_buf = bytes(fs.context.buffer)
    new_buf = bytearray(new_bc * bs)
    new_buf[:len(old_buf)] = old_buf
    for i in range(len(old_buf), len(new_buf)):
        new_buf[i] = 0xFF
    fs.context.buffer = new_buf

    fs.fs_grow(new_bc)
    save_image(fs, image, offset)
    print(f"Grew {image} from {bc} to {new_bc} blocks ({sizeof_fmt(new_bc * bs)})")


def do_repair(
    image: str,
    block_size: int | None = None,
    block_count: int | None = None,
    offset: int = 0,
) -> None:
    """Run mkconsistent on a littleFS image to repair inconsistencies.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size (auto-detected if None).
        block_count: Number of blocks (auto-detected if None).
        offset: Byte offset where the LFS image starts.
    """
    bs, bc = resolve_params(image, block_size, block_count, offset)
    fs = mount_image(image, bs, bc, offset)
    fs.fs_mkconsistent()
    save_image(fs, image, offset)
    print(f"Repaired {image}")
