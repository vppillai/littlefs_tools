"""Tests for CLI argument parsing and entry points."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    ValidationError,
    parse_offset,
    validate_block_count,
    validate_block_size,
)


class TestParseOffset:
    """Tests for parse_offset()."""

    def test_decimal(self) -> None:
        assert parse_offset("1024") == 1024

    def test_hex(self) -> None:
        assert parse_offset("0x80000") == 0x80000

    def test_zero(self) -> None:
        assert parse_offset("0") == 0

    def test_invalid(self) -> None:
        with pytest.raises(ValidationError, match="Invalid offset"):
            parse_offset("not_a_number")


class TestValidation:
    """Tests for input validation helpers."""

    def test_valid_block_size(self) -> None:
        validate_block_size(4096)

    def test_block_size_not_power_of_2(self) -> None:
        with pytest.raises(ValidationError, match="power of 2"):
            validate_block_size(1000)

    def test_block_size_zero(self) -> None:
        with pytest.raises(ValidationError, match="power of 2"):
            validate_block_size(0)

    def test_block_size_negative(self) -> None:
        with pytest.raises(ValidationError, match="power of 2"):
            validate_block_size(-512)

    def test_valid_block_count(self) -> None:
        validate_block_count(64)

    def test_block_count_zero(self) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            validate_block_count(0)

    def test_block_count_negative(self) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            validate_block_count(-1)


class TestUnifiedCLI:
    """Integration tests for the ``littlefs`` unified command."""

    def test_help(self) -> None:
        """``littlefs --help`` exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "littlefs_tools", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "create" in result.stdout
        assert "list" in result.stdout
        assert "extract" in result.stdout

    def test_version(self) -> None:
        """``littlefs --version`` prints the version."""
        from littlefs_tools import __version__

        result = subprocess.run(
            [sys.executable, "-m", "littlefs_tools", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert __version__ in result.stdout

    def test_create_subcommand(self, tmp_path: Path, sample_tree: Path) -> None:
        """``littlefs create`` produces an image file."""
        from littlefs_tools.littlefs_tools import main

        image = tmp_path / "test.bin"
        main([
            "create",
            "-s", str(sample_tree),
            "-i", str(image),
        ])
        assert image.exists()

    def test_list_subcommand(
        self, sample_image: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``littlefs list`` prints tree output."""
        from littlefs_tools.littlefs_tools import main

        main(["list", "-i", str(sample_image)])
        output = capsys.readouterr().out
        assert "test_dir1" in output

    def test_extract_subcommand(self, tmp_path: Path, sample_image: Path) -> None:
        """``littlefs extract`` creates files on disk."""
        from littlefs_tools.littlefs_tools import main

        dest = tmp_path / "out"
        main([
            "extract",
            "-i", str(sample_image),
            "-d", str(dest),
        ])
        assert (dest / "test_dir1" / "test_dir1.txt").exists()
