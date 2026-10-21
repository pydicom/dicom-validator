from http.client import BadStatusLine, CannotSendHeader, HTTPException, HTTPSConnection
from socket import gaierror
from ssl import SSLError
from unittest.mock import Mock

import pytest

from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.html_error_handler import HtmlErrorHandler

URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.html"


@pytest.fixture
def connection(monkeypatch):
    connection = Mock(spec=HTTPSConnection)
    connection.getresponse.return_value.status = 200
    monkeypatch.setattr(
        "dicom_validator.validator.html_error_handler.HTTPSConnection",
        Mock(return_value=connection),
    )
    monkeypatch.setattr(HtmlErrorHandler, "valid_refs", {})
    return connection


@pytest.mark.parametrize(
    "status, expected",
    [(200, True), (302, True), (399, True), (400, False), (404, False), (500, False)],
)
def test_url_status(connection, status, expected):
    connection.getresponse.return_value.status = status
    assert HtmlErrorHandler.url_exists(URL) is expected
    connection.request.assert_called_once_with(
        "HEAD", "/medical/dicom/current/output/chtml/part03/sect_C.7.html"
    )
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("stage", ["request", "getresponse"])
@pytest.mark.parametrize(
    "error",
    [
        OSError,
        TimeoutError,
        gaierror,
        SSLError,
        HTTPException,
        BadStatusLine,
        CannotSendHeader,
        ValueError,
        TypeError,
    ],
)
def test_url_failure(connection, stage, error):
    getattr(connection, stage).side_effect = error("unavailable")
    assert HtmlErrorHandler.url_exists(URL) is False
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("error", [OSError, HTTPException])
def test_url_close_failure(connection, error):
    connection.close.side_effect = error("close failed")
    assert HtmlErrorHandler.url_exists(URL) is False
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("error", [OSError, HTTPException])
def test_url_connection_failure(monkeypatch, error):
    monkeypatch.setattr(
        "dicom_validator.validator.html_error_handler.HTTPSConnection",
        Mock(side_effect=error("connection failed")),
    )
    assert HtmlErrorHandler.url_exists(URL) is False


def test_unexpected_error_is_not_suppressed(connection):
    connection.getresponse.side_effect = RuntimeError("unexpected")
    with pytest.raises(RuntimeError, match="unexpected"):
        HtmlErrorHandler.url_exists(URL)
    connection.close.assert_called_once_with()


def test_offline_report_has_module_name_without_link(connection):
    connection.request.side_effect = OSError("offline")
    dicom_info = DicomInfo(
        {}, {"1.2.3": {"modules": {"Patient": {"ref": "C.7.1.1"}}}}, {}
    )
    handler = HtmlErrorHandler(dicom_info)
    handler.sop_class = "1.2.3"
    handler.handle_module_errors_start("Patient", {})
    assert handler.html == "<h3>Patient</h3>\n<ul>"
    assert connection.close.call_count == 4
    assert not handler.valid_refs


def test_parent_section_is_used_and_cached(connection):
    connection.getresponse.side_effect = [Mock(status=404), Mock(status=200)]
    handler = HtmlErrorHandler(DicomInfo({}, {}, {}))
    parent_url = handler.url_for_ref("C.8.8")
    assert handler.valid_url_for_ref("C.8.8.1") == parent_url
    assert [call.args for call in connection.request.call_args_list] == [
        ("HEAD", "/medical/dicom/current/output/chtml/part03/sect_C.8.8.1.html"),
        ("HEAD", "/medical/dicom/current/output/chtml/part03/sect_C.8.8.html"),
    ]
    assert connection.close.call_count == 2
    assert handler.valid_url_for_ref("C.8.8.1") == parent_url
    assert connection.request.call_count == 2
