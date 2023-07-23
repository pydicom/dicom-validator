#!/usr/bin/env python
from pathlib import Path

from setuptools import setup, find_packages

from dicom_validator import __version__

EXTRA = {}

BASE_PATH = Path(__file__).parent.absolute()
with open(BASE_PATH / 'README.md') as f:
    long_description = f.read()


setup(
    name="dicom-validator",
    packages=find_packages(),
    include_package_data=True,
    version=__version__,
    install_requires=['pydicom'],
    description="Python DICOM tools using input from DICOM specs in docbook format",
    author="mrbean-bremen",
    author_email="hansemrbean@googlemail.com",
    url="https://github.com/pydicom/dicom-validator",
    keywords="dicom python",
    entry_points={
        'console_scripts': [
            'validate_iods=dicom_validator.validate_iods:main',
            'dump_dcm_info=dicom_validator.dump_dcm_info:main'
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        'Operating System :: MacOS',
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    **EXTRA
)
