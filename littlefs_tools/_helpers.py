"""Shared constants, validators, and argument parsing for littlefs_tools."""

from __future__ import annotations

import argparse
import logging
import os
import re
import struct

from littlefs import LittleFS

from littlefs_tools._exceptions import AutoDetectError, ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LFS_TYPE_FILE: int = 1
LFS_TYPE_DIR: int = 2

READ_CHUNK_SIZE: int = 4096

logger = logging.getLogger("littlefs_tools")


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
# Size parsing
# ---------------------------------------------------------------------------

_SIZE_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(kb|k|mb|m|gb|g|tb|t)?\s*$",
    re.IGNORECASE,
)

_SIZE_MULTIPLIERS: dict[str, int] = {
    "k": 1024,
    "kb": 1024,
    "m": 1024 ** 2,
    "mb": 1024 ** 2,
    "g": 1024 ** 3,
    "gb": 1024 ** 3,
    "t": 1024 ** 4,
    "tb": 1024 ** 4,
}

_SUPERBLOCK_MAGIC = b"littlefs"


def parse_size(value: str) -> int:
    """Parse a human-readable size string into an integer byte count.

    Supports plain integers, hex (``0x...``), and suffixes like ``kb``, ``k``,
    ``mb``, ``m`` (binary / 1024-based, case-insensitive).

    Args:
        value: Size string to parse.

    Returns:
        Size in bytes.

    Raises:
        ValidationError: If *value* cannot be parsed.
    """
    # Try hex first
    stripped = value.strip()
    if stripped.lower().startswith("0x"):
        try:
            return int(stripped, 16)
        except ValueError:
            pass

    m = _SIZE_RE.match(stripped)
    if m:
        number = float(m.group(1))
        suffix = m.group(2)
        if suffix:
            result = int(number * _SIZE_MULTIPLIERS[suffix.lower()])
        else:
            result = int(number)
        return result

    raise ValidationError(f"Cannot parse size: {value!r}")


# ---------------------------------------------------------------------------
# Auto-detection and image helpers
# ---------------------------------------------------------------------------

