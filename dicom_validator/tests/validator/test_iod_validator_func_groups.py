import logging

import pytest
from pydicom import Sequence, uid
from pydicom.dataset import Dataset, FileMetaDataset

from dicom_validator.tests.utils import has_tag_error
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.iod_validator import IODValidator
from dicom_validator.validator.validation_result import (
    ValidationResult,
    TagErrors,
    ErrorCode,
    ErrorScope,
    DicomTag,
)

pytestmark = pytest.mark.usefixtures("disable_logging")


def new_data_set(shared_macros, per_frame_macros):
    """Create a DICOM data set with the given attributes"""
    data_set = Dataset()
    data_set.SOPClassUID = uid.EnhancedXAImageStorage
    data_set.PatientName = "XXX"
    data_set.PatientID = "ZZZ"
    data_set.ImageType = "DERIVED\\SECONDARY"
    data_set.InstanceNumber = "1"
    data_set.ContentDate = "20000101"
    data_set.ContentTime = "120000"
    data_set.NumberOfFrames = "3"
    mask_subtraction_seq = Sequence()
    item = Dataset()
    item.MaskOperation = "AVG_SUB"
    mask_subtraction_seq.append(item)
    data_set.MaskSubtractionSequence = mask_subtraction_seq

    shared_groups = Sequence()
    if shared_macros:
        item = Dataset()
        for macro in shared_macros:
            add_contents_to_item(item, macro)
        shared_groups.append(item)
    data_set.SharedFunctionalGroupsSequence = shared_groups

    per_frame_groups = Sequence()
    if per_frame_macros:
        for i in range(3):
            # we don't care about the tag contents, we just put the same values
            # into each per-frame item
            item = Dataset()
            for macro in per_frame_macros:
                add_contents_to_item(item, macro)
            per_frame_groups.append(item)
    data_set.PerFrameFunctionalGroupsSequence = per_frame_groups

    data_set.file_meta = FileMetaDataset()
    data_set.file_meta.TransferSyntaxUID = uid.ExplicitVRLittleEndian
    return data_set


def add_contents_to_item(item, contents):
    for name, content in contents.items():
        if isinstance(content, list):
            value = Sequence()
            add_items_to_sequence(value, content)
        else:
            value = content
        setattr(item, name, value)


def add_items_to_sequence(sequence, contents):
    for content in contents:
        item = Dataset()
        add_contents_to_item(item, content)
        sequence.append(item)


@pytest.fixture
def validator(dicom_info, request):
    marker = request.node.get_closest_marker("shared_macros")
    shared_macros = {} if marker is None else marker.args[0]
    marker = request.node.get_closest_marker("per_frame_macros")
    per_frame_macros = {} if marker is None else marker.args[0]
    data_set = new_data_set(shared_macros, per_frame_macros)
    return IODValidator(data_set, dicom_info, logging.WARNING)


FRAME_ANATOMY = {
    "FrameAnatomySequence": [
        {
            "FrameLaterality": "R",
            "AnatomicRegionSequence": [
                {
                    "CodeValue": "T-D3000",
                    "CodingSchemeDesignator": "SRT",
                    "CodeMeaning": "Chest",
                }
            ],
        }
    ]
}

FRAME_VOI_LUT = {
    "FrameVOILUTSequence": [{"WindowCenter": "7200", "WindowWidth": "12800"}]
}

FRAME_CONTENT = {"FrameContentSequence": [{"FrameReferenceDateTime": "200001011200"}]}

PIXEL_MEASURES = {"PixelMeasuresSequence": [{"PixelSpacing": "0.1\\0.1"}]}

TIMING_RELATED_PARAMS = {
    "MRTimingAndRelatedParametersSequence": [{"RFEchoTrainLength": None}]
}


