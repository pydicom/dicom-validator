Introduction
============
``dicom-validator`` is a package that allows to check DICOM datasets
for missing or unexpected attributes. It is based on the DICOM standard
in docbook format to get the needed information, and uses
`pydicom <https://github.com/pydicom/pydicom>`__ for the handling of DICOM
datasets. The check is done by comparing the contents of the DICOM dataset
against the modules and attributes required by the DICOM standard for the
SOP class of the given dataset.

The package provides a simple API to perform this validation, and the command
line tool *validate_iods* that checks one or several DICOM files for
DICOM compliance in this regard.

The tool gets its input from the newest version of the DICOM standard (or a
specific version given as an argument or command line parameter) as provided by
`ACR NEMA <http://medical.nema.org/>`__ in docbook format.

Additionally, the command line tool *dump_dcm_info* is available that displays
the tag values of one or several DICOM files in a readable format. It is
provided as a simple proof of concept of getting information directly from the
DICOM standard.

**Disclaimer:**
No guarantees are given for the correctness of the results.
This is beta-stage software which was mostly developed as a proof of concept.
Also check the limitations for *validate_iods* described below.

Installation
~~~~~~~~~~~~

The latest version is available on pypi and can be installed via::

  pip install dicom-validator

This installs the ``dicom-validator`` package and the command line tools
``validate_iods`` and ``dump_dcm_info``.

If you need to install the latest development version, you can use::

  pip install git+https://github.com/pydicom/dicom-validator

Usage
~~~~~
::

  validate_iods [-h] [--standard-path STANDARD_PATH]
                [--edition EDITION] [--force-read] [--recreate-json]
                [--suppress-vr-warnings] [--verbose]
                dicomfiles [dicomfiles ...]

  dump_dcm_info [-h] [--standard-path STANDARD_PATH]
                [--edition EDITION] [--max-value-len MAX_VALUE_LEN]
                [--show-tags [SHOW_TAGS [SHOW_TAGS ...]]]
                [--show-image-data] [--recreate-json]
                dicomfiles [dicomfiles ...]

Use the *--help* option for each script do get more specific usage info.

Access to the DICOM standard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Upon first start of a tool, part of the latest version of the DICOM standard
in docbook format (specifically, parts 3.3, 3.4 and 3.6) are downloaded,
parsed, and the needed information saved in json files. If the *--src*
parameter is not provided, the files are downloaded to and looked up in
*<user home>/dicom-validator/*.
These files are then used by the tools. Periodically (once a month), the tools
check for a newer version of the DICOM standard and download it if found.

It is also possible to use older versions of the standard via the command line
option *--edition* or *-e*, provided they are available for download
(at the time of writing, standards are available since edition 2014a). A
list of currently available editions can be found in
*<user home>/dicom-validator/editions.json* after a tool has been called
the first time.

History
~~~~~~~
The idea for this tool came from a lunch break conversation with a colleague around
2016, who made me aware of the fact that the DICOM standard is available in docbook format.
This made me immediately question if this can be used to automate reading
the standard for use in DICOM related tools, and resulted in the toy project
``dcm-spec-tools`` that tried to do this as a proof of concept. I added a trivial
DICOM dump tool and an initial implementation of the IOD validator with the idea
that more tools might follow.
I've mostly neglected the project for a few years, but after a suggestion from
the ``pydicom`` creator Darcy Mason renamed it to ``dicom-validator`` and moved the repo
to the pydicom organization in 2021. That, and a few bug reports, caused me to renew
the work on the project to make it usable and fix the most obvious problems - which is
still an ongoing task.
