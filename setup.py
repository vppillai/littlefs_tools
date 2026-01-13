from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="littlefs_tools",
    version="1.1.7",
    description="Python package to create littleFS filesystem image binaries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vppillai/littlefs_tools",
    author="Vysakh P Pillai",
    author_email="vysakhpillai@embeddedinn.com",
    license="MIT",
    packages=["littlefs_tools"],
    install_requires=["littlefs-python", "colorama"],
    entry_points={
        "console_scripts": [
            "littlefs_list=littlefs_tools.littlefs_tools:list_files",
            "littlefs_create=littlefs_tools.littlefs_tools:create_image",
            "littlefs_extract=littlefs_tools.littlefs_tools:extract_files",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Filesystems",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14"
    ],
)
