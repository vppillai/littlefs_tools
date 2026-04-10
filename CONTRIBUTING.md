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
python -m build
```

This produces both a source distribution and a wheel in the `dist/` directory.

## Pull Request Guidelines

- All new functionality should include tests.
- Run `ruff check` and `pytest` before submitting.
- Keep PRs focused on a single change.
- Update `CHANGELOG.md` with your changes under the `[Unreleased]` section.

## Code Style

- Follow PEP 8 with snake_case naming.
- Add type hints to all function signatures.
- Add docstrings to all public functions.
- Maximum line length: 120 characters.
