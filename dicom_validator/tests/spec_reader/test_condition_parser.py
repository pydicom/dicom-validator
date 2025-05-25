import pytest

from dicom_validator.spec_reader.condition import ConditionType, ConditionOperator
from dicom_validator.spec_reader.condition_parser import ConditionParser


@pytest.fixture
def parser(dict_info):
    yield ConditionParser(dict_info)


class TestInvalidConditionParser:
    def test_ignore_invalid_condition(self, parser):
        result = parser.parse("")
        assert result.tag is None
        assert result.type == ConditionType.UserDefined

    def test_ignore_uncheckable_tag_condition(self, parser):
        result = parser.parse(
            "Required if Numeric Value (0040,A30A) has insufficient "
            "precision to represent the value as a string."
        )
        assert result.type == ConditionType.UserDefined
        assert result.tag is None

    def test_ignore_condition_without_tag(self, parser):
        result = parser.parse(
            "Required if present and consistent in the contributing SOP Instances. "
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_condition_without_value(self, parser):
        # regression test for #15
        result = parser.parse(
            "required if Selector Attribute (0072,0026) is nested in "
            "one or more Sequences or is absent."
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_condition_with_tag_and_unparsable_text(self, parser):
        result = parser.parse(
            "Required if Pixel Intensity Relationship (0028,1040) is not LOG for "
            "frames included in this Item of the Mask Subtraction Sequence (0028,6100)"
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_functional_group_specific_condition(self, parser):
        result = parser.parse(
            "Required if Acquisition Contrast (0008,9209) in any MR Image Frame Type "
            "Functional Group in the SOP Instance equals DIFFUSION and "
            "Image Type (0008,0008) Value 1 is ORIGINAL or MIXED. "
            "May be present otherwise."
        )
        assert result.type == ConditionType.UserDefined

    def test_unparsable_part_invalidates_and_condition1(self, parser):
        result = parser.parse(
            "Required if the image is reconstructed from a system with multiple X-Ray 7"
            "sources and Multi-energy CT Acquisition (0018,9361) is NO or is absent.",
        )
        assert result.type == ConditionType.UserDefined

    def test_unparsable_part_invalidates_and_condition2(self, parser):
        result = parser.parse(
            "Required if Acquisition Contrast (0008,9209) in any MR Image Frame Type "
            "Functional Group in the SOP Instance equals DIFFUSION and "
            "Image Type (0008,0008) Value 1 is ORIGINAL or MIXED. "
            "May be present otherwise."
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_invalid_value(self, parser):
        result = parser.parse(
            "Required if Pseudo-Color Type (0072,0704) "
            "is a reference to a standard palette."
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_unparsable_and_condition_part(self, parser):
        result = parser.parse(
            "Required if Selector Attribute VR (0072,0050) is present and "
            "the value is SQ, and Selector Attribute (0072,0026) is a Code Sequence.",
        )
        assert result.type == ConditionType.UserDefined


class TestSimpleConditionParser:
    def test_not_present(self, parser):
        result = parser.parse(
            "Required if VOI LUT Sequence (0028,3010) is not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,3010)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_not_present_with_mas_as_last_tag_part(self, parser):
        result = parser.parse(
            "Required if Exposure in mAs (0018,9332) is not present. "
            "May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0018,9332)"
        assert result.operator == ConditionOperator.Absent

    def test_operator_in_tag(self, parser):
        result = parser.parse(
            "Required if Fractional Channel Display Scale (003A,0247) is not present"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(003A,0247)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_is_present(self, parser):
        result = parser.parse(
            "Required if Bounding Box Top Left Hand Corner (0070,0010) is present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0070,0010)"
        assert result.operator == ConditionOperator.Present
        assert result.values == []

    def test_is_present_in_sequence_item(self, parser):
        result = parser.parse(
            "Required if Encapsulated Document (0042,0011) is present in this Sequence Item."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0042,0011)"
        assert result.operator == ConditionOperator.Present

    def test_is_present_with_a_value(self, parser):
        result = parser.parse(
            "Required if Image Box Small Scroll Type (0072,0312) is present with a value."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0072,0312)"
        assert result.operator == ConditionOperator.NotEmpty
        assert result.values == []

    def test_is_present_with_value(self, parser):
        result = parser.parse(
            "Required if Responsible Person is present and has a value."
            "Shall not be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrNotAllowed
        assert result.tag == "(0010,2297)"
        assert result.operator == ConditionOperator.NotEmpty
        assert result.values == []

    def test_has_a_value(self, parser):
        result = parser.parse(
            "Required if Device Alternate Identifier (3010,001B) has a value."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(3010,001B)"
        assert result.operator == ConditionOperator.NotEmpty

    def test_is_present_tag_name_with_digit(self, parser):
        result = parser.parse("Required if 3D Mating Point (0068,64C0) is present.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0068,64C0)"
        assert result.operator == ConditionOperator.Present
        assert result.values == []

    def test_not_sent(self, parser):
        result = parser.parse(
            "Required if Anatomic Region Modifier Sequence (0008,2220) is not sent. "
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,2220)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_shall_be_condition_with_absent_tag(self, parser):
        result = parser.parse(
            "Some Stuff. Shall be present if Clinical Trial Subject Reading ID"
            " (0012,0042) is absent. May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0012,0042)"
        assert result.index == 0
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_required_only_if(self, parser):
        result = parser.parse(
            "Required only if Referenced Dose Reference Number (300C,0051) "
            "is not present. It shall not be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrNotAllowed
        assert result.tag == "(300C,0051)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_values_failed_parsing(self, parser):
        """Regression test for #20
        (if the value could not be parsed ignore the condition)"""
        result = parser.parse(
            "Required if Constraint Violation Significance (0082,0036) "
            "is only significant under certain conditions."
        )
        assert result.type == ConditionType.UserDefined

    def test_ignore_before_that_is(self, parser):
        result = parser.parse(
            'Required if Graphic Data (0070,0022) is "closed", '
            "that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["CIRCLE", "ELLIPSE"]

    def test_ignore_explanation(self, parser):
        result = parser.parse(
            "Required if Presentation Size Mode (0070,0100) is TRUE SIZE, "
            "in which case the values will correspond to the physical distance "
            "between the center of each pixel on the display device."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["TRUE SIZE"]

    def test_not_allowed_on_condition(self, parser):
        result = parser.parse(
            "Shall not be present if Rescale Intercept (0028,1052) is present."
        )
        assert result.type == ConditionType.NotAllowedOrUserDefined
        assert result.operator == ConditionOperator.Present
        assert result.tag == "(0028,1052)"

    def test_condition_ends_with_semicolon(self, parser):
        result = parser.parse(
            "Required if Dimension Organization Type (0020,9311) is not TILED_FULL; "
            "may be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.tag == "(0020,9311)"
        assert result.values == ["TILED_FULL"]


class TestValueConditionParser:
    def test_equality_tag(self, parser):
        result = parser.parse("C - Required if Modality (0008,0060) = IVUS")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0060)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["IVUS"]

    def test_equality_tag_without_tag_id(self, parser):
        result = parser.parse("C - Required if Modality = IVUS")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0060)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["IVUS"]

    def test_multiple_values_and_index(self, parser):
        result = parser.parse(
            "C - Required if Image Type (0008,0008) Value 3 "
            "is GATED, GATED TOMO, or RECON GATED TOMO."
            "Shall not be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrNotAllowed
        assert result.tag == "(0008,0008)"
        assert result.index == 2
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["GATED", "GATED TOMO", "RECON GATED TOMO"]

    def test_multiple_values_with_or(self, parser):
        result = parser.parse(
            "Required if Value Type (0040,A040) is COMPOSITE or IMAGE or WAVEFORM."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0040,A040)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["COMPOSITE", "IMAGE", "WAVEFORM"]

    def test_comma_before_value(self, parser):
        result = parser.parse(
            "Required if Series Type (0054,1000), Value 2 is REPROJECTION."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0054,1000)"
        assert result.index == 1
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["REPROJECTION"]

    def test_may_be_present_otherwise(self, parser):
        result = parser.parse(
            "C - Required if Image Type (0008,0008) Value 1 equals ORIGINAL."
            " May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0008)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["ORIGINAL"]

    def test_greater_operator(self, parser):
        result = parser.parse("C - Required if Number of Frames is greater than 1")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,0008)"
        assert result.index == 0
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["1"]

    def test_value_greater_than_operator(self, parser):
        result = parser.parse(
            "Required if Samples per Pixel (0028,0002) has a value greater than 1"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,0002)"
        assert result.index == 0
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["1"]

    def test_tag_ids_as_values(self, parser):
        result = parser.parse(
            "C - Required if Frame Increment Pointer (0028,0009) "
            "is Frame Time (0018,1063) or Frame Time Vector (0018,1065)"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,0009)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == [
            1577059,
            1577061,
        ]

    def test_random_text_with_tag_ids_is_ignored(self, parser):
        result = parser.parse(
            "C - Required if Frame Increment Pointer (0028,0009) "
            "is Frame Time (0018,1063) or Frame Time Vector (0018,1065)"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,0009)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == [
            1577059,
            1577061,
        ]

    def test_has_a_value_of(self, parser):
        result = parser.parse(
            "Required if Pixel Presentation (0008,9205) has a value of TRUE_COLOR."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,9205)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["TRUE_COLOR"]

    def test_at_the_image_level_equals(self, parser):
        result = parser.parse(
            '"Required if Pixel Presentation (0008,9205) at the image level '
            "equals COLOR or MIXED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["COLOR", "MIXED"]

    def test_is_with_colon(self, parser):
        result = parser.parse(
            "Required if Image Type (0008,0008) Value 3 is: WHOLE BODY or STATIC."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0008)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.index == 2
        assert result.values == ["WHOLE BODY", "STATIC"]

    def test_is_with_one_letter_values(self, parser):
        result = parser.parse(
            "Required if Measurement Laterality (0024,0113) is L or B.",
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0024,0113)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["L", "B"]

    def test_is(self, parser):
        result = parser.parse(
            "Required if Blending LUT 1 Transfer Function (0028,1405) is CONSTANT.",
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,1405)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["CONSTANT"]

    def test_value_type_is(self, parser):
        result = parser.parse("Required if Value Type (0040,A040) is DATETIME")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0040,A040)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["DATETIME"]

    def test_value_is(self, parser):
        result = parser.parse("Required if Observer Type value is DEV")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0040,A084)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["DEV"]

    @staticmethod
    def check_the_value_of_is(result):
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,010B)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["Y"]

    def test_the_value_of_is(self, parser):
        result = parser.parse(
            'Required if the value of Context Group Extension Flag (0008,010B) is "Y".'
        )
        self.check_the_value_of_is(result)

    def test_the_uppercase_value_of_is(self, parser):
        result = parser.parse(
            'Required if the Value of Context Group Extension Flag (0008,010B) is "Y".'
        )
        self.check_the_value_of_is(result)

    def test_present_with_value_other_than(self, parser):
        result = parser.parse(
            "Required if Data Path Assignment (0028,1402) is present with a value "
            "other than PRIMARY_PVALUES."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,1402)"
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["PRIMARY_PVALUES"]

    def test_remove_apostrophes(self, parser):
        result = parser.parse(
            'Required if Lossy Image Compression (0028,2110) is "01".'
        )
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["01"]

    def test_remove_apostrophes_from_uids(self, parser):
        result = parser.parse(
            "Required if SOP Class UID (0008,0016) "
            'equals "1.2.840.10008.5.1.4.1.1.12.1.1" '
            'or "1.2.840.10008.5.1.4.1.1.12.2.1". May be present otherwise.'
        )
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == [
            "1.2.840.10008.5.1.4.1.1.12.1.1",
            "1.2.840.10008.5.1.4.1.1.12.2.1",
        ]

    def test_value_of(self, parser):
        result = parser.parse(
            "Required if the value of Context Group Extension Flag "
            '(0008,010B) is "Y".'
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["Y"]

    def test_value_more_than(self, parser):
        result = parser.parse(
            "Required if Data Point Rows (0028,9001) has a value of more than 1."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,9001)"
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["1"]

    def test_is_not_with_uid(self, parser):
        result = parser.parse(
            "Required if SOP Class UID is not "
            '"1.2.840.10008.5.1.4.1.1.4.4" (Legacy Converted).'
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0016)"
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["1.2.840.10008.5.1.4.1.1.4.4"]

    def test_present_and_the_value_is(self, parser):
        result = parser.parse(
            "Required if Selector Attribute VR "
            "(0072,0050) is present and the value is AS."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["AS"]

    def test_value_is_not(self, parser):
        result = parser.parse("Required if Shadow Style (0070,0244) value is not OFF.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["OFF"]

    def test_other_than(self, parser):
        result = parser.parse(
            "Required if Decay Correction (0054,1102) is other than NONE."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["NONE"]

    def test_not_equal_to(self, parser):
        result = parser.parse(
            "Required if Planes in Acquisition "
            "(0018,9410) is not equal to UNDEFINED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["UNDEFINED"]

    def test_equal_to(self, parser):
        result = parser.parse(
            "Required if Blending Mode (0070,1B06) is equal to FOREGROUND."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["FOREGROUND"]

    def test_present_with_value(self, parser):
        result = parser.parse(
            "Required if Performed Protocol Type (0040,0261) "
            "is present with value STAGED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["STAGED"]

    def test_present_with_value_greater_than(self, parser):
        result = parser.parse(
            "Required if Number of Block Slab Items (300A,0440) is present "
            "and has a value greater than zero."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["0"]

    def test_present_with_value_of(self, parser):
        result = parser.parse(
            "Required if Partial View (0028,1350) is present with a value of YES."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["YES"]

    def test_points_to_tag(self, parser):
        result = parser.parse(
            "Required if Frame Increment Pointer (0028,0009) points to "
            "Frame Label Vector (0018,2002)."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsTag
        assert result.values == [1581058]

    def test_non_zero(self, parser):
        result = parser.parse("Required if Number of Blocks (300A,00F0) is non-zero.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == ["0"]

    def test_non_null(self, parser):
        result = parser.parse(
            "Required if value Transfer Tube Number (300A,02A2) is non-null."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(300A,02A2)"
        assert result.operator == ConditionOperator.NotEmpty
        assert result.values == []

    def test_zero_length(self, parser):
        result = parser.parse(
            "Required if Material ID (300A,00E1) is zero-length. "
            "May be present if Material ID (300A,00E1) is non-zero length."
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert result.tag == "(300A,00E1)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == [""]
        assert result.other_condition is not None

    def test_zero_length_with_explanation(self, parser):
        result = parser.parse(
            "Required if Material ID (300A,00E1) is zero-length, "
            "here comes an explanation. "
            "May be present if Material ID (300A,00E1) is non-zero length."
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert result.tag == "(300A,00E1)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == [""]
        assert result.other_condition is not None

    def test_greater_than_zero(self, parser):
        result = parser.parse(
            "Required if Number of Beams (300A,0080) is greater than zero"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["0"]

    def test_greater_ignore_explanation(self, parser):
        result = parser.parse(
            "Shall be present if Number of Frames is greater than 1, overriding (specializing) "
            "the Type 1 requirement on this Attribute in the"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["1"]

    def test_is_non_zero_length(self, parser):
        result = parser.parse("Required if Material ID (300A,00E1) is non-zero length.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEmpty
        assert result.values == []

    def test_is_not_zero_length(self, parser):
        result = parser.parse(
            "Required if value Transfer Tube Number (300A,02A2) is not zero length."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == [""]

    def test_equal_sign(self, parser):
        result = parser.parse("Required if Pixel Component Organization = Bit aligned.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0018,6044)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["Bit aligned"]

    def test_value_has_explanation(self, parser):
        result = parser.parse(
            "Required if Conversion Type (0008,0064) is DF (Digitized Film)."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0064)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["DF"]

    def test_values_have_explanation(self, parser):
        result = parser.parse(
            "Required if Conversion Type (0008,0064) is SD "
            "(Scanned Document) or SI (Scanned Image)."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0064)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["SD", "SI"]

    def test_is_with_colon_after_value(self, parser):
        result = parser.parse(
            "Required if the value of Reformatting Operation Type "
            "(0072,0510) is 3D_RENDERING:"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0072,0510)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["3D_RENDERING"]

    def test_is_set_to(self, parser):
        result = parser.parse(
            "Required if Ophthalmic Volumetric Properties Flag (0022,1622) "
            "is set to YES. May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0022,1622)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["YES"]

    def test_is_either(self, parser):
        result = parser.parse(
            "Required if the value of Ophthalmic Axial Length Measurements Type "
            "(0022,1010) is present and is either SEGMENTAL LENGTH or LENGTH SUMMATION."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0022,1010)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["SEGMENTAL LENGTH", "LENGTH SUMMATION"]

    def test_mandatory_no_shared_group(self, parser):
        result = parser.parse("M - May not be used as a Shared Functional Group.")
        assert result.type == ConditionType.MandatoryPerFrame

    def test_user_no_shared_group(self, parser):
        result = parser.parse("U - May not be used as a Shared Functional Group.")
        assert result.type == ConditionType.UserDefinedPerFrame

    def test_the_before_tag_name(self, parser):
        result = parser.parse(
            "Required if the Image Type (0008,0008) Value 1 equals DERIVED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0008)"
        assert result.index == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["DERIVED"]

    def test_value_of_before_tag_name(self, parser):
        result = parser.parse(
            "Required if value of Reformatting Operation Type (0072,0510) "
            "is SLAB or MPR."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0072,0510)"
        assert result.values == ["SLAB", "MPR"]

    def test_attribute_before_tag_name(self, parser):
        result = parser.parse(
            "Required if Attribute Corneal Topography Surface (0046,0201) "
            "is A (Anterior)."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0046,0201)"
        assert result.values == ["A"]

    def test_the_value_for_before_tag_name(self, parser):
        result = parser.parse(
            "Required if the value for Foveal Sensitivity Measured (0024,0086) is YES "
            "and Foveal Point Normative Data Flag (0024,0117) is YES."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.and_conditions
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].tag == "(0024,0086)"
        assert result.and_conditions[0].values == ["YES"]

    def test_condition_with_hyphen(self, parser):
        result = parser.parse(
            "Required if Image Type (0008,0008) Value 1 is ORIGINAL or MIXED and "
            "Geometry of k-Space Traversal (0018,9032) equals RECTILINEAR. Otherwise "
            "may be present if Image Type (0008,0008) Value 1 is DERIVED and Geometry "
            "of k-Space Traversal (0018,9032) equals RECTILINEAR."
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert result.and_conditions
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].values == ["ORIGINAL", "MIXED"]
        assert result.and_conditions[1].values == ["RECTILINEAR"]
        assert result.other_condition

    def test_incorrect_tag_name(self, parser):
        result = parser.parse(
            "Required if Annotation Generation Type (006A,0007) "
            "is AUTOMATIC or SEMIAUTOMATIC."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(006A,0007)"
        assert result.values == ["AUTOMATIC", "SEMIAUTOMATIC"]

    @staticmethod
    def check_third_value(result):
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0008,0008)"
        assert result.values == ["FLUENCE"]
        assert result.index == 2

    def test_third_value(self, parser):
        result = parser.parse(
            "Required if the third value of Image Type (0008,0008) is FLUENCE."
        )
        self.check_third_value(result)

    def test_third_value_uppercase(self, parser):
        result = parser.parse(
            "Required if The third Value of Image Type (0008,0008) is FLUENCE."
        )
        self.check_third_value(result)

    def test_value_3(self, parser):
        result = parser.parse(
            "Required if Value 3 of Image Type (0008,0008) is SIMULATOR or PORTAL."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0008,0008)"
        assert result.values == ["SIMULATOR", "PORTAL"]
        assert result.index == 2

    def test_is_not_and_not(self, parser):
        result = parser.parse(
            "Required if SOP Class UID (0008,0016) is not "
            '"1.2.840.10008.5.1.4.1.1.2.2" '
            "(Legacy Converted Enhanced CT Image Storage) "
            'and not "1.2.840.10008.5.1.4.1.1.4.4" '
            "(Legacy Converted Enhanced MR Image Storage) "
            'and not "1.2.840.10008.5.1.4.1.1.128.1" '
            "(Legacy Converted Enhanced PET Image Storage)."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 3
        result1 = result.and_conditions[0]
        assert result1.operator == ConditionOperator.NotEqualsValue
        assert result1.tag == "(0008,0016)"
        assert result1.values == ["1.2.840.10008.5.1.4.1.1.2.2"]
        result2 = result.and_conditions[1]
        assert result2.operator == ConditionOperator.NotEqualsValue
        assert result2.tag == "(0008,0016)"
        assert result2.values == ["1.2.840.10008.5.1.4.1.1.4.4"]
        result3 = result.and_conditions[2]
        assert result3.operator == ConditionOperator.NotEqualsValue
        assert result3.tag == "(0008,0016)"
        assert result3.values == ["1.2.840.10008.5.1.4.1.1.128.1"]


class TestNotMandatoryConditionParser:
    def test_default(self, parser):
        result = parser.parse(
            "Required if Image Type "
            "(0008,0008) Value 1 is ORIGINAL. May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["ORIGINAL"]

    def test_comma_instead_of_dot(self, parser):
        result = parser.parse(
            "Required if Absolute Channel Display Scale "
            "(003A,0248) is not present, "
            "may be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.Absent

    def test_missing_dot(self, parser):
        result = parser.parse(
            "Required if Image Type "
            "(0008,0008) Value 1 is ORIGINAL May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["ORIGINAL"]


class TestCompositeConditionParser:
    def test_and_condition(self, parser):
        result = parser.parse(
            "Required if Series Type (0054,1000), Value 1 is GATED and "
            "Beat Rejection Flag (0018,1080) is Y."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(0054,1000)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["GATED"]
        result2 = result.and_conditions[1]
        assert result2.tag == "(0018,1080)"
        assert result2.operator == ConditionOperator.EqualsValue
        assert result2.values == ["Y"]

    def test_and_condition_with_or_values(self, parser):
        result = parser.parse(
            "Required if Image Type (0008,0008) Value 1 is ORIGINAL or MIXED "
            "and SOP Class UID (0008,0016) is not "
            '"1.2.840.10008.5.1.4.1.1.4.4" (Legacy Converted MR Image Storage). '
            "May be present otherwise"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(0008,0008)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["ORIGINAL", "MIXED"]
        result2 = result.and_conditions[1]
        assert result2.tag == "(0008,0016)"
        assert result2.operator == ConditionOperator.NotEqualsValue
        assert result2.values == ["1.2.840.10008.5.1.4.1.1.4.4"]

    def test_and_condition_with_ignored_or_condition(self, parser):
        result = parser.parse(
            "Required if Acquisition Device Sequence (3002,0117) is present and"
            " Value 1 of Image Type (0008,0008) has the value ORIGINAL or "
            "the current Instance was derived from an Instance."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(3002,0117)"
        assert result1.operator == ConditionOperator.Present
        result2 = result.and_conditions[1]
        assert result2.tag == "(0008,0008)"
        assert result2.operator == ConditionOperator.EqualsValue
        assert result2.values == ["ORIGINAL"]

    def test_and_conditions_with_and_in_tag_name(self, parser):
        result = parser.parse(
            "Required if Dose Calibration Conditions Verified Flag (300C,0123) "
            "is present and equals YES and Radiation Device Configuration and "
            "Commissioning Key Sequence (300A,065A) is absent."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(300C,0123)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["YES"]
        result2 = result.and_conditions[1]
        assert result2.tag == "(300A,065A)"
        assert result2.operator == ConditionOperator.Absent

    def test_and_condition_with_other_and_condition(self, parser):
        result = parser.parse(
            "Required if Dose Calibration Conditions Verified Flag (300C,0123) "
            "is present and equals YES and "
            "Radiation Device Configuration and "
            "Commissioning Key Sequence (300A,065A) is absent."
            "May be present if Dose Calibration Conditions Verified Flag (300C,0123) "
            "is present and equals YES and "
            "Radiation Device Configuration and "
            "Commissioning Key Sequence (300A,065A) is present.",
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(300C,0123)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["YES"]
        result2 = result.and_conditions[1]
        assert result2.tag == "(300A,065A)"
        assert result2.operator == ConditionOperator.Absent
        other_condition = result.other_condition
        assert len(other_condition.and_conditions) == 2
        result1 = other_condition.and_conditions[0]
        assert result1.tag == "(300C,0123)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["YES"]
        result2 = other_condition.and_conditions[1]
        assert result2.tag == "(300A,065A)"
        assert result2.operator == ConditionOperator.Present

    def test_ignore_unverifyable_or_condition(self, parser):
        result = parser.parse(
            "Required if Delivery Type (300A,00CE) is CONTINUATION or "
            "one or more channels of any Application Setup are omitted."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 0
        assert result.operator == ConditionOperator.EqualsValue
        assert result.values == ["CONTINUATION"]

    def test_unverifyable_and_condition_invalidates_condition(self, parser):
        result = parser.parse(
            "Required if Delivery Type (300A,00CE) is CONTINUATION and "
            "one or more channels of any Application Setup are omitted."
        )
        assert result.type == ConditionType.UserDefined
        assert result.tag is None

    def test_and_without_value(self, parser):
        result = parser.parse(
            "Required if Recorded Channel Sequence (3008,0130) is sent and "
            "Brachy Treatment Type (300A,0202) is not MANUAL or PDR."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        result1 = result.and_conditions[0]
        assert result1.tag == "(3008,0130)"
        assert result1.operator == ConditionOperator.Present
        result2 = result.and_conditions[1]
        assert result2.tag == "(300A,0202)"
        assert result2.operator == ConditionOperator.NotEqualsValue
        assert result2.values == ["MANUAL", "PDR"]

    @staticmethod
    def check_combined_or_plus_and_with_of_this_frame(result):
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        result1 = result.or_conditions[0]
        assert result1.tag == "(0008,9007)"
        assert result1.operator == ConditionOperator.EqualsValue
        assert result1.values == ["ORIGINAL"]
        result2 = result.or_conditions[1]
        assert len(result2.and_conditions) == 2
        and_result1 = result2.and_conditions[0]
        assert and_result1.tag == "(0008,0008)"
        assert and_result1.operator == ConditionOperator.EqualsValue
        assert and_result1.values == ["ORIGINAL"]
        and_result2 = result2.and_conditions[1]
        assert and_result2.tag == "(0018,9361)"
        assert and_result2.operator == ConditionOperator.EqualsValue
        assert and_result2.values == ["YES"]

    def test_combined_or_plus_and_with_of_this_frame(self, parser):
        result = parser.parse(
            "Required if Frame Type (0008,9007) Value 1 of this frame is ORIGINAL, "
            "or if Image Type (0008,0008) Value 1 is ORIGINAL and "
            "Multi-energy CT Acquisition (0018,9361) is YES. "
            "May be present otherwise."
        )
        self.check_combined_or_plus_and_with_of_this_frame(result)

    def test_combined_or_plus_and_with_of_this_frame_uppercase(self, parser):
        result = parser.parse(
            "Required if Frame Type (0008,9007) Value 1 of this Frame is ORIGINAL, "
            "or if Image Type (0008,0008) Value 1 is ORIGINAL and "
            "Multi-energy CT Acquisition (0018,9361) is YES. "
            "May be present otherwise."
        )
        self.check_combined_or_plus_and_with_of_this_frame(result)

    def test_and_with_multiple_values(self, parser):
        result = parser.parse(
            "Required if Image Type (0008,0008) Value 1 is ORIGINAL or MIXED "
            "and Respiratory Motion Compensation Technique "
            "(0018,9170) equals other than NONE."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].values == ["ORIGINAL", "MIXED"]
        assert result.and_conditions[1].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[1].values == ["NONE"]

    def test_either_or_tag_presence(self, parser):
        result = parser.parse(
            "Required if either Patient's Birth Date in Alternative Calendar "
            "(0010,0033) or Patient's Alternative Death Date in Calendar "
            "(0010,0034) is present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        result1 = result.or_conditions[0]
        assert result1.tag == "(0010,0033)"
        assert result1.operator == ConditionOperator.Present
        result2 = result.or_conditions[1]
        assert result2.tag == "(0010,0034)"
        assert result2.operator == ConditionOperator.Present

    def test_multiple_tag_absence(self, parser):
        result = parser.parse(
            "Required if DICOM Media Retrieval Sequence (0040,E022), "
            "WADO Retrieval Sequence (0040,E023), WADO-RS Retrieval Sequence "
            "(0040,E025) and XDS Retrieval Sequence "
            "(0040,E024) are not present. May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 4
        for result_part in result.and_conditions:
            assert result_part.operator == ConditionOperator.Absent

    def test_multiple_tag_absence_with_comma(self, parser):
        result = parser.parse(
            "Required if DICOM Retrieval Sequence (0040,E021), "
            "WADO Retrieval Sequence (0040,E023), "
            "and WADO-RS Retrieval Sequence (0040,E025) "
            "and XDS Retrieval Sequence (0040,E024) are not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 4
        for result_part in result.and_conditions:
            assert result_part.operator == ConditionOperator.Absent

    def test_multiple_tag_presence(self, parser):
        result = parser.parse(
            "Required if Selector Attribute (0072,0026) and "
            "Filter-by Operator (0072,0406) are present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        for result_part in result.and_conditions:
            assert result_part.operator == ConditionOperator.Present

    def test_mixed_and_or_tag_presence(self, parser):
        result = parser.parse(
            "Required if Selector Attribute (0072,0026) or Filter-by Category "
            "(0072,0402), and Filter-by Operator (0072,0406) are present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert len(result.and_conditions[0].or_conditions) == 2
        for result_part in result.and_conditions[0].or_conditions:
            assert result_part.operator == ConditionOperator.Present
        assert result.and_conditions[1].operator == ConditionOperator.Present

    def test_mixed_or_value_and_tag_conditions(self, parser):
        result = parser.parse(
            "Required if the Image Type (0008,0008) Value 1 equals DERIVED or "
            "Value 1 is ORIGINAL and "
            "Presentation Intent Type equals FOR PRESENTATION. "
            "May be present otherwise.",
            debug=True,
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].tag == "(0008,0008)"
        assert result.or_conditions[0].index == 0
        assert result.or_conditions[0].values == ["DERIVED"]
        and_conditions = result.or_conditions[1].and_conditions
        assert len(and_conditions) == 2
        assert and_conditions[0].operator == ConditionOperator.EqualsValue
        assert and_conditions[0].tag == "(0008,0008)"
        assert and_conditions[0].index == 0
        assert and_conditions[0].values == ["ORIGINAL"]
        assert and_conditions[1].operator == ConditionOperator.EqualsValue
        assert and_conditions[1].tag == "(0008,0068)"
        assert and_conditions[1].values == ["FOR PRESENTATION"]

    def test_or_without_tag(self, parser):
        result = parser.parse(
            "Required if Compensator Surface Representation Flag (300A,02EC) "
            "is absent or has value NO."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].tag == "(300A,02EC)"
        assert result.or_conditions[0].operator == ConditionOperator.Absent
        assert result.or_conditions[1].tag == "(300A,02EC)"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["NO"]

    def test_comma_or_without_tag(self, parser):
        result = parser.parse(
            "Required if Enhanced RT Beam Limiting Device Definition Flag (3008,00A3) "
            "is absent, or is present and has the value NO."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].tag == "(3008,00A3)"
        assert result.or_conditions[0].operator == ConditionOperator.Absent
        assert result.or_conditions[1].tag == "(3008,00A3)"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["NO"]

    def test_and_condition_without_tag_with_value(self, parser):
        result = parser.parse(
            "Required if Image Type (0008,0008) Value 4 is TRANSMISSION and Value 3 "
            "is not any of TOMO, GATED TOMO, RECON TOMO or RECON GATED TOMO."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].tag == "(0008,0008)"
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].index == 3
        assert result.and_conditions[0].values == ["TRANSMISSION"]
        assert result.and_conditions[1].tag == "(0008,0008)"
        assert result.and_conditions[1].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[1].index == 2
        assert result.and_conditions[1].values == [
            "TOMO",
            "GATED TOMO",
            "RECON TOMO",
            "RECON GATED TOMO",
        ]

    def test_mixed_or_and_tag_presence(self, parser):
        result = parser.parse(
            "Required if Filter-by Category (0072,0402) is present, or if "
            "Selector Attribute (0072,0026) is present and "
            "Filter-by Attribute Presence (0072,0404) is not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.Present
        assert result.or_conditions[0].tag == "(0072,0402)"
        and_conditions = result.or_conditions[1].and_conditions
        assert len(and_conditions) == 2
        assert and_conditions[0].operator == ConditionOperator.Present
        assert and_conditions[0].tag == "(0072,0026)"
        assert and_conditions[1].operator == ConditionOperator.Absent
        assert and_conditions[1].tag == "(0072,0404)"

    def test_multi_tag_in_second_condition(self, parser):
        result = parser.parse(
            "Required if Temporal Range Type (0040,A130) is present, "
            "and if Referenced Time Offsets (0040,A138) and "
            "Referenced DateTime (0040,A13A) are not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert len(result.and_conditions[1].and_conditions) == 2
        for result_part in result.and_conditions[1].and_conditions:
            assert result_part.operator == ConditionOperator.Absent
        assert result.and_conditions[0].operator == ConditionOperator.Present

    def test_is_present_with_multiple_tags(self, parser):
        result = parser.parse(
            "Required if Bounding Box Top Left Hand Corner (0070,0010) "
            "or Bounding Box Bottom Right Hand Corner (0070,0011) is present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        for result_part in result.or_conditions:
            assert result_part.operator == ConditionOperator.Present

    def test_multiple_tags_with_value(self, parser):
        result = parser.parse(
            "Required if the value of Image Box Layout Type "
            "(0072,0304) is TILED, and the value of "
            "Image Box Tile Horizontal Dimension (0072,0306) or "
            "Image Box Tile Vertical Dimension (0072,0308) is greater than 1."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert len(result.and_conditions[1].or_conditions) == 2
        for result_part in result.and_conditions[1].or_conditions:
            assert result_part.operator == ConditionOperator.GreaterValue
            assert result_part.values
            assert result_part.values[0] == "1"

    @staticmethod
    def check_is_present_with_value(result):
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].values[0] == "YES"
        assert result.and_conditions[1].operator == ConditionOperator.Absent

    def test_is_present_with_value(self, parser):
        result = parser.parse(
            "Required if Patient Identity Removed (0012,0062) is present and "
            "has a value of YES and De-identification Method Code Sequence "
            "(0012,0064) is not present."
        )
        self.check_is_present_with_value(result)

    def test_is_present_with_uppercase_value(self, parser):
        result = parser.parse(
            "Required if Patient Identity Removed (0012,0062) is present and "
            "has a Value of YES and De-identification Method Code Sequence "
            "(0012,0064) is not present."
        )
        self.check_is_present_with_value(result)

    def test_or_condition_with_space(self, parser):
        result = parser.parse(
            '"Required if Photometric Interpretation '
            "(0028,0004) has a value of PALETTE COLOR "
            "or Pixel Presentation (0008,9205) equals COLOR or MIXED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].values[0] == "PALETTE COLOR"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["COLOR", "MIXED"]

    def test_or_condition_with_comma(self, parser):
        result = parser.parse(
            "Required if the Rescale Type is not HU (Hounsfield Units), or "
            "Multi-energy CT Acquisition (0018,9361) is YES."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.NotEqualsValue
        assert result.or_conditions[0].values[0] == "HU"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["YES"]

    def test_or_condition_with_or_values(self, parser):
        result = parser.parse(
            "Required if Graphic Type (0070,0023) is CIRCLE or ELLIPSE, "
            "or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].values == ["CIRCLE", "ELLIPSE"]
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["POLYLINE", "INTERPOLATED"]

    def test_or_condition_with_not_only(self, parser):
        result = parser.parse(
            "Required if Dimension Organization Type (0020,9311) is absent or "
            "not TILED_FULL."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].tag == "(0020,9311)"
        assert result.or_conditions[0].operator == ConditionOperator.Absent
        assert result.or_conditions[1].tag == "(0020,9311)"
        assert result.or_conditions[1].operator == ConditionOperator.NotEqualsValue
        assert result.or_conditions[1].values[0] == "TILED_FULL"


class TestComplicatedConditionParser:
    def test_incomplete_and_condition(self, parser):
        result = parser.parse(
            'Required if Graphic Data (0070,0022) is "closed", '
            "that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE, "
            "or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED "
            "and the first data point is the same as the last data point."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert not result.or_conditions
        assert not result.and_conditions
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0070,0023)"
        assert result.values == ["CIRCLE", "ELLIPSE"]

    def test_incomplete_or_condition(self, parser):
        """
        The last condition is not parseable and therefore ignored,
        as it is ORed with the other conditions.
        """
        result = parser.parse(
            'Required if Graphic Data (0070,0022) is "closed", '
            "that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE, "
            "or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED "
            "or the first data point is the same as the last data point."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].tag == "(0070,0023)"
        assert result.or_conditions[0].values == ["CIRCLE", "ELLIPSE"]
        assert result.or_conditions[1].tag == "(0070,0023)"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["POLYLINE", "INTERPOLATED"]
        assert result.other_condition is None

    def test_other_condition1(self, parser):
        result = parser.parse(
            "Required if 3D Point Coordinates (0068,6590) is not present and "
            "HPGL Document Sequence (0068,62C0) is present. "
            "May be present if 3D Point Coordinates "
            "(0068,6590) is present and "
            "HPGL Document Sequence (0068,62C0) is present."
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.Absent
        assert result.and_conditions[1].operator == ConditionOperator.Present
        other_cond = result.other_condition
        assert other_cond is not None
        assert len(other_cond.and_conditions) == 2
        assert other_cond.and_conditions[0].operator == ConditionOperator.Present
        assert other_cond.and_conditions[0].tag == "(0068,6590)"
        assert other_cond.and_conditions[1].operator == ConditionOperator.Present
        assert other_cond.and_conditions[1].tag == "(0068,62C0)"

    def test_other_condition2(self, parser):
        result = parser.parse(
            "Required if Pixel Padding Range Limit (0028,0121) is present and "
            "either Pixel Data (7FE0,0010) or Pixel Data Provider URL "
            "(0028,7FE0) is present. May be present otherwise only if "
            "Pixel Data (7FE0,0010) or Pixel Data Provider URL (0028,7FE0) "
            "is present."
        )
        assert result.type == ConditionType.MandatoryOrConditional
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.Present
        or_conditions = result.and_conditions[1].or_conditions
        assert len(or_conditions) == 2
        assert or_conditions[0].operator == ConditionOperator.Present
        assert or_conditions[0].tag == "(7FE0,0010)"
        assert or_conditions[1].operator == ConditionOperator.Present
        assert or_conditions[1].tag == "(0028,7FE0)"
        other_cond = result.other_condition
        assert other_cond is not None
        assert len(other_cond.or_conditions) == 2
        assert other_cond.or_conditions[0].operator == ConditionOperator.Present
        assert other_cond.or_conditions[0].tag == "(7FE0,0010)"
        assert other_cond.or_conditions[1].operator == ConditionOperator.Present
        assert other_cond.or_conditions[1].tag == "(0028,7FE0)"

    def test_possible_false_positive(self, parser):
        # the "nested" had been parsed as value
        # (could be handled correctly at some time in the future)
        result = parser.parse(
            "Selector Attribute (0072,0026) is nested in one "
            "or more Sequences or is absent"
        )
        assert result.type == ConditionType.UserDefined

    def test_sop_class_matching(self, parser):
        # this tests several problems: usage of SOP Class instead of
        # SOP Class UID, usage of UID name in value, and some unusual
        # expressions
        result = parser.parse(
            "Required for images where Patient Orientation Code Sequence "
            "(0054,0410) is not present and whose SOP Class is one of the "
            'following: CT ("1.2.840.10008.5.1.4.1.1.2") or MR '
            '("1.2.840.10008.5.1.4.1.1.4") or Enhanced CT '
            '("1.2.840.10008.5.1.4.1.1.2.1") or Enhanced MR Image '
            '("1.2.840.10008.5.1.4.1.1.4.1") or Enhanced Color MR Image '
            '("1.2.840.10008.5.1.4.1.1.4.3") or MR Spectroscopy '
            '("1.2.840.10008.5.1.4.1.1.4.2") Storage SOP Classes. '
            "May be present for other SOP Classes if Patient Orientation "
            "Code Sequence (0054,0410) is not present. "
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.Absent
        assert result.and_conditions[0].tag == "(0054,0410)"
        assert result.and_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[1].tag == "(0008,0016)"
        assert result.and_conditions[1].values == [
            "1.2.840.10008.5.1.4.1.1.2",
            "1.2.840.10008.5.1.4.1.1.4",
            "1.2.840.10008.5.1.4.1.1.2.1",
            "1.2.840.10008.5.1.4.1.1.4.1",
            "1.2.840.10008.5.1.4.1.1.4.3",
            "1.2.840.10008.5.1.4.1.1.4.2",
        ]
        other_cond = result.other_condition
        assert other_cond is None

    def test_sop_class_matching_with_and(self, parser):
        result = parser.parse(
            "Required if SOP Class UID (0008,0016) is not "
            '"1.2.840.10008.5.1.4.1.1.481.17" (RT Radiation Salvage Record Storage), '
            "and SOP Class UID (0008,0016) is not "
            '"1.2.840.10008.5.1.4.1.1.481.23" (Enhanced RT Image Storage), '
            "and SOP Class UID (0008,0016) is not "
            '"1.2.840.10008.5.1.4.1.1.481.24" (Enhanced Continuous RT Image Storage). '
            "May be present otherwise."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 3
        assert result.and_conditions[0].tag == "(0008,0016)"
        assert result.and_conditions[0].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[0].values == ["1.2.840.10008.5.1.4.1.1.481.17"]
        assert result.and_conditions[1].tag == "(0008,0016)"
        assert result.and_conditions[1].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[1].values == ["1.2.840.10008.5.1.4.1.1.481.23"]
        assert result.and_conditions[2].tag == "(0008,0016)"
        assert result.and_conditions[2].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[2].values == ["1.2.840.10008.5.1.4.1.1.481.24"]
        assert result.other_condition is None

    def test_in_module_ignored(self, parser):
        result = parser.parse(
            "Required if Pixel Presentation (0008,9205) "
            "in the Parametric Map image Module equals COLOR_RANGE and "
            "Palette Color Lookup Table UID (0028,1199) is not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].tag == "(0008,9205)"
        assert result.and_conditions[0].values == ["COLOR_RANGE"]
        assert result.and_conditions[1].operator == ConditionOperator.Absent
        assert result.and_conditions[1].tag == "(0028,1199)"
        assert result.other_condition is None

    def test_in_modules_ignored(self, parser):
        result = parser.parse(
            "Required if Graphic Layer (0070,0002) is present in the "
            "Volumetric Graphic Annotation Module or the Graphic Annotation Module"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0070,0002)"
        assert result.operator == ConditionOperator.Present

    def test_or_value_with_and_condition(self, parser):
        result = parser.parse(
            "Required if the Image Type (0008,0008) Value 1 equals DERIVED or "
            "Value 1 is ORIGINAL and Presentation Intent Type equals FOR PRESENTATION."
            " May be present otherwise."
        )
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].tag == "(0008,0008)"
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].values == ["DERIVED"]
        assert len(result.or_conditions[1].and_conditions) == 2
        cond1 = result.or_conditions[1].and_conditions[0]
        assert cond1.tag == "(0008,0008)"
        assert cond1.operator == ConditionOperator.EqualsValue
        assert cond1.values == ["ORIGINAL"]
        cond2 = result.or_conditions[1].and_conditions[1]
        assert cond2.tag == "(0008,0068)"
        assert cond2.operator == ConditionOperator.EqualsValue
        assert cond2.values == ["FOR PRESENTATION"]

    def test_empty_value_handled(self, parser):
        # regression test for an exception that happened due to a wrong
        # read in condition, see #119
        result = parser.parse(
            "Required if segmented data is NOT used in an Image IOD "
            "or , or if the IOD is a Presentation State IOD."
        )
        assert result.type == ConditionType.UserDefined

    def test_and_with_or_condition_without_tag(self, parser):
        result = parser.parse(
            "Required if Respiratory Motion Compensation Technique (0018,9170) "
            "equals other than NONE or REALTIME and "
            "Respiratory Trigger Type (0020,9250) is absent or "
            "has a value of TIME or BOTH."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].tag == "(0018,9170)"
        assert result.and_conditions[0].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[0].values == ["NONE", "REALTIME"]
        assert len(result.and_conditions[1].or_conditions) == 2
        cond1 = result.and_conditions[1].or_conditions[0]
        assert cond1.tag == "(0020,9250)"
        assert cond1.operator == ConditionOperator.Absent
        cond2 = result.and_conditions[1].or_conditions[1]
        assert cond2.tag == "(0020,9250)"
        assert cond2.operator == ConditionOperator.EqualsValue
        assert cond2.values == ["TIME", "BOTH"]

    def test_and_condition_with_list_and_incorrect_apostrophe(self, parser):
        result = parser.parse(
            "Required if Frame Type (0008,9007) Value 1 of this frame is ORIGINAL, "
            "and Dimension Organization Type (0020,9311) is not TILED_FULL, "
            "and the SOP Class UID (0008,0016) is not: "
            '"1.2.840.10008.5.1.4.1.1.2.2 (Legacy Converted Enhanced CT Image Storage)", '
            'or "1.2.840.10008.5.1.4.1.1.4.4" (Legacy Converted Enhanced MR Image Storage), '
            'or "1.2.840.10008.5.1.4.1.1.128.1" (Legacy Converted Enhanced PET Image Storage), '
            'or "1.2.840.10008.5.1.4.1.1.77.1.6" (VL Whole Slide Microscopy Image Storage).'
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 3
        assert result.and_conditions[0].tag == "(0008,9007)"
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].values == ["ORIGINAL"]
        assert result.and_conditions[1].tag == "(0020,9311)"
        assert result.and_conditions[1].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[1].values == ["TILED_FULL"]
        assert result.and_conditions[2].tag == "(0008,0016)"
        assert result.and_conditions[2].operator == ConditionOperator.NotEqualsValue
        assert result.and_conditions[2].values == [
            "1.2.840.10008.5.1.4.1.1.2.2",
            "1.2.840.10008.5.1.4.1.1.4.4",
            "1.2.840.10008.5.1.4.1.1.128.1",
            "1.2.840.10008.5.1.4.1.1.77.1.6",
        ]
