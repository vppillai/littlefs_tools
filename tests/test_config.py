"""Tests for config file support."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import ValidationError, load_config


class TestLoadConfig:
    def test_json_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"block_size": 512, "block_count": 128}))
        config = load_config(str(config_file))
        assert config["block_size"] == 512
        assert config["block_count"] == 128

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(str(tmp_path / "nope.json"))

    def test_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{{")
        with pytest.raises(ValidationError, match="Failed to parse JSON"):
            load_config(str(bad))

    def test_empty_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.json"
        config_file.write_text("{}")
        config = load_config(str(config_file))
        assert config == {}
