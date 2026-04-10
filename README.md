# littlefs-tools

[![Build Result](https://github.com/vppillai/littlefs_tools/workflows/Build_Tests/badge.svg)](https://github.com/vppillai/littlefs_tools/actions)
[![PIP Version](https://badge.fury.io/py/littlefs-tools.svg)](https://badge.fury.io/py/littlefs-tools)

Tools to create, view, and extract [littleFS](https://github.com/littlefs-project/littlefs) filesystem images.

Though distributed as a Python module, these tools are intended to be executed as command-line tools. The invocation commands are provided below.

*Attribution*: `littlefs_tools` is built on top of [littlefs-python](https://github.com/jrast/littlefs-python). To use littleFS functionality within your Python code, use `littlefs-python` directly.

## Installation

```bash
pip install littlefs_tools
```

Requires Python 3.9 or later.

## Usage

### Unified CLI

All commands are available under a single `littlefs` command:

```bash
littlefs create -s <source_dir> -i <image_file> [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-v]
littlefs list -i <image_file> [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-v]
littlefs extract -i <image_file> -d <destination> [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-f] [-v]
```

Run `littlefs --help` for full usage, or `littlefs <command> --help` for command-specific help.

### littlefs create

Package a directory into a littleFS binary image.

```
usage: littlefs create [-h] [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-v] -s SOURCE -i IMAGE

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCK_SIZE, --block_size BLOCK_SIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCK_COUNT, --block_count BLOCK_COUNT
                        block count of the LFS image (defaults to 64)
  -i IMAGE, --image IMAGE
                        output image file name
  -o OFFSET, --offset OFFSET
                        offset (in bytes) from which the littlefs image starts
                        (defaults to 0). Hex values are supported (e.g. 0x80000)
  -v, --verbose         enable verbose/debug output

required arguments:
  -s SOURCE, --source SOURCE
                        source directory path
```

### littlefs list

Display the file tree of a littleFS binary image.

```
usage: littlefs list [-h] [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-v] -i IMAGE

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCK_SIZE, --block_size BLOCK_SIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCK_COUNT, --block_COUNT BLOCK_COUNT
                        block count of the LFS image (defaults to 64)
  -o OFFSET, --offset OFFSET
                        offset (in bytes) from which the littlefs image starts
                        (defaults to 0). Hex values are supported (e.g. 0x80000)
  -v, --verbose         enable verbose/debug output

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
```

### littlefs extract

Extract all files from a littleFS binary image to a directory.

```
usage: littlefs extract [-h] [-b BLOCK_SIZE] [-c BLOCK_COUNT] [-o OFFSET] [-f] [-v] -i IMAGE -d DESTINATION

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCK_SIZE, --block_size BLOCK_SIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCK_COUNT, --block_count BLOCK_COUNT
                        block count of the LFS image (defaults to 64)
  -o OFFSET, --offset OFFSET
                        offset (in bytes) from which the littlefs image starts
                        (defaults to 0). Hex values are supported (e.g. 0x80000)
  -f, --force           force extract even if destination folder is not empty
  -v, --verbose         enable verbose/debug output

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
  -d DESTINATION, --destination DESTINATION
                        destination directory to extract the contents into
```

### Legacy Commands

The original standalone commands are still available for backward compatibility:

```bash
littlefs_create -s <source_dir> -i <image_file> [options]
littlefs_list -i <image_file> [options]
littlefs_extract -i <image_file> -d <destination> [options]
```

## Building the Package Locally

Install build tools and build:

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

-----------------
_littlefs-tools_  |  _ലിറ്റിലെഫ്എസ്-ഉപകരണങ്ങൾ_
