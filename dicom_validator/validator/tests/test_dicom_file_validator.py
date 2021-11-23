import json
import logging
import os
import unittest

import pyfakefs.fake_filesystem_unittest
from pydicom import write_file
from pydicom.dataset import Dataset, FileDataset

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.tests.test_utils import json_fixture_path, \
    dicom_fixture_path
from dicom_validator.validator.dicom_file_validator import DicomFileValidator


class DicomFileValidatorTestBase(unittest.TestCase):
    iod_info = None
    module_info = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(json_fixture_path(),
                               EditionReader.iod_info_json)) as info_file:
            cls.iod_info = json.load(info_file)
        with open(os.path.join(json_fixture_path(),
                               EditionReader.module_info_json)) as info_file:
            cls.module_info = json.load(info_file)

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.validator = DicomFileValidator(self.iod_info, self.module_info)

    def tearDown(self):
        logging.disable(logging.DEBUG)


class FakeDicomFileValidatorTest(DicomFileValidatorTestBase,
                                 pyfakefs.fake_filesystem_unittest.TestCase):
    iod_info = None
    module_info = None

    def setUp(self):
        super(FakeDicomFileValidatorTest, self).setUp()
        self.setUpPyfakefs()

    @staticmethod
    def create_metadata():
        metadata = Dataset()
        metadata.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
        metadata.MediaStorageSOPInstanceUID = '1.2.3'
        metadata.TransferSyntaxUID = '1.2.840.10008.1.2'
        metadata.ImplementationClassUID = '1.3.6.1.4.1.5962.2'
        return metadata

    def assert_fatal_error(self, filename, error_string):
        error_dict = self.validator.validate(filename)
        self.assertEqual(1, len(error_dict))
        name = list(error_dict.keys())[0]
        self.assertEqual(filename, name)
        errors = error_dict[name]
        self.assertEqual({'fatal': error_string}, errors)

    def test_non_existing_file(self):
        self.assert_fatal_error('non_existing', error_string='File missing')

    def test_invalid_file(self):
        self.fs.create_file('test', contents='invalid')
        self.assert_fatal_error('test', error_string='Invalid DICOM file')

    def test_missing_sop_class(self):
        filename = 'test.dcm'
        file_dataset = FileDataset(filename, Dataset(),
                                   file_meta=self.create_metadata())
        write_file(filename, file_dataset, write_like_original=False)
        self.assert_fatal_error(filename, 'Missing SOPClassUID')

    def test_unknown_sop_class(self):
        dataset = Dataset()
        dataset.SOPClassUID = 'Unknown'
        file_dataset = FileDataset('test', dataset,
                                   file_meta=self.create_metadata())
        write_file('test', file_dataset, write_like_original=False)
        self.assert_fatal_error(
            'test',
            'Unknown SOPClassUID (probably retired): Unknown')

    def test_validate_dir(self):
        self.fs.create_dir(os.path.join('foo', 'bar', 'baz'))
        self.fs.create_dir(os.path.join('foo', 'baz'))
        self.fs.create_file(os.path.join('foo', '1.dcm'))
        self.fs.create_file(os.path.join('foo', 'bar', '2.dcm'))
        self.fs.create_file(os.path.join('foo', 'bar', '3.dcm'))
        self.fs.create_file(os.path.join('foo', 'bar', 'baz', '4.dcm'))
        self.fs.create_file(os.path.join('foo', 'baz', '5.dcm'))
        self.fs.create_file(os.path.join('foo1', '6.dcm'))

        self.assertEqual(5, len(self.validator.validate('foo')))

    def test_non_fatal_errors(self):
        dataset = Dataset()
        dataset.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
        file_dataset = FileDataset('test', dataset,
                                   file_meta=self.create_metadata())
        write_file('test', file_dataset, write_like_original=False)
        error_dict = self.validator.validate('test')
        self.assertEqual(1, len(error_dict))
        errors = error_dict['test']
        self.assertNotIn('fatal', errors)


class RealDicomFileValidatorTest(DicomFileValidatorTestBase):

    def test_that_pixeldata_is_read(self):
        # regression test for #6
        rtdose_path = os.path.join(dicom_fixture_path(), 'rtdose.dcm')
        error_dict = self.validator.validate(rtdose_path)
        self.assertEqual(1, len(error_dict))
        results = error_dict[rtdose_path]
        self.assertIn('RT Series', results)
        self.assertIn('Tag (0008,1070) is missing', results['RT Series'])
        # if PixelData is not read, RT Dose will show errors
        self.assertNotIn('RT Dose', results)
