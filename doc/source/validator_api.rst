Classes related to the validation API
=====================================

Validation Logic
----------------
.. autoclass:: dicom_validator.validator.iod_validator.IODValidator
    :members: __init__, validate

.. autoclass:: dicom_validator.validator.dicom_file_validator.DicomFileValidator
    :members: __init__, validate, validate_dir, validate_file

Validation result
-----------------
.. automodule:: dicom_validator.validator.validation_result
    :members: DicomTag, ErrorCode, ErrorScope, Status, TagError, TagType, ValidationResult

Error handling
--------------
.. automodule:: dicom_validator.validator.error_handler
    :members: ValidationResultHandlerBase, ValidationResultHandler, LoggingResultHandler
