#!/usr/bin/env python
import os

from setuptools import setup, find_packages

EXTRA = {}

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(BASE_PATH, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name="dcm-spec-tools",
    packages=find_packages(),
    include_package_data=True,
    version="0.3.0",
    install_requires=['pydicom'],
    description="Python DICOM tools using input from DICOM specs in docbook format",
    author="mrbean-bremen",
    author_email="hansemrbean@googlemail.com",
    url="http://github.com/mrbean-bremen/dcm-spec-tools",
    keywords="dicom python",
    entry_points={
        'console_scripts': [
            'validate_iods=dcm_spec_tools.validate_iods:main',
            'dump_dcm_info=dcm_spec_tools.dump_dcm_info:main'
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    **EXTRA
)
