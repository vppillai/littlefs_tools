# littlefs-tools

[![Build Result](https://github.com/vppillai/littlefs_tools/workflows/Build_Tests/badge.svg)](https://github.com/vppillai/littlefs_tools/actions)
[![PIP Version](https://badge.fury.io/py/littlefs-tools.svg)](https://badge.fury.io/py/littlefs-tools)

Tools create, view and extract [littleFS](https://github.com/littlefs-project/littlefs) filesystem images.

Though distributed as a python module, these tools are intended to be executed as a command-line tool. Consequently, the code is written into a single python file without classes. The Invocation commands are provided below.

*Attribution*: `littlefs_tools` are built on top of [littlefs-python](https://github.com/jrast/littlefs-python). To use littlefs functionality within your python code, please use `littlefs-python` directly.

## Installation

```bash
pip install littlefs_tools
```

## Usage

### littlefs_create

Tool to create a littleFS filesystem binary image. This tool recursively packages the contents of a source directory into a littlefs image.

```bash
usage: littlefs_create [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-i IMAGE] [-v] -s SOURCE

Tool to generate lfs images from a source folder

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCKSIZE, --block_size BLOCKSIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCKCOUNT, --block_count BLOCKCOUNT
                        block Count of the LFS image (defaults to 64)
  -i IMAGE, --image IMAGE
                        image file name
  -v, --verbose         Verbose

required arguments:
  -s SOURCE, --source SOURCE
                        source path
```

### littlefs_list

Tool to list contents of a littleFS filesystem image as a tree.

```bash
usage: littlefs_list [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-o OFFSET] [-v] -i IMAGE

Tool to list files in a littlefs file image

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCKSIZE, --block_size BLOCKSIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCKCOUNT, --block_count BLOCKCOUNT
                        block Count of the LFS image (defaults to 64)
  -o OFFSET, --offset OFFSET
                        offset (in bytes) from which the littlefs image starts(defaults to 0). Hex values are supported (e.g. 0x80000)
  -v, --verbose         Verbose

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
```

### littlefs_extract

Tool to extract contents of a littleFS filesystem image to a destination folder.

```bash
usage: littlefs_extract [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-f] [-o OFFSET] [-v] -i IMAGE -d DESTINATION

Tool to extract files from a littlefs file image

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCKSIZE, --block_size BLOCKSIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCKCOUNT, --block_count BLOCKCOUNT
                        block Count of the LFS image (defaults to 64)
  -f, --force           Force extract even if destination folder is not empty
  -o OFFSET, --offset OFFSET
                        offset (in bytes) from which the littlefs image starts(defaults to 0). Hex values are supported (e.g. 0x80000)
  -v, --verbose         Verbose

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
  -d DESTINATION, --destination DESTINATION
                        destination directory to extract the contents into
```

## Building the package locally

The tools package can be built locally using the following command:

```bash
python setup.py bdist_wheel --universal
```

And then installed with

```bash
pip install dist/littlefs_tools-1.0.0-py2.py3-none-any.whl  --force
```

> Note: The wheel package must match the version of the package. The version of the package is determined by the version of the package in the `setup.py` file.

Source distribution is created with the following command:

```bash
python setup.py sdist
```

-----------------
_littlefs-tools_  |  _ലിറ്റിലെഫ്എസ്-ഉപകരണങ്ങൾ_
