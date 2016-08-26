import os
import unittest

import pyfakefs.fake_filesystem_unittest

from dcm_spec_tools.spec_reader.spec_reader import SpecReader, SpecReaderFileError


class ReadSpecTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        super(ReadSpecTest, self).setUp()
        self.setUpPyfakefs()

    def test_missing_path(self):
        spec_path = '/var/dicom/specs'
        self.assertRaises(OSError, SpecReader, spec_path)

    def test_missing_doc_files(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.CreateFile(os.path.join('notadoc.xml'))
        self.assertRaises(SpecReaderFileError, SpecReader, spec_path)

    def test_existing_doc_files(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.CreateFile(os.path.join(spec_path, 'part03.xml'))
        self.assertTrue(SpecReader(spec_path))


if __name__ == '__main__':
    unittest.main()
