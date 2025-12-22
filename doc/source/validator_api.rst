Classes related to the validation API
=====================================

DICOM Edition reader
--------------------
.. autoclass:: dicom_validator.validator.dicom_info.DicomInfo

.. autoclass:: dicom_validator.spec_reader.edition_reader.EditionReader
    :members:

Validation Logic
----------------
.. autoclass:: dicom_validator.validator.iod_validator.IODValidator
    :members: __init__, validate

.. autoclass:: dicom_validator.validator.dicom_file_validator.DicomFileValidator
    :members: __init__, validate, validate_dir, validate_file

.. _validation_result:

Validation result
-----------------
.. automodule:: dicom_validator.validator.validation_result
    :members: DicomTag, ErrorCode, ErrorScope, Status, TagError, TagType, ValidationResult

.. _error_handling:

Error handling
--------------
Base classes
~~~~~~~~~~~~
.. autoclass:: dicom_validator.validator.error_handler.ValidationResultHandler
    :members:

.. autoclass:: dicom_validator.validator.error_handler.ValidationResultHandlerBase
    :members:

Default error handler
~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: dicom_validator.validator.error_handler.LoggingResultHandler
    :members:

Example error handler
~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: dicom_validator.validator.html_error_handler.HtmlErrorHandler
    :members:
