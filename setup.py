from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='littlefs_tools',
    version='1.0.0',    
    description='Python package to create littleFS filesystem image binaries',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/vppillai/littlefs_tools',
    author='Vysakh P Pillai',
    author_email='vysakhpillai@embeddedinn.xyz',
    license='MIT',
    packages=['littlefs_tools'],
    install_requires=['littlefs-python'],
    entry_points = {
              'console_scripts': [
                'littlefs_list=littlefs_tools.littlefs_tools:list_files',
                'littlefs_create=littlefs_tools.littlefs_tools:main_entry',
                'littlefs_extract=littlefs_tools.littlefs_tools:extract_files',
              ],              
          },

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
