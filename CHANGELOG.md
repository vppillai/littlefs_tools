# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - Unreleased

This is a major feature release that adds 15 new subcommands, auto-detection, and a modular
codebase. The v1.2.0 modernization and v1.3.0 feature expansion were AI-assisted updates that
restructured the codebase from a single 327-line file into a well-tested, modular package.

### Added
- **Auto-detection**: `--block_size` and `--block_count` are now optional for all read commands. Values are auto-detected from the image superblock.
- **`--fs-size` flag**: Specify total image size (e.g. `256kb`, `1mb`, `0x40000`) as alternative to `--block_count`.
- **`-q/--quiet` flag**: Suppress informational output.
- **`--config` flag**: Load default options from a JSON or YAML config file.
- **`info` subcommand**: Display image metadata (version, block size/count, usage, file counts, limits).
- **`cat` subcommand**: Print a file from the image to stdout.
- **`du` subcommand**: Per-directory disk usage statistics.
- **`add` subcommand**: Add files or directories to an existing image.
- **`remove` subcommand**: Remove files or directories from an image (with `--recursive`).
- **`rename` subcommand**: Rename or move files within an image.
- **`verify` subcommand**: Validate image integrity (superblock, mount, file consistency).
- **`diff` subcommand**: Compare two images and report differences.
- **`attr` subcommand**: Get, set, or remove extended attributes on files.
- **`gc` subcommand**: Run garbage collection.
- **`grow` subcommand**: Grow an image to a larger size.
- **`repair` subcommand**: Repair an inconsistent image via `mkconsistent`.
- **`--compact` flag** on `create`: Trim image to used blocks only.
- **`--format` flag** on `list`: Output as `tree` (default), `json`, or `csv`.
- **`--format` flag** on `info`, `du`, `diff`: Output as `table` or `json`.
- **Selective extraction**: `--file` and `--pattern` flags on `extract`.
- **LFS config params** on `create`: `--name-max`, `--file-max`, `--attr-max`, `--read-size`, `--prog-size`, `--cache-size`, `--lookahead-size`, `--block-cycles`, `--disk-version`.
- **Optional YAML support**: `pip install littlefs_tools[config]` for YAML config files.
- New exceptions: `AutoDetectError`, `ImageCorruptError`, `PathNotFoundError`.
- 68 new pytest tests (105 total).
- Shared helpers: `mount_image()`, `save_image()`, `collect_entries()`, `count_entries()`, `auto_detect()`, `resolve_params()`, `parse_size()`, `load_config()`.

### Changed
- Codebase split from single file into focused modules (`_exceptions.py`, `_helpers.py`, `operations.py`, `cli.py`) with a backward-compatible re-export shim.
- `do_list()` and `do_extract()` accept `None` for block_size/block_count (triggers auto-detection).
- `do_create()` accepts additional LFS configuration parameters.

## [1.2.0] - 2026-04-10

This release modernized the project from a legacy single-file package to a well-structured,
PEP-compliant Python package. This was the first AI-assisted update to the project.

### Added
- Unified `littlefs` CLI with subcommands: `littlefs create`, `littlefs list`, `littlefs extract`.
- `--version` flag for the unified CLI.
- Python pytest test suite with full coverage (37 tests).
- Input validation for block size (must be power of 2) and block count (must be positive).
- Custom exception hierarchy (`LittleFSToolsError`, `ImageTooSmallError`, `ValidationError`, `DestinationNotEmptyError`).
- Type hints on all functions.
- Docstrings on all public functions.
- `pyproject.toml` for modern PEP 517/518 packaging.
- `CHANGELOG.md` and `CONTRIBUTING.md`.
- macOS and Windows in CI test matrix.
- `ruff` linting in CI.
- `__version__` accessible via `littlefs_tools.__version__`.
- `python -m littlefs_tools` support.

### Changed
- File I/O now uses chunked reads (4096 bytes) instead of byte-by-byte, significantly improving performance for large files.
- All internal names follow PEP 8 snake_case convention.
- `-i/--image` is now required for `create` (previously defaulted to `test.bin`).
- Error handling uses proper exceptions instead of `exit()` -- the library functions can now be called programmatically.
- Minimum Python version is now 3.9 (dropped 3.8 which is EOL).
- Dependencies pinned with minimum versions: `littlefs-python>=0.12.0`, `colorama>=0.4.0`.
- CI uses `python -m build` instead of deprecated `python setup.py bdist_wheel`.
- `colorama.init()` is only called in CLI entry points, not at module import time.

### Removed
- `setup.py` (replaced by `pyproject.toml`).
- `requirements.txt` (replaced by `pyproject.toml` and `requirements-dev.txt`).
- Python 3.8 support.

### Fixed
- OS classifiers now include macOS and Windows (previously Linux-only).

## [1.1.7] - 2026-01-13

### Added
- Python 3.14 support.

## [1.1.6] - 2025-10-15

### Added
- Python 3.13 support.
- Windows path separator support (PR #2 by @thomasweichselbaumer).

## [1.1.5] - 2024-10-15

### Added
- Python 3.12 support.

## [1.1.4] - 2023-12-01

### Added
- Offset support for `littlefs_create` (zero-padding at image start).
- Offset support for `littlefs_list` and `littlefs_extract` (partitioned disk images).

## [1.1.3] - 2023-06-01

### Added
- Large file test.

## [1.0.2] - 2022-01-01

### Added
- Initial public release with `littlefs_create`, `littlefs_list`, `littlefs_extract`.
