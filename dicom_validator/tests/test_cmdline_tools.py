import os
import unittest

from dicom_validator.tests.test_utils import dicom_fixture_path, fixture_path
from dicom_validator.validate_iods import main


class ValidatorTest(unittest.TestCase):

    @unittest.skip('FIXME: Does not work with TextTestRunner')
    def test_validate_sr(self):
        rtdose_path = os.path.join(dicom_fixture_path(), 'rtdose.dcm')
        cmd_line_args = ['-src', fixture_path(), '-r', 'local', rtdose_path]
        with self.assertLogs('validator', level='INFO') as cm:
            main(cmd_line_args)

        output = ''.join(cm.output)
        # regression test for #9
        self.assertNotIn('Unknown SOPClassUID', output)
        self.assertIn("Tag (0008,1070) (Operators' Name) is missing", output)
