# dcm-spec-tools

*dcm-spec-tools* is planned to be a collection of simple pure python command line tools which get the input from 
the DICOM standard in docbook format as provided by [ACR NEMA](http://medical.nema.org/).

Currently available tools:  
* `validate_iods` checks DICOM files for correct attributes for the given SOP class.  
* `dump_dcm_info` outputs the DICOM tag IDs and values of a given DICOM file.


Installation:  
`pip install dcm-spec-tools`  

Use the `--help` option for each script do get usage info.

Note that this is still in an early stage of development.

[pydicom](https://github.com/darcymason/pydicom) is used to read/parse DICOM files.
