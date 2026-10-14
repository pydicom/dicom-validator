from html.parser import HTMLParser
from pathlib import Path

import pytest

from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.html_error_handler import HtmlErrorHandler
from dicom_validator.validator.validation_result import ValidationResult


class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_data(self, data):
        self.text.append(data)


@pytest.mark.parametrize("path_type", [str, Path])
def test_filename_is_report_text(path_type):
    filename = 'scan <img src=x onerror=alert(1)> & "quoted".dcm'
    result = ValidationResult(sop_class_uid="1.2.3", file_path=path_type(filename))
    handler = HtmlErrorHandler(DicomInfo({}, {}, {}))
    handler.handle_validation_result_start(result)
    handler.handle_validation_result_end(result)
    parser = HeadingParser()
    parser.feed(handler.html)
    assert parser.tags == ["html", "body", "h2", "br"]
    assert "".join(parser.text) == filename + "SOP Class 1.2.3"


def test_missing_filename_has_no_line_break():
    handler = HtmlErrorHandler(DicomInfo({}, {}, {}))
    handler.handle_validation_result_start(ValidationResult(sop_class_uid="1.2.3"))
    assert handler.html == "<h2>SOP Class 1.2.3</h2>"
