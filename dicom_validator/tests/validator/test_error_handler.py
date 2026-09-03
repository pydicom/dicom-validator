import logging
from pathlib import Path

import pytest
from pydicom import DataElement, uid

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.dicom_file_validator import DicomFileValidator
from dicom_validator.validator.error_handler import (
    NullValidationResultHandler,
    ValidationResultFormatter,
    ValidationResultHandler,
)
from dicom_validator.validator.html_error_handler import HtmlErrorHandler
from dicom_validator.validator.validation_result import (
    DicomTag,
    ErrorCode,
    Status,
    ValidationResult,
)


class GenericErrorHandler(ValidationResultHandler):
    def __init__(self):
        self.logs = []

    def handle_validation_start(self, result: ValidationResult):
        self.logs.append("Starting Validation")

    def handle_validation_result(self, result: ValidationResult):
        self.logs.append("Finished Validation")
        self.logs.append(f"Status: {result.status.name}")
        self.logs.append(f"Error: {result.errors}")


@pytest.mark.tag_set(
    {
        "SOPClassUID": uid.CTImageStorage,
        "PatientName": "XXX",
        "PatientID": "ZZZ",
    }
)
def test_generic_error_handler(validator) -> None:
    handler = GenericErrorHandler()
    validator.handler = handler
    result = validator.validate()
    nr_errors = result.errors
    assert handler.logs == [
        "Starting Validation",
        "Finished Validation",
        "Status: Failed",
        f"Error: {nr_errors}",
    ]


@pytest.fixture(scope="module")
def dicom_fixture_path():
    yield Path(__file__).parent.parent / "fixtures" / "dicom"


def test_html_error_handler(dicom_info, dicom_fixture_path) -> None:
    rtdose_path = dicom_fixture_path / "rtdose.dcm"
    handler = HtmlErrorHandler(dicom_info)
    validator = DicomFileValidator(dicom_info, error_handler=handler)
    validator.validate(rtdose_path)
    assert (
        '<h3><a href="https://dicom.nema.org/medical/dicom/current/output/chtml/part03'
        '/sect_C.8.8.html">RT Series</a></h3>' in handler.html
    )


def test_html_error_handler_failed_validation(dicom_info, validator) -> None:
    """Check that a failed validation is reported."""
    handler = HtmlErrorHandler(dicom_info)
    validator.handler = handler
    validator.validate()
    assert "<p>Missing SOP Class UID</p>" in handler.html


@pytest.mark.tag_set(
    {
        "SOPClassUID": uid.CTImageStorage,
        "DerivationCodeSequence": DataElement(
            "DerivationCodeSequence", "OB", b"\x00" * 10
        ),
    }
)
def test_html_error_handler_invalid_sequence(dicom_info, validator) -> None:
    """Check that an invalid sequence is reported."""
    handler = HtmlErrorHandler(dicom_info)
    validator.handler = handler
    validator.validate()
    assert (
        "<li>(0008,9215) (Derivation Code Sequence)"
        " is not a valid sequence, ignoring it</li>" in handler.html
    )


def test_null_validation_result_handler(validator, caplog) -> None:
    """Check that validation happens with a null handler, but nothing is logged."""
    validator.handler = NullValidationResultHandler()
    with caplog.at_level(logging.DEBUG):
        result = validator.validate()

    assert result.status == Status.MissingSOPClassUID
    assert result.errors == 1
    assert caplog.records == []


@pytest.mark.tag_set(
    {
        "SOPClassUID": uid.CTImageStorage,
        "PatientName": "XXX",
        "PatientID": "ZZZ",
    }
)
def test_null_validation_result_handler_with_module_errors(validator, caplog) -> None:
    """Check module errors are found with the null handler."""
    validator.handler = NullValidationResultHandler()
    with caplog.at_level(logging.DEBUG):
        result = validator.validate()

    assert has_tag_error(result, "Patient", 0x0010_0040, ErrorCode.TagMissing)
    assert caplog.records == []


@pytest.mark.tag_set(
    {
        "SOPClassUID": uid.CTImageStorage,
        "PatientName": "XXX",
        "PatientID": "ZZZ",
        "UltrasoundColorDataPresent": 1,  # triggers TagUnexpected
    }
)
def test_formatter_error_message_tag_unexpected(validator) -> None:
    """Check unexpected tags are correctly converted to human-readable text."""
    validator.handler = NullValidationResultHandler()
    result = validator.validate()
    tag_error = result.module_errors["General"].get(DicomTag(0x0028_0014))
    assert tag_error is not None

    formatter = ValidationResultFormatter()
    assert formatter.error_message(tag_error) == " is unexpected"


@pytest.mark.tag_set(
    {
        "SOPClassUID": uid.CTImageStorage,
        "PatientName": "XXX",
        "PatientID": "ZZZ",
        "MultienergyCTAcquisition": "YES",
        "CTAdditionalXRaySourceSequence": [],
    }
)
def test_formatter_error_message_tag_not_allowed(dicom_info, validator) -> None:
    """Check formatting of text for tags that are not allowed by a condition.

    Based on test_iod_validator.py::test_not_allowed_tag
    """
    validator.handler = NullValidationResultHandler()
    result = validator.validate()
    tag_error = result.module_errors["CT Image"].get(DicomTag(0x0018_9360))
    assert tag_error is not None

    # without a dictionary, condition text is left out
    formatter = ValidationResultFormatter()
    assert formatter.error_message(tag_error) == " is not allowed"

    # with a dictionary, the condition is rendered too
    formatter = ValidationResultFormatter(dicom_info.dictionary)
    assert formatter.error_message(tag_error) == (
        " is not allowed by condition:\n"
        '  Multi-energy CT Acquisition is equal to "YES"'
    )


@pytest.mark.parametrize(
    "result,expected",
    [
        (
            ValidationResult(status=Status.MissingSOPClassUID),
            "Missing SOP Class UID",
        ),
        (
            ValidationResult(status=Status.UnknownSOPClassUID, sop_class_uid="1.2.3"),
            "Unknown or retired SOP Class UID: 1.2.3",
        ),
        (
            ValidationResult(status=Status.MissingFile, file_path="foo.dcm"),
            "Missing DICOM File: foo.dcm",
        ),
        (
            ValidationResult(status=Status.InvalidFile, file_path="foo.dcm"),
            "Not a DICOM File: foo.dcm - ignoring",
        ),
        (ValidationResult(status="UNKNOWN"), "Unknown error"),
    ],
    ids=[
        "missing-sop-class-uid",
        "unknown-sop-class-uid",
        "missing-file",
        "invalid-file",
        "unknown-status",
    ],
)
def test_formatter_failed_validation_message(result, expected) -> None:
    """Check that every failed-validation status maps to the correct message."""
    formatter = ValidationResultFormatter()
    assert formatter.failed_validation_message(result) == expected
