import logging

import pydicom
import pytest
from pydicom import DataElement, uid, Sequence, dcmwrite, dcmread
from pydicom.datadict import dictionary_VR
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.filebase import DicomBytesIO
from pydicom.tag import Tag

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.iod_validator import IODValidator
from dicom_validator.validator.validation_result import Status, ErrorCode

pytestmark = pytest.mark.usefixtures("disable_logging")


def new_data_set(tags, ds: Dataset | None = None):
    """Create a DICOM data set with the given attributes"""
    tags = tags or {}
    data_set = ds or Dataset()
    if not tags:
        return data_set
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
    # write the dataset into a file and read it back to ensure the real behavior
    if "SOPInstanceUID" not in data_set:
        data_set.SOPInstanceUID = "1.2.3"
    data_set.file_meta = FileMetaDataset()
    data_set.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    fp = DicomBytesIO()
    kwargs = (
        {"write_like_original": False}
        if int(pydicom.__version_info__[0]) < 3
        else {"enforce_file_format": True}
    )
    dcmwrite(fp, data_set, **kwargs)
    fp.seek(0)
    return dcmread(fp)


@pytest.fixture
def validator(dicom_info, request):
    marker = request.node.get_closest_marker("tag_set")
    if marker is None:
        tag_set = {}
    else:
        tag_set = marker.args[0]
    data_set = new_data_set(tag_set)
    return IODValidator(data_set, dicom_info, logging.WARNING)


