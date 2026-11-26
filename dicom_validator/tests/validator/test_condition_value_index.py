import pytest
from pydicom import uid

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.validation_result import ErrorCode

pytestmark = pytest.mark.usefixtures("disable_logging")


class TestConditionValueIndex:
    """Regression tests for 0-based condition value index lookup in IODValidator."""

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.VLWholeSlideMicroscopyImageStorage,
            "ImageType": ["ORIGINAL", "PRIMARY", "VOLUME", "NONE"],
        }
    )
    def test_value_3_condition_met(self, validator):
        # PS3.3 C.8.12.4: Imaged Volume Width (0048,0001) is required if
        # Image Type (0008,0008) Value 3 is VOLUME (parsed as index 2).
        result = validator.validate()
        assert has_tag_error(
            result,
            "Whole Slide Microscopy Image",
            0x0048_0001,
            ErrorCode.TagMissing,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.VLWholeSlideMicroscopyImageStorage,
            "ImageType": ["ORIGINAL", "VOLUME", "OVERVIEW", "NONE"],
        }
    )
    def test_value_3_condition_not_met_by_value_2(self, validator):
        # Value 2 is VOLUME but Value 3 is OVERVIEW, so (0048,0001) is not required.
        result = validator.validate()
        assert not has_tag_error(
            result,
            "Whole Slide Microscopy Image",
            0x0048_0001,
            ErrorCode.TagMissing,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.PositronEmissionTomographyImageStorage,
            "SeriesType": ["STATIC", "REPROJECTION"],
        }
    )
    def test_value_2_condition_met(self, validator):
        # PS3.3 C.8.9.1: Reprojection Method (0054,1004) is required if
        # Series Type (0054,1000) Value 2 is REPROJECTION (parsed as index 1).
        result = validator.validate()
        assert has_tag_error(
            result,
            "PET Series",
            0x0054_1004,
            ErrorCode.TagMissing,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.PositronEmissionTomographyImageStorage,
            "SeriesType": "REPROJECTION",
        }
    )
    def test_value_2_condition_not_met_when_vm_is_1(self, validator):
        # Only Value 1 is present (VM == 1), so a Value 2 condition must not match.
        result = validator.validate()
        assert not has_tag_error(
            result,
            "PET Series",
            0x0054_1004,
            ErrorCode.TagMissing,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.NuclearMedicineImageStorage,
            "ImageType": ["ORIGINAL", "PRIMARY", "STATIC", "TRANSMISSION"],
            "DetectorInformationSequence": [{}],
        }
    )
    def test_value_4_condition_met(self, validator):
        # PS3.3 C.8.4.11: Distance Source to Detector (0018,1110) is required if
        # Image Type Value 4 is TRANSMISSION (parsed as index 3) and Value 3 is not TOMO.
        result = validator.validate()
        assert has_tag_error(
            result,
            "NM Detector",
            0x0018_1110,
            ErrorCode.TagMissing,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.NuclearMedicineImageStorage,
            "ImageType": ["ORIGINAL", "PRIMARY", "TRANSMISSION", "EMISSION"],
            "DetectorInformationSequence": [{}],
        }
    )
    def test_value_4_condition_not_met_by_value_3(self, validator):
        # Value 3 is TRANSMISSION but Value 4 is EMISSION, so (0018,1110) is not required.
        result = validator.validate()
        assert not has_tag_error(
            result,
            "NM Detector",
            0x0018_1110,
            ErrorCode.TagMissing,
        )
