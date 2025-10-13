from pathlib import Path

import pytest
from pydicom import uid

from dicom_validator.validator.dicom_file_validator import DicomFileValidator
from dicom_validator.validator.html_error_handler import HtmlErrorHandler
from dicom_validator.validator.error_handler import (
    ValidationResultHandler,
)
from dicom_validator.validator.validation_result import (
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
