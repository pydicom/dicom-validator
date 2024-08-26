import logging
from typing import Optional

import pytest
from pydicom import DataElement, uid, Sequence
from pydicom.datadict import dictionary_VR
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.tag import Tag

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.iod_validator import IODValidator

pytestmark = pytest.mark.usefixtures("disable_logging")


def new_data_set(tags, ds: Optional[Dataset] = None):
    """Create a DICOM data set with the given attributes"""
    tags = tags or {}
    data_set = ds or Dataset()
    for tag, value in tags.items():
        tag = Tag(tag)  # raises for invalid tag
        try:
            vr = dictionary_VR(tag)
        except KeyError:
            vr = "LO"
        if vr == "SQ":
            items = []
            for item_tags in value:
                items.append(new_data_set(item_tags, data_set))
            value = Sequence(items)
        data_set[tag] = DataElement(tag, vr, value)
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
            "SOPClassUID": uid.CTImageStorage,
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
            "SOPClassUID": uid.CTImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "MultienergyCTAcquisition": "YES",
            "CTAdditionalXRaySourceSequence": [],
        }
    )
    def test_not_allowed_tag(self, validator):
        result = validator.validate()

        assert "fatal" not in result
        assert has_tag_error(result, "CT Image", "(0018,9360)", "not allowed")

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
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
            "SOPClassUID": uid.CTImageStorage,
            "TypeOfPatientID": "lowercase",  # VR is CS, which is required to be uppercase
            "Modality": None,
        }
    )
    def test_vr_conflict(self, validator):
        result = validator.validate()

        assert "fatal" not in result
        assert "CT Image" in result
        assert has_tag_error(result, "Patient", "(0010,0022)", "conflicting")

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.MultiFrameSingleBitSecondaryCaptureImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.EnhancedXAImageStorage,
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
            "SOPClassUID": uid.XRayRadiationDoseSRStorage,
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

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "DERIVED",
            "PresentationLUTShape": "INVALID",
            "ContentQualification": "PRODUCT",
            "BitsStored": 1,
        }
    )
    def test_invalid_enum_value(self, validator):
        result = validator.validate()

        # Presentation LUT Shape: incorrect enum value
        assert has_tag_error(
            result,
            "Enhanced XA/XRF Image",
            "(2050,0020)",
            "value is not allowed",
            "(value: INVALID, allowed: IDENTITY, INVERSE)",
        )

        # Content Qualification: correct enum value
        assert not has_tag_error(
            result, "Enhanced XA/XRF Image", "(0018,9004)", "value is not allowed"
        )

        # Bits Stored: incorrect int enum value
        assert has_tag_error(
            result,
            "Enhanced XA/XRF Image",
            "(0028,0101)",
            "value is not allowed",
            "(value: 1, allowed: 8, 9, 10, 11, 12, 13, 14, 15, 16)",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.MRImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ScanningSequence": ["SE", "EP"],
        }
    )
    def test_valid_multi_valued_enum(self, validator):
        result = validator.validate()

        # Scanning Sequence - all values allowed
        assert not has_tag_error(
            result,
            "MR Image",
            "(0018,0020)",
            "value is not allowed",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.MRImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ScanningSequence": ["SE", "EP", "IV"],
        }
    )
    def test_invalid_multi_valued_enum(self, validator):
        result = validator.validate()

        # Scanning Sequence - IV not allowed
        assert has_tag_error(
            result,
            "MR Image",
            "(0018,0020)",
            "value is not allowed",
            "(value: IV, allowed: SE, IR, GR, EP, RM)",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.OphthalmicOpticalCoherenceTomographyBscanVolumeAnalysisStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": ["ORIGINAL", "PRIMARY"],
        }
    )
    def test_valid_indexed_enum(self, validator):
        result = validator.validate()

        # Image Type - both values correct
        assert not has_tag_error(
            result,
            "Ophthalmic Optical Coherence Tomography B-scan Volume Analysis Image",
            "(0008,0008)",
            "value is not allowed",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.OphthalmicOpticalCoherenceTomographyBscanVolumeAnalysisStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": ["ORIGINAL", "SECONDARY"],
        }
    )
    def test_invalid_indexed_enum(self, validator):
        result = validator.validate()

        # Image Type - second value incorrect
        assert has_tag_error(
            result,
            "Ophthalmic Optical Coherence Tomography B-scan Volume Analysis Image",
            "(0008,0008)",
            "value is not allowed",
            "(value: SECONDARY, allowed: PRIMARY)",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.OphthalmicOpticalCoherenceTomographyBscanVolumeAnalysisStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": ["PRIMARY", "ORIGINAL"],
        }
    )
    def test_indexed_enum_incorrect_index(self, validator):
        result = validator.validate()

        # Image Type - allowed values at incorrect index
        assert has_tag_error(
            result,
            "Ophthalmic Optical Coherence Tomography B-scan Volume Analysis Image",
            "(0008,0008)",
            "value is not allowed",
            "(value: ORIGINAL, allowed: PRIMARY)",
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.GrayscaleSoftcopyPresentationStateStorage,
            "GraphicAnnotationSequence": [
                {
                    "GraphicLayer": "TEST_LAYER",
                    "GraphicObjectSequence": [
                        {
                            "GraphicAnnotationUnits": "PIXEL",
                            "GraphicDimensions": 2,
                            "GraphicData": [318, 1555, 714, 1778],
                            "GraphicType": "POLYLINE",
                            "GraphicFilled": "N",
                        }
                    ],
                }
            ],
            "GraphicLayerSequence": [
                {
                    "GraphicLayer": "TEST_LAYER",
                }
            ],
        }
    )
    def test_incorrect_parsed_type(self, validator):
        # regression test for exception, see #115
        modules = validator._dicom_info.modules
        modules["C.10.5"]["(0070,0001)"]["items"]["(0070,0009)"]["items"][
            "(0070,0024)"
        ]["cond"] = {
            "index": 0,
            "op": "=",
            "tag": "(0070,0022)",
            "type": "MU",
            "values": ["closed"],
        }
        assert validator.validate()