class TestIODValidatorFuncGroups:
    """Tests IODValidator for functional groups."""

    @staticmethod
    def ensure_group_result(result: ValidationResult) -> TagErrors:
        assert result.module_errors is not None
        assert "Multi-frame Functional Groups" in result.module_errors
        return result.module_errors["Multi-frame Functional Groups"]

    def test_missing_func_groups(self, dicom_info: DicomInfo, caplog):
        caplog.set_level(logging.WARNING)
        data_set = new_data_set({}, {})
        del data_set[0x52009229]
        del data_set[0x52009230]
        validator = IODValidator(data_set, dicom_info, logging.WARNING)
        result = validator.validate()
        group_result = self.ensure_group_result(result)
        assert DicomTag(0x5200_9229) in group_result
        assert group_result[DicomTag(0x5200_9229)].code == ErrorCode.TagMissing

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Multi-frame Functional Groups":' in messages
        assert (
            "Tag (5200,9229) (Shared Functional Groups Sequence) is missing" in messages
        )

    def test_empty_func_groups(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()
        group_result = self.ensure_group_result(result)
        assert DicomTag(0x5200_9229) in group_result
        assert group_result[DicomTag(0x5200_9229)].code == ErrorCode.TagEmpty
        assert DicomTag(0x5200_9230) in group_result
        assert group_result[DicomTag(0x5200_9230)].code == ErrorCode.TagEmpty

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Multi-frame Functional Groups":' in messages
        assert (
            "Tag (5200,9229) (Shared Functional Groups Sequence) is empty" in messages
        )
        assert (
            "Tag (5200,9230) (Per-Frame Functional Groups Sequence) is empty"
            in messages
        )

    @pytest.mark.shared_macros([FRAME_ANATOMY])
    @pytest.mark.per_frame_macros([FRAME_VOI_LUT])
    def test_missing_sequences(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()
        # Irradiation Event Identification Sequence (mandatory, missing)
        assert has_tag_error(
            result,
            "Irradiation Event Identification",
            0x0018_9477,
            ErrorCode.TagMissing,
        )
        # Frame Content Sequence (mandatory, missing)
        assert has_tag_error(result, "Frame Content", 0x0020_9111, ErrorCode.TagMissing)
        # Frame Anatomy Sequence (present in shared groups)
        assert not has_tag_error(
            result, "Frame Anatomy", 0x0020_9071, ErrorCode.TagMissing
        )
        # Frame VOI LUT Sequence (present in per-frame groups)
        assert not has_tag_error(
            result, "Frame VOI LUT", 0x0028_9132, ErrorCode.TagMissing
        )
        # Referenced Image Sequence (not mandatory)
        assert not has_tag_error(
            result, "Referenced Image", 0x0008_1140, ErrorCode.TagMissing
        )

        # Subtraction Item ID, required because of the SOP Class UID value (in dataset root)
        assert has_tag_error(result, "Mask", 0x0028_9416, ErrorCode.TagMissing)
        # Mask Frame Numbers, required because Mask Operation (inside the sequence item) is AVG_SUB
        assert has_tag_error(result, "Mask", 0x0028_6110, ErrorCode.TagMissing)

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Irradiation Event Identification":' in messages
        assert "(5200,9229) (Shared Functional Groups Sequence):" in messages
        assert (
            "  Tag (0018,9477) (Irradiation Event Identification Sequence) is missing"
            in messages
        )

    @pytest.mark.shared_macros([FRAME_ANATOMY])
    @pytest.mark.per_frame_macros([FRAME_ANATOMY])
    def test_sequence_in_shared_and_per_frame(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()
        # Frame Anatomy Sequence (present in shared groups)
        assert has_tag_error(
            result,
            "Frame Anatomy",
            0x0020_9071,
            ErrorCode.TagNotAllowed,
        )

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Frame Anatomy":' in messages
        assert "(5200,9230) (Per-Frame Functional Groups Sequence):" in messages
        assert (
            "  Tag (0020,9071) (Frame Anatomy Sequence) is not allowed "
            "in both Shared and Per-Frame Groups" in messages
        )

    @pytest.mark.shared_macros([FRAME_CONTENT])
    @pytest.mark.per_frame_macros([FRAME_CONTENT])
    def test_macro_not_allowed_in_shared_group(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        result = validator.validate()
        # Frame Anatomy Sequence (present in shared groups)
        assert "Frame Content" in result.module_errors
        assert (
            DicomTag(0x0020_9111, [0x5200_9229])
            in result.module_errors["Frame Content"]
        )
        frame_anatomy_seq = result.module_errors["Frame Content"][
            DicomTag(0x0020_9111, [0x5200_9229])
        ]
        assert frame_anatomy_seq.code == ErrorCode.TagNotAllowed
        assert frame_anatomy_seq.scope == ErrorScope.SharedFuncGroup

        assert (
            DicomTag(0x0020_9111, [0x5200_9230])
            not in result.module_errors["Frame Content"]
        )

        assert not has_tag_error(
            result,
            "Multi-frame Functional Groups",
            0x0020_9111,
            ErrorCode.TagUnexpected,
        )

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Frame Content":' in messages
        assert "(5200,9229) (Shared Functional Groups Sequence):" in messages
        assert (
            "  Tag (0020,9111) (Frame Content Sequence) is not allowed in Shared Group"
            in messages
        )

    @pytest.mark.shared_macros([])
    @pytest.mark.per_frame_macros([PIXEL_MEASURES])
    def test_macro_not_allowed_in_per_frame_group(self, validator, caplog):
        caplog.set_level(logging.WARNING)
        validator._dataset.SOPClassUID = uid.VLWholeSlideMicroscopyImageStorage
        result = validator.validate()
        # Frame Anatomy Sequence (present in shared groups)
        assert has_tag_error(
            result, "Pixel Measures", 0x0028_9110, ErrorCode.TagNotAllowed
        )

        messages = [rec.message for rec in caplog.records]
        assert '\nModule "Pixel Measures":' in messages
        assert "(5200,9230) (Per-Frame Functional Groups Sequence):" in messages
        assert (
            "  Tag (0028,9110) (Pixel Measures Sequence) is not allowed in Per-Frame Group"
            in messages
        )

    @pytest.mark.shared_macros([TIMING_RELATED_PARAMS])
    @pytest.mark.per_frame_macros([FRAME_CONTENT])
    def test_empty_tag_in_shared_group(self, validator):
        # regression test for KeyError in this case
        validator._dataset.SOPClassUID = uid.MRSpectroscopyStorage
        validator._dataset.ImageType = "ORIGINAL\\PRIMARY"
        result = validator.validate()
        # RF Echo Train Length
        assert has_tag_error(
            result, "MR Timing and Related Parameters", 0x0018_9240, ErrorCode.TagEmpty
        )
