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
            "Required if present and consistent " "in the contributing SOP Instances. "
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


class TestSimpleConditionParser:
    def test_not_present(self, parser):
        result = parser.parse(
            "Required if VOI LUT Sequence (0028,3010) is not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0028,3010)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_operator_in_tag(self, parser):
        result = parser.parse(
            "Required if Fractional Channel Display Scale " "(003A,0247) is not present"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(003A,0247)"
        assert result.operator == ConditionOperator.Absent
        assert result.values == []

    def test_is_present(self, parser):
        result = parser.parse(
            "Required if Bounding Box Top Left Hand Corner " "(0070,0010) is present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0070,0010)"
        assert result.operator == ConditionOperator.Present
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

    def test_is_present_tag_name_with_digit(self, parser):
        result = parser.parse("Required if 3D Mating Point (0068,64C0) is present.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0068,64C0)"
        assert result.operator == ConditionOperator.Present
        assert result.values == []

    def test_not_sent(self, parser):
        result = parser.parse(
            "Required if Anatomic Region Modifier Sequence " "(0008,2220) is not sent. "
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

    def test_not_allowed_on_condition(self, parser):
        result = parser.parse(
            "Shall not be present if Rescale Intercept (0028,1052) is present."
        )
        assert result.type == ConditionType.NotAllowedOrUserDefined
        assert result.operator == ConditionOperator.Present
        assert result.tag == "(0028,1052)"


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
            "Required if Value Type (0040,A040) is " "COMPOSITE or IMAGE or WAVEFORM."
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
            "Required if Samples per Pixel " "(0028,0002) has a value greater than 1"
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
            "Required if Pixel Presentation " "(0008,9205) has a value of TRUE_COLOR."
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
            "Required if Image Type " "(0008,0008) Value 3 is: WHOLE BODY or STATIC."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.tag == "(0008,0008)"
        assert result.operator == ConditionOperator.EqualsValue
        assert result.index == 2
        assert result.values == ["WHOLE BODY", "STATIC"]

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
            "Required if Data Point Rows " "(0028,9001) has a value of more than 1."
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

    def test_present_with_value(self, parser):
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

    def test_present_with_value_of(self, parser):
        result = parser.parse(
            "Required if Partial View " "(0028,1350) is present with a value of YES."
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
        assert result.values == ["1581058"]

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

    def test_greater_than_zero(self, parser):
        result = parser.parse(
            "Required if Number of Beams (300A,0080) is greater than zero"
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.GreaterValue
        assert result.values == ["0"]

    def test_is_non_zero_length(self, parser):
        result = parser.parse("Required if Material ID (300A,00E1) is non-zero length.")
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.NotEqualsValue
        assert result.values == [""]

    def test_is_not_zero_length(self, parser):
        result = parser.parse(
            "Required if value Transfer Tube Number (300A,02A2) " "is not zero length."
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

    def test_third_value(self, parser):
        result = parser.parse(
            "Required if the third value of Image Type (0008,0008) is FLUENCE."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0008,0008)"
        assert result.values == ["FLUENCE"]
        assert result.index == 2

    def test_value_3(self, parser):
        result = parser.parse(
            "Required if Value 3 of Image Type (0008,0008) is SIMULATOR or PORTAL."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0008,0008)"
        assert result.values == ["SIMULATOR", "PORTAL"]
        assert result.index == 2


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

    def test_ispresent_with_value(self, parser):
        result = parser.parse(
            "Required if Patient Identity Removed (0012,0062) is present and "
            "has a value of YES and De-identification Method Code Sequence "
            "(0012,0064) is not present."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.and_conditions) == 2
        assert result.and_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.and_conditions[0].values[0] == "YES"
        assert result.and_conditions[1].operator == ConditionOperator.Absent

    def check_or_condition(self, result):
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].values[0] == "PALETTE COLOR"
        assert result.or_conditions[1].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[1].values == ["COLOR", "MIXED"]

    def test_or_condition_with_space(self, parser):
        result = parser.parse(
            '"Required if Photometric Interpretation '
            "(0028,0004) has a value of PALETTE COLOR "
            "or Pixel Presentation (0008,9205) equals COLOR or MIXED."
        )
        self.check_or_condition(result)

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


class TestComplicatedConditionParser:
    def disabled_test_data_points_check(self, parser):
        result = parser.parse(
            'Required if Graphic Data (0070,0022) is "closed", '
            "that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE, "
            "or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED "
            "and the first data point is the same as the last data point."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert len(result.or_conditions) == 2
        assert result.or_conditions[0].operator == ConditionOperator.EqualsValue
        assert result.or_conditions[0].tag == "(0070,0023)"
        assert result.or_conditions[0].values == ["CIRCLE", "ELLIPSE"]
        and_conditions = result.or_conditions[1].and_conditions
        assert and_conditions[0].operator == ConditionOperator.EqualsValue
        assert and_conditions[0].tag == "(0070,0023)"
        assert and_conditions[0].values == ["POLYLINE", "INTERPOLATED"]
        assert and_conditions[1].operator == ...  # some special operator
        assert and_conditions[1].tag == "(0070,0022)"

    def test_incomplete_and_condition(self, parser):
        """
        The last condition is not parseable and therefore ignored
        together with the condition that is ANDead with.
        To see the expected correct result, see the test
        `disabled_test_data_points_check` above.
        """
        result = parser.parse(
            'Required if Graphic Data (0070,0022) is "closed", '
            "that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE, "
            "or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED "
            "and the first data point is the same as the last data point."
        )
        assert result.type == ConditionType.MandatoryOrUserDefined
        assert result.operator == ConditionOperator.EqualsValue
        assert result.tag == "(0070,0023)"
        assert result.values == ["CIRCLE", "ELLIPSE"]
        assert result.or_conditions == result.and_conditions == []
        assert result.other_condition is None

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

    def test_empty_value_handled(self, parser):
        # regression test for an exception that happened due to a wrongly
        # read in condition, see #119
        result = parser.parse(
            "Required if segmented data is NOT used in an Image IOD "
            "or , or if the IOD is a Presentation State IOD."
        )
        assert result.type == ConditionType.UserDefined
