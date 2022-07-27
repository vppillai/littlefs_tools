import os
import sys
import argparse
from pathlib import Path
from littlefs import LittleFS
import logging
from colorama import init
from colorama import Fore, Back, Style

init(autoreset=True)


logger = logging.getLogger("littlefs_tools")


def set_log_level(verbose):
    logging.basicConfig(format="%(levelname)s - %(lineno)d - %(message)s")
    if verbose:
        print("setting logger level to debug")
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


###########################################################################################################################################
# Image content listing tools
###########################################################################################################################################
def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def _print_tree(fs, path):
    try:
        depth = path.count("/") - 1
        fsContent = fs.scandir(path)
        for item in fsContent:
            logger.debug(f"{item.name} {item.type}")
            if item.type == 2:
                print(f"  {depth*'    '}{Fore.CYAN}{item.name}")
                _print_tree(fs, f"{path}/{item.name}")
            else:
                print(
                    f"  {depth*'    '}{Fore.RED}*---{Fore.YELLOW}{item.name} {('',f'({sizeof_fmt(item.size)})')[item.type==1]}"
                )
    except Exception as e:
        logger.critical(e)
        exit(-2)


def _lsfiles(args):
    try:
        fs = LittleFS(
            block_size=args.blockSize, block_count=args.blockCount, mount=False
        )
        with open(args.image, "rb") as fh:
            fs.context.buffer = bytearray(fh.read())
        fs.mount()
        print(f"{Fore.GREEN}{args.image}")
        _print_tree(fs, "/")

    except Exception as e:
        logger.critical(e)
        exit(-2)


def list_files():
    parser = argparse.ArgumentParser(
        description=f"Tool to list files in a littlefs file image", prog="littlefs_list"
    )
    parser.add_argument(
        "-b",
        "--block_size",
        dest="blockSize",
        help="block size of the LFS image (defaults to 4096)",
        type=int,
        default=4096,
    )
    parser.add_argument(
        "-c",
        "--block_count",
        dest="blockCount",
        help="block Count of the LFS image (defaults to 64) ",
        type=int,
        default=64,
    )
    parser.add_argument("-v", "--verbose", help="Verbose", action="store_true")

    requiredNamed = parser.add_argument_group("required arguments")
    requiredNamed.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True
    )
    args = parser.parse_args()

    set_log_level(args.verbose)

    _lsfiles(args)


#############################################################################################################################
# Image Extraction tools
#############################################################################################################################
def _walk_fs_tree(fs, path, destination):
    try:
        fsContent = fs.scandir(path)
        for item in fsContent:
            logger.debug(f"{item.name} {item.type}")
            if item.type == 1:  # type=File
                with fs.open(f"{path}/{item.name}", "rb") as fh:
                    with open(f"{destination}/{path}/{item.name}", "wb") as f:
                        f.write(fh.read())
            if item.type == 2:  # type=Folder
                Path(f"{destination}/{path}/{item.name}").mkdir(
                    parents=True, exist_ok=True
                )
                _walk_fs_tree(fs, f"{path}/{item.name}", destination)
    except Exception as e:
        logger.critical(e)
        exit(-2)


def _extract_files(args):
    try:
        # check if args.destination exists and is an empty folder
        if (
            not args.force
            and os.path.exists(args.destination)
            and os.listdir(args.destination)
        ):
            logger.critical(f"{args.destination} is not an empty folder")
            exit(-1)

        fs = LittleFS(
            block_size=args.blockSize, block_count=args.blockCount, mount=False
        )
        with open(args.image, "rb") as fh:
            fs.context.buffer = bytearray(fh.read())
        fs.mount()
        Path(args.destination).mkdir(parents=True, exist_ok=True)
        _walk_fs_tree(fs, "/", args.destination)
        print(f"Extracted files to {args.destination}")
    except Exception as e:
        logger.critical(e)
        exit(-2)


