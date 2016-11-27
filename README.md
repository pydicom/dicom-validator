# dcm-spec-tools

*dcm-spec-tools* is planned to be a collection of simple pure python command line tools which get the input from 
the DICOM standard in docbook format as provided by [ACR NEMA](http://medical.nema.org/).

Currently available:

* `get_dcm_specs` gets the DICOM specs of the wanted version from the official site.
* `write_dcm_specs` extracts the needed information and writes it back in json format.
* `validate_iods` uses that information to check DICOM files for correct attributes

Installation:
`pip install git+https://github.com/mrbean-bremen/dcm-spec-tools@master` (Linux)  
`pip install https://github.com/mrbean-bremen/dcm-spec-tools/archive/master.zip` (Windows)  
Use the `--help` option for each script do get usage info.

Note that this is work in progress and not fully usable.

[pydicom](https://github.com/darcymason/pydicom) is used to read/parse DICOM files.
