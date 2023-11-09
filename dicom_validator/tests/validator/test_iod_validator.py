import logging

import pytest
from pydicom import DataElement
from pydicom.dataset import Dataset, FileMetaDataset

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.iod_validator import IODValidator

pytestmark = pytest.mark.usefixtures("disable_logging")


def new_data_set(tags):
    """Create a DICOM data set with the given attributes"""
    tags = tags or {}
    data_set = Dataset()
    for tag, value in tags.items():
        if isinstance(tag, int):
            data_set[tag] = DataElement(tag, "LO", value)
        else:
            setattr(data_set, tag, value)
    data_set.file_meta = FileMetaDataset()
    data_set.is_implicit_VR = False
    data_set.is_little_endian = True
    return data_set


@pytest.fixture
def validator(dicom_info, request):
    marker = request.node.get_closest_marker("tag_set")
    if marker is None:
        tag_set = {}
    else:
        tag_set = marker.args[0]
    data_set = new_data_set(tag_set)
    return IODValidator(data_set, dicom_info, logging.ERROR)


class TestIODValidator:
    """Tests IODValidator.
    Note: some of the fixture data are not consistent with the DICOM Standard.
    """

    def test_empty_dataset(self, validator):
        result = validator.validate()
        assert "fatal" in result

    @pytest.mark.tag_set({"SOPClassUID": "1.2.3"})
    def test_invalid_sop_class_id(self, validator):
        result = validator.validate()
        assert "fatal" in result

    @pytest.mark.tag_set(
        {
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.2",  # CT
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_missing_tags(self, validator):
        result = validator.validate()

        assert "fatal" not in result
        assert "CT Image" in result

        # PatientName is set
        assert not has_tag_error(result, "Patient", "(0010,0010)", "missing")
        # PatientSex - type 2, missing
        assert has_tag_error(result, "Patient", "(0010,0040)", "missing")
        # Clinical Trial Sponsor Name -> type 1, but module usage U
        assert not has_tag_error(result, "Patient", "(0012,0010)", "missing")
        # Patient Breed Description -> type 2C, but no parsable condition
        assert not has_tag_error(result, "Patient", "(0010,2292)", "missing")

    @pytest.mark.tag_set(
        {
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.2",  # CT
            "PatientName": "",
            "Modality": None,
        }
    )
    def test_empty_tags(self, validator):
        result = validator.validate()

        assert "fatal" not in result
        assert "CT Image" in result
        # Modality - type 1, present but empty
        assert has_tag_error(result, "Patient", "(0010,0040)", "missing")
        # PatientName - type 2, empty tag is allowed
        assert not has_tag_error(result, "Patient", "(0010,0010)", "missing")

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "CArmPositionerTabletopRelationship": "YES",
            "SynchronizationTrigger": "SET",
            "FrameOfReferenceUID": "1.2.3.4.5.6.7.8",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_fulfilled_condition_existing_tag(self, validator):
        result = validator.validate()

        # Frame Of Reference UID Is and Synchronization Trigger set
        assert not has_tag_error(
            result, "Enhanced X-Ray Angiographic Image", "(0020,0052)", "missing"
        )
        assert not has_tag_error(result, "Synchronization", "(0018,106A)", "missing")

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "CArmPositionerTabletopRelationship": "YES",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_fulfilled_condition_missing_tag(self, validator):
        result = validator.validate()

        assert has_tag_error(result, "Frame of Reference", "(0020,0052)", "missing")
        assert has_tag_error(result, "Synchronization", "(0018,106A)", "missing")

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_condition_not_met_no_tag(self, validator):
        result = validator.validate()

        assert not has_tag_error(result, "Frame of Reference", "(0020,0052)", "missing")
        assert not has_tag_error(
            result, "Frame of Reference", "(0020,0052)", "not allowed"
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            0x00191001: "unknown",
        }
    )
    def test_private_tags_are_ignored(self, validator):
        result = validator.validate()
        assert not has_tag_error(result, "Root", "(0019,1001)", "unexpected")

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "SECONDARY",
            "CardiacSynchronizationTechnique": "OTHER",
            "HighRRValue": "123",  # 0018,1082
        }
    )
    def test_and_condition_not_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1081)", "missing"
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1082)", "missing"
        )

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "PRIMARY",
            "CardiacSynchronizationTechnique": "OTHER",
            "HighRRValue": "123",  # 0018,1082
        }
    )
    def test_only_one_and_condition_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1081)", "missing"
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1082)", "missing"
        )

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "MIXED",
            "CardiacSynchronizationTechnique": "PROSPECTIVE",
            "HighRRValue": "123",  # 0018,1082
        }
    )
    def test_and_condition_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are needed
        assert has_tag_error(
            result, "Cardiac Synchronization", "(0018,1081)", "missing"
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1082)", "missing"
        )

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "PixelPaddingRangeLimit": "10",
            "PixelDataProviderURL": "https://dataprovider",
        }
    )
    def test_presence_condition_met(self, validator):
        result = validator.validate()

        assert has_tag_error(
            result, "General Equipment", "(0028,0120)", "missing"
        )  # Pixel Padding Value

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "PixelPaddingRangeLimit": "10",
        }
    )
    def test_presence_condition_not_met(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "General Equipment", "(0028,0120)", "missing"
        )  # Pixel Padding Value

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "SamplesPerPixel": 3,
        }
    )
    def test_greater_condition_met(self, validator):
        result = validator.validate()

        assert has_tag_error(
            result, "Image Pixel", "(0028,0006)", "missing"
        )  # Planar configuration

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "SamplesPerPixel": 1,
        }
    )
    def test_greater_condition_not_met(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "Image Pixel", "(0028,0006)", "missing"
        )  # Planar configuration

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "FrameIncrementPointer": 0x00181055,
        }
    )
    def test_points_to_condition_not_met(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,1086)", "missing"
        )  # Skip beats

    @pytest.mark.tag_set(
        {
            # Multi-frame Single Bit Secondary Capture Image Storage
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.7.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "FrameIncrementPointer": 0x00181065,
        }
    )
    def test_for_frame_pointer_condition_not_met(self, validator):
        # regression test for #58
        result = validator.validate()

        assert has_tag_error(
            result, "Cine", "(0018,1065)", "missing"
        )  # Frame Time Vector

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "ORIGINAL",
            "CardiacSynchronizationTechnique": "ANY",
        }
    )
    def test_condition_for_not_required_tag_cond1_fulfilled(self, validator):
        result = validator.validate()

        assert has_tag_error(
            result, "Cardiac Synchronization", "(0018,9085)", "missing"
        )  # Cardiac signal source

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "ORIGINAL",
            "CardiacSynchronizationTechnique": "NONE",
            "CardiacSignalSource": "ECG",
        }
    )
    def test_condition_for_not_required_tag_no_cond_fulfilled(self, validator):
        result = validator.validate()

        assert has_tag_error(
            result, "Cardiac Synchronization", "(0018,9085)", "not allowed"
        )  # Cardiac signal source

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "DERIVED",
            "CardiacSynchronizationTechnique": "ANY",
            "CardiacSignalSource": "ECG",
        }
    )
    def test_condition_for_not_required_tag_cond2_fulfilled_present(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,9085)", "not allowed"
        )  # Cardiac signal source

    @pytest.mark.tag_set(
        {
            # Enhanced X-Ray Angiographic Image
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.12.1.1",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "DERIVED",
            "CardiacSynchronizationTechnique": "ANY",
        }
    )
    def test_condition_for_not_required_tag_cond2_fulfilled_not_present(
        self, validator
    ):
        result = validator.validate()

        assert not has_tag_error(
            result, "Cardiac Synchronization", "(0018,9085)", "missing"
        )  # Cardiac signal source

    @pytest.mark.tag_set(
        {
            # X-Ray Radiation Dose SR Storage
            "SOPClassUID": "1.2.840.10008.5.1.4.1.1.88.67",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "DERIVED",
            "ValueType": "NUM",
        }
    )
    def test_conditional_includes(self, validator):
        result = validator.validate()

        # condition met (ValueType is NUM) - error because of missing tag
        assert has_tag_error(
            result, "SR Document Content", "(0040,A300)", "missing"
        )  # Measured Value Sequence

        # condition not met for other macros - no tags expected
        assert not has_tag_error(
            result, "SR Document Content", "(0040,A168)", "missing"
        )  # Concept Code Sequence
        assert not has_tag_error(
            result, "SR Document Content", "(0008,1199)", "missing"
        )  # Referenced SOP Sequence
        assert not has_tag_error(
            result, "SR Document Content", "(0070,0022)", "missing"
        )  # Graphic Data
