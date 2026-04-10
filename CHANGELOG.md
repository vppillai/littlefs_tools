# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - Unreleased

### Added
- Unified `littlefs` CLI with subcommands: `littlefs create`, `littlefs list`, `littlefs extract`.
- `--version` flag for the unified CLI.
- Python pytest test suite with full coverage.
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
- Error handling uses proper exceptions instead of `exit()` — the library functions can now be called programmatically.
- Minimum Python version is now 3.9 (dropped 3.8 which is EOL).
- Dependencies are now pinned with minimum versions: `littlefs-python>=0.12.0`, `colorama>=0.4.0`.
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
