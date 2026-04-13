# littlefs-tools

[![Build Result](https://github.com/vppillai/littlefs_tools/workflows/Build_Tests/badge.svg)](https://github.com/vppillai/littlefs_tools/actions)
[![PIP Version](https://badge.fury.io/py/littlefs-tools.svg)](https://badge.fury.io/py/littlefs-tools)

A comprehensive set of tools to create, inspect, modify, and extract [littleFS](https://github.com/littlefs-project/littlefs) filesystem images.

Though distributed as a Python module, these tools are intended to be executed as command-line tools. The invocation commands are provided below.

*Attribution*: `littlefs_tools` is built on top of [littlefs-python](https://github.com/jrast/littlefs-python). To use littleFS functionality within your Python code, use `littlefs-python` directly.

## Installation

```bash
pip install littlefs_tools
```

For YAML config file support:

```bash
pip install littlefs_tools[config]
```

Requires Python 3.9 or later.

## Quick Start

```bash
# Create an image from a directory
littlefs create -s my_files/ -i image.bin

# List contents (auto-detects block size and count)
littlefs list -i image.bin

# Extract to a directory
littlefs extract -i image.bin -d output/

# Show image metadata
littlefs info -i image.bin

# Read a single file
littlefs cat -i image.bin /config.json
```

## Usage

### Unified CLI

All commands are available under the `littlefs` command:

```
littlefs [-h] [--version] [--config CONFIG_FILE]
         {create,list,extract,info,cat,du,add,remove,rename,verify,diff,attr,gc,grow,repair} ...
```

**Global options** (available for all subcommands):

| Flag | Description |
|------|-------------|
| `-b, --block_size` | Block size in bytes (auto-detected if omitted, defaults to 4096 for create) |
| `-c, --block_count` | Block count (auto-detected if omitted, defaults to 64 for create) |
| `--fs-size` | Total image size as alternative to `--block_count` (e.g. `256kb`, `1mb`, `0x40000`) |
| `-o, --offset` | Byte offset where the LFS image starts (default: 0). Supports hex (e.g. `0x80000`) |
| `-v, --verbose` | Enable verbose/debug output |
| `-q, --quiet` | Suppress informational output |
| `--config` | JSON or YAML config file for default options |

### Image Creation and Modification

#### `littlefs create`

Package a directory into a littleFS binary image.

```bash
littlefs create -s <source_dir> -i <image_file> [options]
```

| Flag | Description |
|------|-------------|
| `-s, --source` | Source directory path (required) |
| `-i, --image` | Output image file name (required) |
| `--compact` | Trim image to used blocks only (smaller file) |
| `--name-max` | Max filename length (0 = default 255) |
| `--file-max` | Max file size (0 = unlimited) |
| `--attr-max` | Max attribute size (0 = default) |
| `--read-size` | Read size (0 = default) |
| `--prog-size` | Prog size (0 = default) |
| `--cache-size` | Cache size (0 = default) |
| `--lookahead-size` | Lookahead size (0 = default) |
| `--block-cycles` | Block cycles (-1 = disable wear leveling) |
| `--disk-version` | Disk version (0 = latest) |

#### `littlefs add`

Add files or directories to an existing image.

```bash
littlefs add -i <image_file> -s <source1> [<source2> ...] [--dest /path/in/image]
```

#### `littlefs remove`

Remove files or directories from an image.

```bash
littlefs remove -i <image_file> /path/to/file [/path/to/file2 ...] [-r]
```

| Flag | Description |
|------|-------------|
| `-r, --recursive` | Remove directories recursively |

#### `littlefs rename`

Rename or move a file/directory within an image.

```bash
littlefs rename -i <image_file> /old/path /new/path
```

### Image Inspection

#### `littlefs list`

List files in an image as a tree, JSON, or CSV.

```bash
littlefs list -i <image_file> [--format tree|json|csv]
```

#### `littlefs info`

Show image metadata (version, sizes, usage, limits).

```bash
littlefs info -i <image_file> [--format table|json]
```

#### `littlefs cat`

Print a file's contents from the image to stdout.

```bash
littlefs cat -i <image_file> /path/to/file [--binary]
```

#### `littlefs du`

Show per-directory disk usage.

```bash
littlefs du -i <image_file> [/start/path] [--format table|json]
```

#### `littlefs diff`

Compare two images and show differences.

```bash
littlefs diff <image1> <image2> [--format table|json]
```

### Extraction

#### `littlefs extract`

Extract files from an image to a directory.

```bash
littlefs extract -i <image_file> -d <destination> [-f] [--file /path1 /path2] [--pattern "*.txt"]
```

| Flag | Description |
|------|-------------|
| `-d, --destination` | Destination directory (required) |
| `-f, --force` | Extract even if destination is not empty |
| `--file` | Extract only specific file path(s) |
| `--pattern` | Extract only files matching a glob pattern |

### Maintenance

#### `littlefs verify`

Validate image integrity (superblock, mount, file consistency).

```bash
littlefs verify -i <image_file>
```

#### `littlefs gc`

Run garbage collection on an image.

```bash
littlefs gc -i <image_file>
```

#### `littlefs grow`

Grow an image to a larger size.

```bash
littlefs grow -i <image_file> --new-block-count 128
littlefs grow -i <image_file> --new-size 512kb
```

#### `littlefs repair`

Repair an inconsistent image (runs `mkconsistent`).

```bash
littlefs repair -i <image_file>
```

### Extended Attributes

#### `littlefs attr`

Get, set, or remove extended attributes on files.

```bash
littlefs attr -i <image_file> --action get --path /file.txt --type 0x42
littlefs attr -i <image_file> --action set --path /file.txt --type 0x42 --data 48656c6c6f
littlefs attr -i <image_file> --action remove --path /file.txt --type 0x42
```

### Auto-Detection

For all read-oriented commands (`list`, `extract`, `info`, `cat`, `du`, `verify`, `diff`, `add`, `remove`, `rename`, `gc`, `grow`, `repair`, `attr`), the `--block_size` and `--block_count` options are **optional**. If omitted, they are automatically detected from the image's superblock. This means you can simply run:

```bash
littlefs list -i image.bin
littlefs info -i image.bin
littlefs cat -i image.bin /config.json
```

### Config Files

Use `--config` to provide default options from a JSON or YAML file:

```json
{
    "block_size": 4096,
    "block_count": 128,
    "offset": 0,
    "name_max": 128
}
```

```bash
littlefs create -s src/ -i out.bin --config littlefs.json
```

CLI arguments override config file values.

### Legacy Commands

The original standalone commands are still available for backward compatibility:

```bash
littlefs_create -s <source_dir> -i <image_file> [options]
littlefs_list -i <image_file> [options]
littlefs_extract -i <image_file> -d <destination> [options]
```

## Building the Package Locally

```bash
pip install build
python -m build
```

This produces both a source distribution and a wheel in the `dist/` directory.

Install the built wheel:

```bash
pip install dist/littlefs_tools-*.whl
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and pull request guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each release.

## About

This project was originally written as a simple CLI tool in the pre-AI era. Starting with version 1.2.0, it underwent a comprehensive AI-assisted modernization that restructured the codebase, added extensive tests, expanded the feature set, and improved documentation. The AI-assisted updates helped bring modern Python practices (type hints, proper packaging, CI/CD) and a significantly expanded feature set to the project while maintaining full backward compatibility.

-----------------
_littlefs-tools_  |  _ലിറ്റിലെഫ്എസ്-ഉപകരണങ്ങൾ_
