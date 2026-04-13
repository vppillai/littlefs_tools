"""Tests for auto-detection, parse_size, and shared helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    AutoDetectError,
    ValidationError,
    auto_detect,
    count_entries,
    do_create,
    do_extract,
    do_list,
    mount_image,
    parse_size,
    resolve_params,
)


class TestParseSize:
    def test_decimal(self) -> None:
        assert parse_size("1024") == 1024

    def test_hex(self) -> None:
        assert parse_size("0x40000") == 262144

    def test_kb(self) -> None:
        assert parse_size("256kb") == 262144

    def test_mb(self) -> None:
        assert parse_size("1mb") == 1048576

    def test_k_suffix(self) -> None:
        assert parse_size("256k") == 262144

    def test_case_insensitive(self) -> None:
        assert parse_size("1MB") == 1048576

    def test_invalid(self) -> None:
        with pytest.raises(ValidationError, match="Cannot parse size"):
            parse_size("notasize")


class TestAutoDetect:
    def test_basic(self, sample_image: Path) -> None:
        bs, bc = auto_detect(str(sample_image))
        assert bs == 4096
        assert bc == 64

    def test_with_offset(self, tmp_path: Path, sample_tree: Path) -> None:
        image = tmp_path / "offset.bin"
        do_create(source=str(sample_tree), image=str(image), block_size=4096, block_count=64, offset=0x1000)
        bs, bc = auto_detect(str(image), offset=0x1000)
        assert bs == 4096
        assert bc == 64

    def test_invalid_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.bin"
        bad.write_bytes(b"\x00" * 4096)
        with pytest.raises(AutoDetectError, match="Not a littleFS image"):
            auto_detect(str(bad))

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            auto_detect(str(tmp_path / "nope.bin"))


class TestResolveParams:
    def test_explicit_params(self, sample_image: Path) -> None:
        bs, bc = resolve_params(str(sample_image), 4096, 64, 0)
        assert bs == 4096
        assert bc == 64

    def test_auto_detect_both(self, sample_image: Path) -> None:
        bs, bc = resolve_params(str(sample_image), None, None, 0)
        assert bs == 4096
        assert bc == 64

    def test_auto_detect_block_count_only(self, sample_image: Path) -> None:
        bs, bc = resolve_params(str(sample_image), 4096, None, 0)
        assert bs == 4096
        assert bc == 64


class TestMountImage:
    def test_mount_and_read(self, sample_image: Path) -> None:
        fs = mount_image(str(sample_image), 4096, 64, 0)
        entries = list(fs.scandir("/"))
        assert len(entries) > 0

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            mount_image(str(tmp_path / "nope.bin"), 4096, 64, 0)


class TestCountEntries:
    def test_basic(self, sample_image: Path) -> None:
        fs = mount_image(str(sample_image), 4096, 64, 0)
        file_count, dir_count, total_bytes = count_entries(fs)
        assert file_count == 9
        assert dir_count == 9
        assert total_bytes > 0


class TestAutoDetectIntegration:
    def test_list_auto_detect(self, sample_image: Path, capsys: pytest.CaptureFixture[str]) -> None:
        do_list(image=str(sample_image))
        output = capsys.readouterr().out
        assert "test_dir1" in output

    def test_extract_auto_detect(self, tmp_path: Path, sample_image: Path) -> None:
        dest = tmp_path / "out"
        do_extract(image=str(sample_image), destination=str(dest))
        assert (dest / "test_dir1" / "test_dir1.txt").exists()
