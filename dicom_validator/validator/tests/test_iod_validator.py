import json
import logging
import os
import unittest

from dicom_validator.spec_reader.edition_reader import EditionReader

from pydicom.dataset import Dataset

from dicom_validator.tests.test_utils import json_fixture_path
from dicom_validator.validator.iod_validator import IODValidator


class IODValidatorTest(unittest.TestCase):
    """Tests IODValidator.
    Note: some of the fixture data are not consistent with the DICOM Standard.
    """
    iod_specs = None
    module_specs = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(json_fixture_path(),
                               EditionReader.iod_info_json)) as info_file:
            cls.iod_specs = json.load(info_file)
        with open(os.path.join(json_fixture_path(),
                               EditionReader.module_info_json)) as info_file:
            cls.module_specs = json.load(info_file)

    def setUp(self):
        super(IODValidatorTest, self).setUp()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.DEBUG)

    def validator(self, data_set):
        return IODValidator(data_set, self.iod_specs, self.module_specs, None,
                            logging.ERROR)

    @staticmethod
    def new_data_set(tags):
        """ Create a DICOM data set with the given attributes """
        tags = tags or {}
        data_set = Dataset()
        for tag_name, value in tags.items():
            setattr(data_set, tag_name, value)
        data_set.file_meta = Dataset()
        data_set.is_implicit_VR = False
        data_set.is_little_endian = True
        return data_set

    def test_empty_dataset(self):
        data_set = self.new_data_set(tags={})
        validator = self.validator(data_set)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_invalid_sop_class_id(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.3'
        })
        validator = self.validator(data_set)
        result = validator.validate()
        self.assertIn('fatal', result)

    @staticmethod
    def has_tag_error(messages, module_name, tag_id_string, error_kind):
        if module_name not in messages:
            return False
        for message in messages[module_name]:
            if message.startswith(
                    'Tag {} is {}'.format(tag_id_string, error_kind)):
                return True
        return False

    def test_missing_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('CT Image', result)

        # PatientName is set
        self.assertFalse(
            self.has_tag_error(result, 'Patient', '(0010,0010)', 'missing'))
        # PatientSex - type 2, missing
        self.assertTrue(
            self.has_tag_error(result, 'Patient', '(0010,0040)', 'missing'))
        # Clinical Trial Sponsor Name -> type 1, but module usage U
        self.assertFalse(
            self.has_tag_error(result, 'Patient', '(0012,0010)', 'missing'))
        # Patient Breed Description -> type 2C, but no parsable condition
        self.assertFalse(
            self.has_tag_error(result, 'Patient', '(0010,2292)', 'missing'))

    def test_empty_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientName': '',
            'Modality': None
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('CT Image', result)
        # Modality - type 1, present but empty
        self.assertTrue(
            self.has_tag_error(result, 'Patient', '(0010,0040)', 'missing'))
        # PatientName - type 2, empty tag is allowed
        self.assertFalse(
            self.has_tag_error(result, 'Patient', '(0010,0010)', 'missing'))

    def test_fulfilled_condition_existing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'CArmPositionerTabletopRelationship': 'YES',
            'SynchronizationTrigger': 'SET',
            'FrameOfReferenceUID': '1.2.3.4.5.6.7.8',
            'PatientName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        # Frame Of Reference UID Is and Synchronization Trigger set
        self.assertFalse(
            self.has_tag_error(result, 'Enhanced X-Ray Angiographic Image',
                               '(0020,0052)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Synchronization',
                                            '(0018,106A)', 'missing'))

    def test_fulfilled_condition_missing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'CArmPositionerTabletopRelationship': 'YES',
            'PatientName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(result, 'Frame of Reference',
                                           '(0020,0052)', 'missing'))
        self.assertTrue(self.has_tag_error(result, 'Synchronization',
                                           '(0018,106A)', 'missing'))

    def test_condition_not_met_no_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(result, 'Frame of Reference',
                                            '(0020,0052)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Frame of Reference',
                                            '(0020,0052)', 'not allowed'))

    def test_condition_not_met_existing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'FrameOfReferenceUID': '1.2.3.4.5.6.7.8',
            'SynchronizationTrigger': 'SET',
            'PatientName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        # Frame Of Reference is allowed, Synchronization Trigger not
        self.assertFalse(self.has_tag_error(result, 'Frame of Reference',
                                            '(0020,0052)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Frame of Reference',
                                            '(0020,0052)', 'not allowed'))
        self.assertTrue(self.has_tag_error(result, 'Synchronization',
                                           '(0018,106A)', 'not allowed'))

    def test_and_condition_not_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'SECONDARY',
            'CardiacSynchronizationTechnique': 'OTHER',
            'HighRRValue': '123'  # 0018,1082
        })
        validator = self.validator(data_set)
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1081)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1082)', 'missing'))

    def test_only_one_and_condition_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'PRIMARY',
            'CardiacSynchronizationTechnique': 'OTHER',
            'HighRRValue': '123'  # 0018,1082
        })
        validator = self.validator(data_set)
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1081)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1082)', 'missing'))

    def test_and_condition_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'MIXED',
            'CardiacSynchronizationTechnique': 'PROSPECTIVE',
            'HighRRValue': '123'  # 0018,1082
        })
        validator = self.validator(data_set)
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are needed
        self.assertTrue(self.has_tag_error(result, 'Cardiac Synchronization',
                                           '(0018,1081)', 'missing'))
        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1082)', 'missing'))

    def test_presence_condition_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'PixelPaddingRangeLimit': '10',
            'PixelDataProviderURL': 'https://dataprovider'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(result, 'General Equipment',
                                           '(0028,0120)',
                                           'missing'))  # Pixel Padding Value

    def test_presence_condition_not_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'PixelPaddingRangeLimit': '10',
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(result, 'General Equipment',
                                            '(0028,0120)',
                                            'missing'))  # Pixel Padding Value

    def test_greater_condition_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'SamplesPerPixel': 3
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(result, 'Image Pixel',
                                           '(0028,0006)',
                                           'missing'))  # Planar configuration

    def test_greater_condition_not_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'SamplesPerPixel': 1
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(result, 'Image Pixel',
                                            '(0028,0006)',
                                            'missing'))  # Planar configuration

    def test_points_to_condition_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'FrameIncrementPointer': 0x00181065
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(result, 'Cardiac Synchronization',
                                           '(0018,1086)',
                                           'missing'))  # Skip beats

    def test_points_to_condition_not_met(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'FrameIncrementPointer': 0x00181055
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(result, 'Cardiac Synchronization',
                                            '(0018,1086)',
                                            'missing'))  # Skip beats

    def test_condition_for_not_required_tag_cond1_fulfilled(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'ORIGINAL',
            'CardiacSynchronizationTechnique': 'ANY'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(result, 'Cardiac Synchronization',
                                           '(0018,9085)',
                                           'missing'))  # Cardiac signal source

    def test_condition_for_not_required_tag_no_cond_fulfilled(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'ORIGINAL',
            'CardiacSynchronizationTechnique': 'NONE',
            'CardiacSignalSource': 'ECG'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertTrue(self.has_tag_error(
            result, 'Cardiac Synchronization',
            '(0018,9085)',
            'not allowed'))  # Cardiac signal source

    def test_condition_for_not_required_tag_cond2_fulfilled_present(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'DERIVED',
            'CardiacSynchronizationTechnique': 'ANY',
            'CardiacSignalSource': 'ECG'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(
            result, 'Cardiac Synchronization',
            '(0018,9085)',
            'not allowed'))  # Cardiac signal source

    def test_condition_for_not_required_tag_cond2_fulfilled_not_present(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',
            # Enhanced X-Ray Angiographic Image
            'PatientName': 'XXX',
            'PatientID': 'ZZZ',
            'ImageType': 'DERIVED',
            'CardiacSynchronizationTechnique': 'ANY'
        })
        validator = self.validator(data_set)
        result = validator.validate()

        self.assertFalse(self.has_tag_error(
            result, 'Cardiac Synchronization',
            '(0018,9085)',
            'missing'))  # Cardiac signal source


if __name__ == '__main__':
    unittest.main()
