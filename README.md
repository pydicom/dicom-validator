# dcm-spec-tools

*dcm-spec-tools* is planned to be a collection of simple pure python command line tools which get the input from 
the DICOM standard in docbook format as provided by [ACR NEMA](http://medical.nema.org/).

Currently available tools:  
* `validate_iods` checks DICOM files for correct attributes for the given SOP class.  
* `dump_dcm_info` outputs the DICOM tag IDs and values of a given DICOM file.

Note that this is still in an early stage of development.

[pydicom](https://github.com/pydicom/pydicom) is used to read/parse DICOM 
files.

Installation
------------
The latest version is available on pypi and can be installed via
```
pip install dcm-spec-tools
```

Usage
-----
```
dump_dcm_info [-r <revision>] [-src <spec dir>] <DICOM filename>
validate_iods [-r <revision>] [-src <spec dir>] [-v] <DICOM files or directories>
```
Use the `--help` option for each script do get usage info.

Access to DICOM standard
------------------------

Upon first start of a tool, part of the latest version of the DICOM standard
in docbook format is downloaded, parsed, and the needed information saved in 
json files. These files are then used by the tools. Periodically (once a 
month), the tools check for a newer version of the DICOM standard and download 
it if found.

It is also possible to use older versions of the standard via a command line 
option, provided they are still available for download (at the time of 
writing, standards are available from 2014a to 2018b).

dcm_dump_info
-------------

This is a very simple DICOM dump tool with (currently) no options, which uses 
the DICOM dictionary as read from part 6 of the standard. The output looks 
like this:
```
(py3_test) c:\dev\GitHub\dcm-spec-tools>dump_dcm_info "c:\dev\DICOM Data\SR\image12.dcm"
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
(0008,0090) Referring Physician's Name               PN    1  []
(0008,1010) Station Name                             SH    1  [QV-00775]
(0008,1030) Study Description                        LO    1  [ABDOMEN]
(0008,1050) Performing Physician's Name              PN    1  [KLOFAS,EDWARD]
(0008,1060) Name of Physician(s) Reading Study       PN    1  []
(0008,1070) Operators' Name                          PN    1  [DO]
(0008,1080) Admitting Diagnoses Description          LO    1  [RSNA'95 Data Not Delete]
(0009,0010) [Unknown]                                LO    1  [AEGIS_DICOM_2.00]
...
```

validate_iods
-------------

This checks a given DICOM file, or all DICOM files recursively in a given 
directory, for correct tags for the related SOP class. Only the presence or  
absence of the tag, and the presence of a tag value is checked, not the 
contained value itself (a check for correct enumerated values may be added later).
This is done by looking up all required and optional modules for this 
SOP class, and checking the tags for these modules. Tags that are not allowed or 
missing in a module are listed. Parts 3 and 4 of the DICOM standard are used 
to collect the needed information.
Conditions for type 1C and 2C modules and tags are evaluated if possible. 
If the evaluation fails, the respective modules and tags are considered 
optional. Condition evaluation may fail if:
- the needed information is not contained in the DICOM file (e.g. verbose 
descriptions like "if the Patient is an animal")
- the information is related to other DICOM files (e.g. referenced images)
- the parsing failed because the condition is too complicated, unexpected, 
or due to a bug
- the related tags are retired and not listed in the current standard

The output for a single file may look like this:
```
(py3_test) c:\dev\GitHub\dcm-spec-tools>validate_iods "c:\dev\DICOM Data\SR\test.dcm"

Processing DICOM file "c:\dev\DICOM Data\SR\test.dcm"
SOP class is "1.2.840.10008.5.1.4.1.1.88.33" (Comprehensive SR IOD)

Errors
======
Module "SR Document Content":
Tag (0040,A043) (Concept Name Code Sequence) is not allowed due to condition:
  Value Type is equal to "TEXT", "NUM", "CODE", "DATETIME", "DATE", "TIME", "UIDREF" or "PNAME"
Tag (0040,A300) (Measured Value Sequence) is missing
Tag (0040,A168) (Concept Code Sequence) is missing
Tag (0008,1199) (Referenced SOP Sequence) is missing
Tag (0070,0022) (Graphic Data) is missing
Tag (0070,0023) (Graphic Type) is missing
Tag (3006,0024) (Referenced Frame of Reference UID) is missing
Tag (0040,A130) (Temporal Range Type) is missing
Tag (0040,A138) (Referenced Time Offsets) is missing due to condition:
  Referenced Sample Positions is not present and Referenced DateTime is not present
Tag (0040,A13A) (Referenced DateTime) is missing due to condition:
  Referenced Sample Positions is not present and Referenced Time Offsets is not present
```

*Note:* No guarantees are given for the correctness of the results. This is 
pre-alpha software and mostly thought as a proof of concept.