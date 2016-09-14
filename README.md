# dcm-spec-tools
___

*dcm-spec-tools* is planned to be a collection of simple pure python command line tools which get the input from 
the DICOM standard in docbook format as provided by [ACR NEMA] (http://medical.nema.org/).
A simple reader (write_specs.py) extracts the needed information and writes it back in json format.
An IOD validator (validate_iods.py) uses that information to check DICOM files for correct attributes, more tools may follow.
Currently this is in early implementation state and not usable.
[pydicom] (https://github.com/darcymason/pydicom) is used to read/parse DICOM files.
