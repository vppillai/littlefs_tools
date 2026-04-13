"""Shared constants, validators, and argument parsing for littlefs_tools."""

from __future__ import annotations

import argparse
import logging

from littlefs_tools._exceptions import ValidationError

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
