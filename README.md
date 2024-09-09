# dicom-validator

[![PyPI version](https://badge.fury.io/py/dicom-validator.svg)](https://pypi.org/project/dicom-validator) [![Test Suite](https://github.com/pydicom/dicom-validator/workflows/Testsuite/badge.svg)](https://github.com/pydicom/dicom-validator/actions) [![Python version](https://img.shields.io/pypi/pyversions/dicom-validator.svg)](https://pypi.org/project/dicom-validator)

*dicom-validator* provides the command line tool `validate_iods` that
checks a DICOM file for missing or unexpected attributes. The check is done by
comparing the contents of the DICOM file against the modules and
attributes required by the DICOM standard for the SOP class of the given
dataset.

The tool gets its input from the newest version of the DICOM standard (or a
specific version given as command line parameter) as provided by
[ACR NEMA](http://medical.nema.org/) in docbook format.
[pydicom](https://github.com/pydicom/pydicom) is used to read and parse
the DICOM files.

Additionally, the command line tool `dump_dcm_info` is available that displays
the tag values of one or several DICOM files in a readable format. It is
provided as a proof of concept of getting information directly from the
DICOM standard.

*Disclaimer:*
No guarantees are given for the correctness of the results.
This is beta-stage software which is mostly developed as a proof of concept.
Also check the limitations for `validate_iods` described below.

*Note:*
The original name of the package (`dcm-spec-tools`) has been
changed to `dicom-validator` together with the move to the `pydicom`
organization to reflect the fact that no other tools are planned, and that the
DICOM validator is the relevant tool.


## Installation

The latest version is available on pypi and can be installed via
```
pip install dicom-validator
```

## Usage
```
validate_iods [-h] [--standard-path STANDARD_PATH]
              [--revision REVISION] [--force-read] [--recreate-json]
              [--suppress-vr-warnings] [--verbose]
              dicomfiles [dicomfiles ...]

dump_dcm_info [-h] [--standard-path STANDARD_PATH]
              [--revision REVISION] [--max-value-len MAX_VALUE_LEN]
              [--show-tags [SHOW_TAGS [SHOW_TAGS ...]]]
              [--show-image-data] [--recreate-json]
              dicomfiles [dicomfiles ...]
```
Use the `--help` option for each script do get more specific usage info.

## Access to the DICOM standard

Upon first start of a tool, part of the latest version of the DICOM standard
in docbook format (specifically, parts 3.3, 3.4 and 3.6) are downloaded,
parsed, and the needed information saved in json files. If the `--src`
parameter is not provided, the files are downloaded to and looked up in
`<user home>/dicom-validator/`.
These files are then used by the tools. Periodically (once a month), the tools
check for a newer version of the DICOM standard and download it if found.

It is also possible to use older versions of the standard via the command line
option `--revision` or `-r`, provided they are available for download
(at the time of writing, standards are available since revision 2014a). A
list of currently available editions can be found in
*<user home>/dicom-validator/editions.json* after a tool has been called
the first time.

## validate_iods

This checks a given DICOM file, or all DICOM files recursively in a given
directory, for correct tags for the related SOP class. The presence or
absence of the tag and the presence of a tag value are checked, and in the
case that an enumeration is defined for the value, the value is also checked for validity.
More checks may be added later.
This is done by looking up all required and optional modules for this
SOP class, and checking the tags for these modules. Tags that are not allowed or
missing in a module are listed. Parts 3 and 4 of the DICOM standard are used
to collect the needed information.
Conditions for type 1C and 2C modules and tags are evaluated if possible.
If the evaluation fails, the respective modules and tags are considered
optional.
The return value of the function represents the  number of errors found during the check.

The output for a single file may look like this:
```
(py3_test) c:\dev\GitHub\dicom-validator>validate_iods "c:\dev\DICOM Data\WG02\Enhanced-XA\ENHXA"

Using DICOM revision 2023c
SOP class is "1.2.840.10008.5.1.4.1.1.12.1.1" (Enhanced XA Image IOD)

Errors
======
Module "Enhanced XA/XRF Image":
Tag (0018,9410) (Planes in Acquisition) is missing

Module "Mask":
Tag (0028,6100) (Mask Subtraction Sequence) is missing

Module "X-Ray Frame Acquisition":
Tag (0018,9328) (Exposure Time in ms) is unexpected in  Multi-frame Functional Groups > (5200,9230) > (0018,9417)
Tag (0018,9332) (Exposure in mAs) is unexpected in  Multi-frame Functional Groups > (5200,9230) > (0018,9417)

Module "X-Ray Geometry":
Tag (0018,9476) (X-Ray Geometry Sequence) is missing in  Multi-frame Functional Groups > (5200,9230)

Module "XA/XRF Multi-frame Presentation":
Tag (0028,1090) (Recommended Viewing Mode) is missing in  XA/XRF Multi-frame Presentation > (0008,9458)
Tag (0028,9411) (Display Filter Percentage) is missing in  XA/XRF Multi-frame Presentation > (0008,9458)

General:
Tag (0008,0022) (Acquisition Date) is unexpected
Tag (0008,0032) (Acquisition Time) is unexpected
Tag (0028,9411) (Display Filter Percentage) is unexpected
Tag (0018,1164) (Imager Pixel Spacing) is unexpected


Process finished with exit code 6
```

### Limitations

#### Condition evaluation
As mentioned, if the evaluation of conditions fails, the related module or
tag is considered optional, which may hide some non-conformity.
Condition evaluation may fail if:
- the needed information is not directly contained in the DICOM file (e.g. verbose
  descriptions like "if the Patient is an animal", "if the image has been calibrated" etc.)
- the information is related to other DICOM files (e.g. referenced images)
- the parsing failed because the condition is too complicated, unexpected,
  or due to a bug (please write an issue if you encounter such a problem)

#### Retired tags
Only the given standard is used to evaluate the files. If
the DICOM file has been written using an older standard, it may conform to
that standard, but not to the newest one. Tags that are retired in the
version of the standard used for parsing are not considered at all.
You can always check against an older standard by using the `--revision` option.

#### Enumerated values and defined terms
Most enumerated values are checked against, but some are ignored due to parsing issues.
Support for more cases may be added in the future.
Defined terms are _not_ checked, because they are allowed to be user-defined, which means
that any value may be valid.

#### Unsupported cases (support may be added in future versions)
- SOP classes not in the table in PS3.3 such as Presentation States are not
  handled


## dump_dcm_info

This is a very simple DICOM dump tool, which uses
the DICOM dictionary as read from part 6 of the standard. It prints the
DICOM header of the given DICOM file, or of all DICOM files recursively in a
given directory. The output looks like this:
```
(py3_test) c:\dev\GitHub\dicom-validator>dump_dcm_info "c:\dev\DICOM
Data\SR\image12.dcm"

c:\dev\DICOM Data\SR\image12.dcm
(0005,0010) [Unknown]                                LO    1  [AEGIS_DICOM_2.00]
(0005,1000) [Unknown]                                UN    1  [\x00\x05 \x08\x00\x00\x00\n  RIGHT   \x00\x05\xc1X\x00\x00\x00\x06 0.09 \x00\x05...]
(0008,0008) Image Type                               CS    0  []
(0008,0016) SOP Class UID                            UI    1  [Ultrasound Image Storage (Retired)]
(0008,0018) SOP Instance UID                         UI    1  [1.2.840.113680.3.103.775.2873347909.282313.2]
(0008,0020) Study Date                               DA    1  [19950119]
(0008,0030) Study Time                               TM    1  [092854.0]
(0008,0050) Accession Number                         SH    1  [ACN000001]
(0008,0060) Modality                                 CS    1  [US]
(0008,0070) Manufacturer                             LO    1  [Acuson]
(0008,0090) Referring Physician's Name               ON    1  []
(0008,1010) Station Name                             SH    1  [QV-00775]
(0008,1030) Study Description                        LO    1  [ABDOMEN]
(0008,1050) Performing Physician's Name              ON    1  [DOE,JOHN]
(0008,1060) Name of Physician(s) Reading Study       ON    1  []
(0008,1070) Operators' Name                          ON    1  [DO]
(0008,1080) Admitting Diagnoses Description          LO    1  [RSNA'95 Data Not Delete]
(0009,0010) [Unknown]                                LO    1  [AEGIS_DICOM_2.00]
...
```

If you want to show only specific tags, you can use the option `--show-tags`:
```
(py3_test) c:\dev\GitHub\dicom-validator>dump_dcm_info "c:\dev\DICOM Data\SR\image12.dcm" --show-tags 0010,0010 PatientID

c:\dev\DICOM Data\SR\image12.dcm
(0010,0010) Patient's Name                           ON    1  [DOE^JANE]
(0010,0020) Patient ID                               LO    1  [ACN000001]
```

## Build executable on Windows

A self-contained Windows executable is contained in the release artifacts.

Here is a sample workflow to build such an executable yourself:
```powershell
# Clone the repository
git clone git@github.com:pydicom/dicom-validator.git

# Create a virtual environment and activate it
cd dicom-validator
virtualenv venv
venv\Scripts\activate

# Install dependencies for development
pip install -r requirements-dev.txt

# Build executables. They will be placed in the `dist` subfolder.
pyinstaller dicom-validator.spec -y
```

## Contributing
Contributions are very welcome. If you submit a pull request for a bugfix
or a new feature, please make sure to also write respective tests.
