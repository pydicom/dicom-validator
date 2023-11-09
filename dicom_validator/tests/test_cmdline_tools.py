import logging
from pathlib import Path

import pytest

from dicom_validator.validate_iods import main


@pytest.fixture(scope="session")
def fixture_path():
    yield Path(__file__).parent / "fixtures"


@pytest.fixture
def dicom_fixture_path(fixture_path):
    yield fixture_path / "dicom"


def test_validate_sr(caplog, fixture_path, dicom_fixture_path):
    rtdose_path = dicom_fixture_path / "rtdose.dcm"
    # recreate json files to avoid getting the cached ones
    # relies on the fact that this test is run first
    cmd_line_args = [
        "-src",
        str(fixture_path),
        "-r",
        "local",
        "--recreate-json",
        str(rtdose_path),
    ]
    with caplog.at_level(logging.INFO):
        main(cmd_line_args)

    # regression test for #9
    assert "Unknown SOPClassUID" not in caplog.text
    assert "Tag (0008,1070) (Operators' Name) is missing" in caplog.text
