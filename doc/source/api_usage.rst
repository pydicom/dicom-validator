Using the validation API
========================
While the easiest way to use the package is by using the command line tool,
it is also possible to include the validation logic in another Python package.
This chapter describes how the package can be used programmatically.

.. note:: The described API is preliminary and subject to change.

The Edition Reader
------------------
The validation works using the information extracted from a specific edition of
the DICOM standard. The :class:`~dicom_validator.spec_reader.edition_reader.EditionReader`
is responsible for the download of the docbook version of the standard, the extraction of
the relevant information into `json` files, and for loading this information into a
:class:`~dicom_validator.validator.dicom_info.DicomInfo` object.
To get the DICOM information you can use
:meth:`~dicom_validator.spec_reader.edition_reader.EditionReader.load_dicom_info`:

.. code:: python

    # uses the default location <user home>/dicom-validator
    reader = EditionReader()
    # if the edition is not downloaded yet, load_dicom_info will download and process it
    dicom_info = reader.load_dicom_info("2025b")

You can also use a custom location to store the DICOM standard by using the optional `path`
argument for the `EditionReader`.

The DICOM File Validator
------------------------
The validator tool uses the :class:`~dicom_validator.validator.dicom_file_validator.DicomFileValidator`
class for the validation of one or more DICOM files. If you directly want to work on DICOM files,
this is the easiest way:

.. code:: python

    from dicom_validator.validator.dicom_file_validator import DicomFileValidator

    # here we use the DICOM info read by the edition reader
    validator = DicomFileValidator(dicom_info)
    result = validator.validate(dicom_file_path)

This returns a dictionary with DICOM file names as keys, and the corresponding validation result of
type :class:`~dicom_validator.validator.validation_result.ValidationResult` as value. It also
prints the output to the console, which is likely not what you want. You can change this by providing
a custom error handler, as described further below.

The IOD Validator
-----------------
The DICOM file validator is based on the :class:`~dicom_validator.validator.iod_validator.IODValidator`,
which uses a single DICOM dataset as input. If you are reading your DICOM file using `pydicom` and
want to validate the loaded dataset as part of your processing, you can use this class instead
of the file validator. It also allows to pass a custom error via the `error_handler` argument.
In the simplest case (with the default logging error handler) this could look like this:

.. code:: python

    from dicom_validator.validator.iod_validator import IODValidator
    from pydicom import dcmread

    ds = dcmread("path/to/dicom/file")
    ... # other handling of the dataset
    validator = IODValidator(ds, dicom_info)
    result = validator.validate()

In this case, `result` is a single object of type
:class:`~dicom_validator.validator.validation_result.ValidationResult`, which you can
handle with your own logic (check the :ref:`API documentation <validation_result>` for details
on the result class).

Error Handling
--------------
The :ref:`API documentation <error_handling>` describes the classes used for error handling.
Per default, a :class:`~dicom_validator.validator.error_handler.LoggingResultHandler` is used
for handling the data. Note that the result is handled `after` the processing of each dataset.
That means that if using :class:`~dicom_validator.validator.iod_validator.IODValidator`, the result is
handled (e.g., by default logged) only at the end of the validation, and after the validation of
each file if using :class:`~dicom_validator.validator.dicom_file_validator.DicomFileValidator`.
This is done with the assumption that validating a single dataset is fast, and there is no need
to handle each error directly as it appears (if this assumption turns out not to hold, this
behavior may change in the future).

Note that the error handling API is very simple. If you do not want to do any handling, you
can write a null handler:

.. code:: python

    from dicom_validator.validator.error_handler import ValidationResultHandler

    class NullValidationResultHandler(ValidationResultHandler):
        """Handler that does nothing."""

        def handle_validation_start(self, result: ValidationResult):
            pass

        def handle_validation_result(self, result: ValidationResult):
            pass

And use this for your validation:

.. code:: python

    validator = IODValidator(ds, dicom_info, error_handler=NullValidationResultHandler())
    result = validator.validate()
    # handle result yourself

You could also move your result handling into `handle_validation_result`.
The more useful option is to base your handler on
:class:`~dicom_validator.validator.error_handler.ValidationResultHandlerBase`. This already provides
a number of methods that you can implement to handle several parts of the validation result, for
example start handling a failing module or handle a tag error.
An example of how to do this can be found in the example class
:class:`~dicom_validator.validator.html_error_handler.HtmlErrorHandler`, which creates a simple HTML
page with a list of the validation errors (which is not very useful as is, but can be used as a base
for your own handler).
