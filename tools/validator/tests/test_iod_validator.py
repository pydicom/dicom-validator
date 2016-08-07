import json
import logging
import os
import unittest
from pydicom.dataset import Dataset

from tools.validator.iod_validator import IODValidator


class IODValidatorTest(unittest.TestCase):
    iod_specs = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'iods.json')) as f:
            cls.iod_specs = json.load(f)

    def setUp(self):
        super(IODValidatorTest, self).setUp()
        logging.disable(logging.CRITICAL)

    @staticmethod
    def new_data_set(tags):
        """ Create a DICOM data set with the given attributes """
        tags = tags or {}
        data_set = Dataset()
        for tagName, value in tags.items():
            setattr(data_set, tagName, value)
        data_set.file_meta = Dataset()
        data_set.is_implicit_VR = False
        data_set.is_little_endian = True
        return data_set

    def test_empty_dataset(self):
        data_set = self.new_data_set(tags={})
        validator = IODValidator(data_set, self.iod_specs)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_invalid_sop_class_id(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.3'
        })
        validator = IODValidator(data_set, self.iod_specs)
        result = validator.validate()
        self.assertIn('fatal', result)


if __name__ == '__main__':
    unittest.main()