class TestIODValidator:
    """Tests IODValidator.
    Note: some of the fixture data are not consistent with the DICOM Standard.
    """

    def test_empty_dataset(self, validator, caplog):
        caplog.set_level(logging.ERROR)
        result = validator.validate()
        assert result.status == Status.MissingSOPClassUID
        assert result.errors == 1
        assert [rec.message for rec in caplog.records] == [
            "Missing SOP Class UID - aborting"
        ]

    @pytest.mark.tag_set({"SOPClassUID": "1.2.3"})
    def test_invalid_sop_class_id(self, validator, caplog):
        caplog.set_level(logging.ERROR)
        result = validator.validate()
        assert result.status == Status.UnknownSOPClassUID
        assert result.errors == 1
        assert [rec.message for rec in caplog.records] == [
            "Unknown or retired SOP Class UID: 1.2.3 - aborting"
        ]

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_missing_tags(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        assert result.status == Status.Failed
        assert "Patient" in result.module_errors

        # PatientName is set
        assert not has_tag_error(result, "Patient", 0x0010_0010, ErrorCode.TagMissing)
        # PatientSex - type 2, missing
        assert has_tag_error(result, "Patient", 0x0010_0040, ErrorCode.TagMissing)
        # Clinical Trial Sponsor Name -> type 1, but module usage U
        assert not has_tag_error(result, "Patient", 0x0012_0010, ErrorCode.TagMissing)
        # Patient Breed Description -> type 2C, but no parsable condition
        assert not has_tag_error(result, "Patient", 0x0010_2292, ErrorCode.TagMissing)

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Patient":' in messages
        assert "Tag (0010,0040) (Patient's Sex) is missing" in messages

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "MultienergyCTAcquisition": "YES",
            "CTAdditionalXRaySourceSequence": [],
        }
    )
    def test_not_allowed_tag(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        assert result.status == Status.Failed
        assert has_tag_error(result, "CT Image", 0x0018_9360, ErrorCode.TagNotAllowed)

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "CT Image":' in messages
        assert (
            "Tag (0018,9360) (CT Additional X-Ray Source Sequence) is not allowed by condition:\n"
            '  Multi-energy CT Acquisition is equal to "YES"' in messages
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
            "PatientName": "",
            "Modality": None,
        }
    )
    def test_empty_tags(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        assert result.status == Status.Failed
        assert "Patient" in result.module_errors
        # Modality - type 1, present but empty
        assert has_tag_error(result, "Patient", 0x0010_0040, ErrorCode.TagMissing)
        # PatientName - type 2, empty tag is allowed
        assert not has_tag_error(result, "Patient", 0x0010_0010, ErrorCode.TagMissing)

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Patient":' in messages
        assert "Tag (0010,0040) (Patient's Sex) is missing" in messages

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
            "TypeOfPatientID": "lowercase",  # VR is CS, which is required to be uppercase
            "Modality": None,
        }
    )
    def test_vr_conflict(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        assert result.status == Status.Failed
        assert "Patient" in result.module_errors
        assert has_tag_error(result, "Patient", 0x0010_0022, ErrorCode.InvalidValue)

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Patient":' in messages
        assert (
            "Tag (0010,0022) (Type of Patient ID) has invalid value 'lowercase' for VR CS"
            in messages
        )

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
            result,
            "Enhanced X-Ray Angiographic Image",
            0x0020_0052,
            ErrorCode.TagMissing,
        )
        assert not has_tag_error(
            result, "Synchronization", 0x0018_106A, ErrorCode.TagMissing
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "CArmPositionerTabletopRelationship": "YES",
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_fulfilled_condition_missing_tag(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        assert has_tag_error(
            result, "Frame of Reference", 0x0020_0052, ErrorCode.TagMissing
        )
        assert has_tag_error(
            result, "Synchronization", 0x0018_106A, ErrorCode.TagMissing
        )
        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Frame of Reference":' in messages
        assert "Tag (0020,0052) (Frame of Reference UID) is missing" in messages
        assert '\nModule "Synchronization":' in messages
        assert "Tag (0018,106A) (Synchronization Trigger) is missing" in messages

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
        }
    )
    def test_condition_not_met_no_tag(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "Frame of Reference", 0x0020_0052, ErrorCode.TagMissing
        )
        assert not has_tag_error(
            result, "Frame of Reference", 0x0020_0052, ErrorCode.TagNotAllowed
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
        assert not has_tag_error(
            result, "General", 0x0019_1001, ErrorCode.TagUnexpected
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "SECONDARY",
            "CardiacSynchronizationTechnique": "OTHER",
            "HighRRValue": "123",  # 0018_1082
        }
    )
    def test_and_condition_not_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        assert not has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1081, ErrorCode.TagMissing
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1082, ErrorCode.TagMissing
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "PRIMARY",
            "CardiacSynchronizationTechnique": "OTHER",
            "HighRRValue": "123",  # 0018_1082
        }
    )
    def test_only_one_and_condition_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are not needed but allowed
        assert not has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1081, ErrorCode.TagMissing
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1082, ErrorCode.TagMissing
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "MIXED",
            "CardiacSynchronizationTechnique": "PROSPECTIVE",
            "HighRRValue": "123",  # 0018_1082
        }
    )
    def test_and_condition_met(self, validator):
        result = validator.validate()

        # Both Low R-R Value and High R-R Value are needed
        assert has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1081, ErrorCode.TagMissing
        )
        assert not has_tag_error(
            result, "Cardiac Synchronization", 0x0018_1082, ErrorCode.TagMissing
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "PixelPaddingRangeLimit": 10,
            "PixelDataProviderURL": "https://dataprovider",
        }
    )
    def test_presence_condition_met(self, validator):
        result = validator.validate()

        assert has_tag_error(
            result, "General Equipment", 0x0028_0120, ErrorCode.TagMissing
        )  # Pixel Padding Value

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "PixelPaddingRangeLimit": 10,
        }
    )
    def test_presence_condition_not_met(self, validator):
        result = validator.validate()

        assert not has_tag_error(
            result, "General Equipment", 0x0028_0120, ErrorCode.TagMissing
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
            result, "Image Pixel", 0x0028_0006, ErrorCode.TagMissing
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
            result, "Image Pixel", 0x0028_0006, ErrorCode.TagMissing
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
            result, "Cardiac Synchronization", 0x0018_1086, ErrorCode.TagMissing
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
            result, "Cine", 0x0018_1065, ErrorCode.TagMissing
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
            result, "Cardiac Synchronization", 0x0018_9085, ErrorCode.TagMissing
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
            result, "Cardiac Synchronization", 0x0018_9085, ErrorCode.TagNotAllowed
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
            result, "Cardiac Synchronization", 0x0018_9085, ErrorCode.TagNotAllowed
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
            result, "Cardiac Synchronization", 0x0018_9085, ErrorCode.TagMissing
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
            result, "SR Document Content", 0x0040_A300, ErrorCode.TagMissing
        )  # Measured Value Sequence

        # condition not met for other macros - no tags expected
        assert not has_tag_error(
            result, "SR Document Content", 0x0040_A168, ErrorCode.TagMissing
        )  # Concept Code Sequence
        assert not has_tag_error(
            result, "SR Document Content", 0x0008_1199, ErrorCode.TagMissing
        )  # Referenced SOP Sequence
        assert not has_tag_error(
            result, "SR Document Content", 0x0070_0022, ErrorCode.TagMissing
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
    def test_invalid_enum_value(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        # Presentation LUT Shape: incorrect enum value
        assert has_tag_error(
            result,
            "Enhanced XA/XRF Image",
            0x2050_0020,
            ErrorCode.EnumValueNotAllowed,
            {"value": "INVALID", "allowed": ["IDENTITY", "INVERSE"]},
        )

        # Content Qualification: correct enum value
        assert not has_tag_error(
            result, "Enhanced XA/XRF Image", 0x0018_9004, ErrorCode.EnumValueNotAllowed
        )

        # Bits Stored: incorrect int enum value
        assert has_tag_error(
            result,
            "Enhanced XA/XRF Image",
            0x0028_0101,
            ErrorCode.EnumValueNotAllowed,
            {"value": 1, "allowed": [8, 9, 10, 11, 12, 13, 14, 15, 16]},
        )

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Enhanced XA/XRF Image":' in messages
        assert (
            "Tag (0028,0101) (Bits Stored) - enum value '1' not allowed,\n"
            "  allowed values: 8, 9, 10, 11, 12, 13, 14, 15, 16"
        ) in messages

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.CTImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ReconstructionTargetCenterPatient": [0, -188, -1179.45],
        }
    )
    def test_multilist_fd(self, validator):
        # regression test for #166
        result = validator.validate()
        # Reconstruction Target Center Patient has a list as value
        # that shall be handled like MultiValue
        assert not has_tag_error(
            result,
            "CT Image",
            0x0018_9318,
            ErrorCode.InvalidValue,
        )

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.EnhancedXAImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "ImageType": "DERIVED",
            "PresentationLUTShape": "",
        }
    )
    def test_empty_type_1_enum_value(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()

        # Presentation LUT Shape: incorrect enum value
        assert has_tag_error(
            result,
            "Enhanced XA/XRF Image",
            0x2050_0020,
            ErrorCode.TagEmpty,
        )
        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Enhanced XA/XRF Image":' in messages
        assert "Tag (2050,0020) (Presentation LUT Shape) is empty" in messages

    @pytest.mark.tag_set(
        {
            "SOPClassUID": uid.OphthalmicPhotography8BitImageStorage,
            "PatientName": "XXX",
            "PatientID": "ZZZ",
            "PatientEyeMovementCommanded": "",
            "PupilDilated": "",
        }
    )
    def test_empty_type_2_enum_value(self, validator):
        # regression test for #147
        result = validator.validate()

        assert not has_tag_error(
            result,
            "Ophthalmic Photography Acquisition Parameters",
            0x0022_0005,
            ErrorCode.EnumValueNotAllowed,
        )

        assert not has_tag_error(
            result,
            "Ophthalmic Photography Acquisition Parameters",
            0x0022_000D,
            ErrorCode.EnumValueNotAllowed,
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
            0x0018_0020,
            ErrorCode.EnumValueNotAllowed,
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
            0x0018_0020,
            ErrorCode.EnumValueNotAllowed,
            {"value": "IV", "allowed": ["SE", "IR", "GR", "EP", "RM"]},
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
            0x0008_0008,
            ErrorCode.EnumValueNotAllowed,
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
            0x0008_0008,
            ErrorCode.EnumValueNotAllowed,
            {"value": "SECONDARY", "allowed": ["PRIMARY"]},
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
            0x0008_0008,
            ErrorCode.EnumValueNotAllowed,
            {"value": "ORIGINAL", "allowed": ["PRIMARY"]},
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