def extract_files():
    parser = argparse.ArgumentParser(
        description=f"Tool to extract files from a littlefs file image",
        prog="littlefs_extract",
    )
    parser.add_argument(
        "-b",
        "--block_size",
        dest="blockSize",
        help="block size of the LFS image (defaults to 4096)",
        type=int,
        default=4096,
    )
    parser.add_argument(
        "-c",
        "--block_count",
        dest="blockCount",
        help="block Count of the LFS image (defaults to 64) ",
        type=int,
        default=64,
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Force extract even if destination folder is not empty",
        action="store_true",
    )
    parser.add_argument("-v", "--verbose", help="Verbose", action="store_true")

    requiredNamed = parser.add_argument_group("required arguments")
    requiredNamed.add_argument(
        "-i", "--image", dest="image", help="image file name", required=True
    )
    requiredNamed.add_argument(
        "-d",
        "--destination",
        dest="destination",
        help="destination directory to extract the contents into",
        required=True,
    )
    args = parser.parse_args()

    set_log_level(args.verbose)

    _extract_files(args)


###########################################################################################################################################
# Image creation tools
###########################################################################################################################################
def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix) :]


def globPath(args):
    try:
        fs = LittleFS(block_size=args.blockSize, block_count=args.blockCount)
        contentSize = 0
        for path, subdirs, files in os.walk(args.source):
            for subdir in subdirs:
                lfsDir = os.path.join("/", remove_prefix(path, args.source), subdir)
                if "/" != lfsDir:
                    fs.mkdir(lfsDir)
                    logger.info(f"LFS Directory : {lfsDir}")

            for name in files:
                filePath = os.path.join(path, name)
                lfsPath = os.path.join("/", remove_prefix(filePath, args.source))

                with open(filePath, "rb") as file:
                    fileSize = os.path.getsize(filePath)
                    contentSize += fileSize
                    if contentSize > (args.blockSize * (args.blockCount - 2)):
                        logger.critical(
                            "Contents wont fit into the disk. Plese adjust block size and block count"
                        )
                        logger.critical(f"\tTotal Contents size = {contentSize} Bytes")
                        logger.critical(
                            f"\tImage size [{args.blockSize} x {args.blockCount}] = {args.blockSize*args.blockCount} Bytes"
                        )
                        exit(-1)
                    with fs.open(lfsPath, "wb") as fh:
                        logger.info(f"LFS File   : {lfsPath} ({fileSize} Bytes)")
                        byte = file.read(1)
                        while byte:
                            fh.write(byte)
                            byte = file.read(1)
        print(f"\nTotal Contents size = {contentSize} Bytes")

        # Dump the filesystem content to a file
        with open(args.image, "wb") as fh:
            fh.write(fs.context.buffer)

    except Exception as e:
        logger.critical(e)
        exit(-2)


def create_image():
    parser = argparse.ArgumentParser(
        description=f"Tool to generate lfs images from a source folder",
        prog="littlefs_create",
    )
    parser.add_argument(
        "-b",
        "--block_size",
        dest="blockSize",
        help="block size of the LFS image (defaults to 4096)",
        type=int,
        default=4096,
    )
    parser.add_argument(
        "-c",
        "--block_count",
        dest="blockCount",
        help="block Count of the LFS image (defaults to 64) ",
        type=int,
        default=64,
    )
    parser.add_argument(
        "-i", "--image", dest="image", help="image file name", default="test.bin"
    )
    parser.add_argument("-v", "--verbose", help="Verbose", action="store_true")

    requiredNamed = parser.add_argument_group("required arguments")
    requiredNamed.add_argument(
        "-s", "--source", dest="source", help="source path", required=True
    )
    args = parser.parse_args()

    set_log_level(args.verbose)

    globPath(args)

    print(
        f"Created `{args.image}` of size [{args.blockSize} x {args.blockCount}] = {args.blockSize*args.blockCount} Bytes"
    )
