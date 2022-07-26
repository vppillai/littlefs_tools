# lfs-create

Tool to package the contents of a folder into a [littleFS](https://github.com/littlefs-project/littlefs) binary image.

Though distributed as a python module, this tools is primarily intented to be executed as a commandline tool by invoking `littlefs-create`

## Usage

```bash
usage: littlefs-create [-h] [-b BLOCKSIZE] [-c BLOCKCOUNT] [-i IMAGE] [-v] -s
                  SOURCE

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