def auto_detect(image_path: str, offset: int = 0) -> tuple[int, int]:
    """Detect ``block_size`` and ``block_count`` from a littleFS superblock.

    Args:
        image_path: Path to the littleFS binary image.
        offset: Byte offset where the LFS image starts.

    Returns:
        Tuple of ``(block_size, block_count)``.

    Raises:
        FileNotFoundError: If *image_path* does not exist.
        AutoDetectError: If the superblock magic is not found.
        ValidationError: If the detected block_size is invalid.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    with open(image_path, "rb") as fh:
        # Check magic at offset + 0x08
        fh.seek(offset + 0x08)
        magic = fh.read(8)
        if magic != _SUPERBLOCK_MAGIC:
            raise AutoDetectError(
                f"Not a littleFS image (expected magic {_SUPERBLOCK_MAGIC!r} "
                f"at offset {offset + 0x08:#x}, got {magic!r})"
            )

        # Read block_size at offset + 0x18
        fh.seek(offset + 0x18)
        raw = fh.read(4)
        if len(raw) < 4:
            raise AutoDetectError("Image too small to read block_size field")
        (block_size,) = struct.unpack("<I", raw)

    validate_block_size(block_size)

    # Mount with block_count=0 to let littlefs auto-detect block_count
    fs = LittleFS(block_size=block_size, block_count=0, mount=False)
    with open(image_path, "rb") as fh:
        fh.seek(offset)
        fs.context.buffer = bytearray(fh.read())
    fs.mount()
    stat = fs.fs_stat()
    block_count = stat.block_count

    return (block_size, block_count)


def resolve_params(
    image: str,
    block_size: int | None,
    block_count: int | None,
    offset: int,
) -> tuple[int, int]:
    """Resolve block_size and block_count, auto-detecting if necessary.

    If both *block_size* and *block_count* are provided, they are validated
    and returned.  If either is ``None``, :func:`auto_detect` fills in the
    missing value(s).

    Args:
        image: Path to the littleFS binary image.
        block_size: Block size or ``None`` to auto-detect.
        block_count: Block count or ``None`` to auto-detect.
        offset: Byte offset where the LFS image starts.

    Returns:
        Tuple of ``(block_size, block_count)``.
    """
    if block_size is not None and block_count is not None:
        validate_block_size(block_size)
        validate_block_count(block_count)
        return (block_size, block_count)

    detected_bs, detected_bc = auto_detect(image, offset)
    bs = block_size if block_size is not None else detected_bs
    bc = block_count if block_count is not None else detected_bc
    return (bs, bc)


def mount_image(
    image: str,
    block_size: int,
    block_count: int,
    offset: int,
) -> LittleFS:
    """Mount a littleFS image and return the filesystem object.

    Args:
        image: Path to the littleFS binary image.
        block_size: LFS block size in bytes.
        block_count: Number of blocks in the image.
        offset: Byte offset where the LFS image starts.

    Returns:
        A mounted :class:`LittleFS` instance.

    Raises:
        FileNotFoundError: If *image* does not exist.
    """
    if not os.path.isfile(image):
        raise FileNotFoundError(f"Image file not found: {image}")

    fs = LittleFS(block_size=block_size, block_count=block_count, mount=False)
    with open(image, "rb") as fh:
        fh.seek(offset)
        fs.context.buffer = bytearray(fh.read())
    fs.mount()
    return fs


def save_image(fs: LittleFS, image: str, offset: int) -> None:
    """Write a LittleFS buffer back to an image file.

    If *offset* > 0, the original file's first *offset* bytes are preserved.

    Args:
        fs: A mounted :class:`LittleFS` instance.
        image: Output image file path.
        offset: Byte offset where the LFS data starts.
    """
    buffer = fs.context.buffer
    if offset > 0 and os.path.isfile(image):
        with open(image, "rb") as fh:
            prefix = fh.read(offset)
        with open(image, "wb") as fh:
            fh.write(prefix)
            fh.write(buffer)
    else:
        if offset > 0:
            buffer = bytearray(offset) + buffer
        with open(image, "wb") as fh:
            fh.write(buffer)


def collect_entries(fs: LittleFS, path: str = "/") -> list[dict]:
    """Walk the filesystem tree and return a list of entry dicts.

    Each entry has keys ``"path"`` (str), ``"type"`` (``"file"`` or
    ``"dir"``), and ``"size"`` (int, 0 for directories).

    Args:
        fs: A mounted :class:`LittleFS` instance.
        path: Root path to start from.

    Returns:
        List of entry dictionaries.
    """
    entries: list[dict] = []
    for item in fs.scandir(path):
        full = f"{path}/{item.name}" if path != "/" else f"/{item.name}"
        if item.type == LFS_TYPE_DIR:
            entries.append({"path": full, "type": "dir", "size": 0})
            entries.extend(collect_entries(fs, full))
        elif item.type == LFS_TYPE_FILE:
            entries.append({"path": full, "type": "file", "size": item.size})
    return entries


def count_entries(fs: LittleFS) -> tuple[int, int, int]:
    """Walk the filesystem tree and count entries.

    Args:
        fs: A mounted :class:`LittleFS` instance.

    Returns:
        Tuple of ``(file_count, dir_count, total_bytes)``.
    """
    entries = collect_entries(fs)
    file_count = sum(1 for e in entries if e["type"] == "file")
    dir_count = sum(1 for e in entries if e["type"] == "dir")
    total_bytes = sum(e["size"] for e in entries)
    return (file_count, dir_count, total_bytes)


# ---------------------------------------------------------------------------
# Shared argument parser
# ---------------------------------------------------------------------------

def _common_parser() -> argparse.ArgumentParser:
    """Return a parent parser containing arguments shared by all subcommands.

    Shared arguments: ``-b/--block_size``, ``-c/--block_count``,
    ``--fs-size``, ``-o/--offset``, ``-v/--verbose``, ``-q/--quiet``.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-b", "--block_size",
        dest="block_size",
        help=(
            "block size of the LFS image "
            "(auto-detected if not specified, defaults to 4096 for create)"
        ),
        type=int,
        default=None,
    )
    parser.add_argument(
        "-c", "--block_count",
        dest="block_count",
        help=(
            "block count of the LFS image "
            "(auto-detected if not specified, defaults to 64 for create)"
        ),
        type=int,
        default=None,
    )
    parser.add_argument(
        "--fs-size",
        dest="fs_size",
        help=(
            "total image size (e.g. 256kb, 1mb, 0x40000). "
            "Alternative to --block_count"
        ),
        type=str,
        default=None,
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
    parser.add_argument(
        "-q", "--quiet",
        help="suppress informational output",
        action="store_true",
    )
    return parser


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
