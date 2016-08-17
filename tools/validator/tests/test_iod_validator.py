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
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'iod_info.json')) as f:
            cls.iod_specs = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'module_info.json')) as f:
            cls.module_specs = json.load(f)

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
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_invalid_sop_class_id(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.3'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_missing_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ',
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('missing', result)

        # PatientsName is set
        self.assertNotIn('(0010,0010)', result['missing'])
        # PatientsSex - type 2, missing
        self.assertIn('(0010,0040)', result['missing'])  # PatientsSex
        # Clinical Trial Sponsor Name -> type 1, but module usage U
        self.assertNotIn('(0012,0010)', result['missing'])

    def test_empty_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientsName': '',
            'Modality': None
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('empty', result)
        # Modality - type 1, present but empty
        self.assertIn('(0010,0040)', result['missing'])  # PatientsSex
        # PatientsName - type 2, empty tag is allowed
        self.assertNotIn('(0010,0010)', result['missing'])


if __name__ == '__main__':
    unittest.main()
