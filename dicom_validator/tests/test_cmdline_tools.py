import logging
import os

from dicom_validator.tests.test_utils import dicom_fixture_path, fixture_path
from dicom_validator.validate_iods import main


def test_validate_sr(caplog):
    rtdose_path = os.path.join(dicom_fixture_path(), 'rtdose.dcm')
    cmd_line_args = ['-src', fixture_path(), '-r', 'local', rtdose_path]
    with caplog.at_level(logging.INFO):
        main(cmd_line_args)

    # regression test for #9
    assert 'Unknown SOPClassUID' not in caplog.text
    assert "Tag (0008,1070) (Operators' Name) is missing" in caplog.text
