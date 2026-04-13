# Contributing to littlefs_tools

Thank you for your interest in contributing to littlefs_tools!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/vppillai/littlefs_tools.git
   cd littlefs_tools
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows
   pip install -e .
   pip install -r requirements-dev.txt
   ```

   For YAML config file support:
   ```bash
   pip install -e ".[config]"
   ```

## Project Structure

```
littlefs_tools/
    __init__.py          # Package metadata and __version__
    __main__.py          # python -m littlefs_tools support
    _exceptions.py       # Exception hierarchy
    _helpers.py          # Shared constants, validators, auto-detect, mount/save helpers
    operations.py        # Core operations (do_create, do_list, do_extract, do_info, etc.)
    cli.py               # CLI entry points (main, legacy commands)
    littlefs_tools.py    # Backward-compatible re-export shim
```

The `littlefs_tools.py` shim re-exports all public names so existing imports like
`from littlefs_tools.littlefs_tools import do_create` continue to work.

## Running Tests

```bash
# Run the pytest suite
pytest tests/ -v

# Run the legacy bash integration tests (Linux/macOS only)
cd test && ./test.sh && ./test_large.sh
```

## Linting

```bash
ruff check littlefs_tools/ tests/
```

## Building

```bash
pip install build
python -m build
```

This produces both a source distribution and a wheel in the `dist/` directory.

## Pull Request Guidelines

- All new functionality should include tests.
- Run `ruff check` and `pytest` before submitting.
- Keep PRs focused on a single change.
- Update `CHANGELOG.md` with your changes under the `[Unreleased]` section.
- New subcommands should follow the existing patterns:
  - Operation function in `operations.py` (e.g. `do_something()`)
  - Subparser and dispatch in `cli.py`
  - Tests in `tests/test_something.py`

## Code Style

- Follow PEP 8 with snake_case naming.
- Add type hints to all function signatures.
- Add docstrings to all public functions.
- Maximum line length: 120 characters.
- Use `resolve_params()` and `mount_image()` for image access (not inline mount code).
- Raise exceptions from `_exceptions.py` (not `exit()` or `sys.exit()`).
