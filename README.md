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
json files. These files are then used by the tools. Periodically (one a 
month), the tools check for a newer version of the DICOM standard and download 
it if found.

It is also possible to use older versions of the standard via a command line 
option, provided they are still available for download. 

