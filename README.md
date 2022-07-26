# littlefs_tools

Tools create, view and extract [littleFS](https://github.com/littlefs-project/littlefs) filesystem images.

Though distributed as a python module, these tools are intented to be executed as a commandline tools. Invocation commands are provided below.

## Installation

```bash
pip install littlefs_tools
```

## Usage

### littlefs_create

Tool to create a littleFS filesystem binary image.

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
usage: littlefs_list [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-v] -i IMAGE

Tool to list files in a littlefs file image

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCKSIZE, --block_size BLOCKSIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCKCOUNT, --block_count BLOCKCOUNT
                        block Count of the LFS image (defaults to 64)
  -v, --verbose         Verbose

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
```

### littlefs_extract

Tool to extract contents of a littleFS filesystem image to a destination folder.

```bash
usage: littlefs_extract [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-f] [-v] -i IMAGE -d DESTINATION

Tool to extract files from a littlefs file image

optional arguments:
  -h, --help            show this help message and exit
  -b BLOCKSIZE, --block_size BLOCKSIZE
                        block size of the LFS image (defaults to 4096)
  -c BLOCKCOUNT, --block_count BLOCKCOUNT
                        block Count of the LFS image (defaults to 64)
  -f, --force           Force extract even if destination folder is not empty
  -v, --verbose         Verbose

required arguments:
  -i IMAGE, --image IMAGE
                        image file name
  -d DESTINATION, --destination DESTINATION
                        destination directory to extract the contents into
```
