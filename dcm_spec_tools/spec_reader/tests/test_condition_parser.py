import json
import os
import unittest

from dcm_spec_tools.spec_reader.condition_parser import ConditionParser
from dcm_spec_tools.tests.test_utils import json_fixture_path


class ConditionParserTest(unittest.TestCase):
    """Tests ConditionParser by testing different kinds of condition strings as taken from DICOM standard."""
    dict_info = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(json_fixture_path(), 'dict_info.json')) as info_file:
            cls.dict_info = json.load(info_file)

    def setUp(self):
        super(ConditionParserTest, self).setUp()
        self.parser = ConditionParser(self.dict_info)


class InvalidConditionParserTest(ConditionParserTest):
    def test_ignore_invalid_condition(self):
        result = self.parser.parse('')
        self.assertNotIn('tag', result)
        self.assertEqual('U', result['type'])

    def test_ignore_uncheckable_tag_condition(self):
        result = self.parser.parse('Required if Numeric Value (0040,A30A) has insufficient '
                                   'precision to represent the value as a string.')
        self.assertEqual('U', result['type'])
        self.assertNotIn('tag', result)

    def test_ignore_condition_without_tag(self):
        result = self.parser.parse('Required if present and consistent in the contributing SOP Instances. ')
        self.assertEqual('U', result['type'])


class SimpleConditionParserTest(ConditionParserTest):
    def test_not_present(self):
        result = self.parser.parse('Required if VOI LUT Sequence (0028,3010) is not present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,3010)', result['tag'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_operator_in_tag(self):
        result = self.parser.parse('Required if Fractional Channel Display Scale (003A,0247) is not present')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(003A,0247)', result['tag'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_is_present(self):
        result = self.parser.parse('Required if Bounding Box Top Left Hand Corner (0070,0010) is present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0070,0010)', result['tag'])
        self.assertEqual('+', result['op'])
        self.assertNotIn('values', result)

    def test_is_present_with_value(self):
        result = self.parser.parse('Required if Responsible Person is present and has a value.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0010,2297)', result['tag'])
        self.assertEqual('++', result['op'])
        self.assertNotIn('values', result)

    def test_is_present_tag_name_with_digit(self):
        result = self.parser.parse('Required if 3D Mating Point (0068,64C0) is present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0068,64C0)', result['tag'])
        self.assertEqual('+', result['op'])
        self.assertNotIn('values', result)

    def test_not_sent(self):
        result = self.parser.parse('Required if Anatomic Region Modifier Sequence (0008,2220) is not sent. ')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,2220)', result['tag'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_shall_be_condition_with_absent_tag(self):
        result = self.parser.parse('Some Stuff. Shall be present if Clinical Trial Subject Reading ID '
                                   '(0012,0042) is absent. May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0012,0042)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)


class ValueConditionParserTest(ConditionParserTest):
    def test_equality_tag(self):
        result = self.parser.parse('C - Required if Modality (0008,0060) = IVUS')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0060)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['IVUS'], result['values'])

    def test_equality_tag_without_tag_id(self):
        result = self.parser.parse('C - Required if Modality = IVUS')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0060)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['IVUS'], result['values'])

    def test_multiple_values_and_index(self):
        result = self.parser.parse('C - Required if Image Type (0008,0008) Value 3 '
                                   'is GATED, GATED TOMO, or RECON GATED TOMO')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0008)', result['tag'])
        self.assertEqual(2, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['GATED', 'GATED TOMO', 'RECON GATED TOMO'], result['values'])

    def test_comma_before_value(self):
        result = self.parser.parse('Required if Series Type (0054,1000), Value 2 is REPROJECTION.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0054,1000)', result['tag'])
        self.assertEqual(1, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['REPROJECTION'], result['values'])

    def test_may_be_present_otherwise(self):
        result = self.parser.parse('C - Required if Image Type (0008,0008) Value 1 equals ORIGINAL.'
                                   ' May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0008)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['ORIGINAL'], result['values'])

    def test_greater_operator(self):
        result = self.parser.parse('C - Required if Number of Frames is greater than 1')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,0008)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('>', result['op'])
        self.assertEqual(['1'], result['values'])

    def test_value_greater_than_operator(self):
        result = self.parser.parse('Required if Samples per Pixel (0028,0002) has a value greater than 1')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,0002)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('>', result['op'])
        self.assertEqual(['1'], result['values'])

    def test_tag_ids_as_values(self):
        result = self.parser.parse('C - Required if Frame Increment Pointer (0028,0009) '
                                   'is Frame Time (0018,1063) or Frame Time Vector (0018,1065)')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,0009)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['Frame Time (0018,1063)', 'Frame Time Vector (0018,1065)'], result['values'])

    def test_has_a_value_of(self):
        result = self.parser.parse('Required if Pixel Presentation (0008,9205) has a value of TRUE_COLOR.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,9205)', result['tag'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['TRUE_COLOR'], result['values'])

    def test_at_the_image_level_equals(self):
        result = self.parser.parse('"Required if Pixel Presentation (0008,9205) at the image level '
                                   'equals COLOR or MIXED.')
        self.assertEqual('MN', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['COLOR', 'MIXED'], result['values'])

    def test_is_with_colon(self):
        result = self.parser.parse('Required if Image Type (0008,0008) Value 3 is: WHOLE BODY or STATIC.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0008)', result['tag'])
        self.assertEqual('=', result['op'])
        self.assertEqual(2, result['index'])
        self.assertEqual(['WHOLE BODY', 'STATIC'], result['values'])

    def test_remove_apostrophes(self):
        result = self.parser.parse('Required if Lossy Image Compression (0028,2110) is "01".')
        self.assertEqual('=', result['op'])
        self.assertEqual(['01'], result['values'])

    def test_remove_apostrophes_from_uids(self):
        result = self.parser.parse('Required if SOP Class UID (0008,0016) equals "1.2.840.10008.5.1.4.1.1.12.1.1" '
                                   'or "1.2.840.10008.5.1.4.1.1.12.2.1". May be present otherwise.')
        self.assertEqual('=', result['op'])
        self.assertEqual(['1.2.840.10008.5.1.4.1.1.12.1.1', '1.2.840.10008.5.1.4.1.1.12.2.1'], result['values'])

    def test_value_of(self):
        result = self.parser.parse('Required if the value of Context Group Extension Flag (0008,010B) is "Y".')
        self.assertEqual('MN', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['Y'], result['values'])

    def test_value_more_than(self):
        result = self.parser.parse('Required if Data Point Rows (0028,9001) has a value of more than 1.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,9001)', result['tag'])
        self.assertEqual('>', result['op'])
        self.assertEqual(['1'], result['values'])

    def test_is_not_with_uid(self):
        result = self.parser.parse('Required if SOP Class UID is not "1.2.840.10008.5.1.4.1.1.4.4" (Legacy Converted).')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,0016)', result['tag'])
        self.assertEqual('!=', result['op'])
        self.assertEqual(['1.2.840.10008.5.1.4.1.1.4.4'], result['values'])

    def test_present_with_value(self):
        result = self.parser.parse('Required if Selector Attribute VR (0072,0050) is present and the value is AS.')
        self.assertEqual('MN', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['AS'], result['values'])

    def test_other_than(self):
        result = self.parser.parse('Required if Decay Correction (0054,1102) is other than NONE.')
        self.assertEqual('MN', result['type'])
        self.assertEqual('!=', result['op'])
        self.assertEqual(['NONE'], result['values'])

    def test_not_equal_to(self):
        result = self.parser.parse('Required if Planes in Acquisition (0018,9410) is not equal to UNDEFINED.')
        self.assertEqual('MN', result['type'])
        self.assertEqual('!=', result['op'])
        self.assertEqual(['UNDEFINED'], result['values'])

    def test_present_with_value_of(self):
        result = self.parser.parse('Required if Partial View (0028,1350) is present with a value of YES.')
        self.assertEqual('MN', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['YES'], result['values'])

    def test_points_to_tag(self):
        result = self.parser.parse('Required if Frame Increment Pointer (0028,0009) points to '
                                   'Frame Label Vector (0018,2002).')
        self.assertEqual('MN', result['type'])
        self.assertEqual('=>', result['op'])
        self.assertEqual(['1581058'], result['values'])


class NotMandatoryConditionParserTest(ConditionParserTest):
    def test_default(self):
        result = self.parser.parse('Required if Image Type (0008,0008) Value 1 is ORIGINAL. May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['ORIGINAL'], result['values'])

    def test_comma_instead_of_dot(self):
        result = self.parser.parse('Required if Absolute Channel Display Scale (003A,0248) is not present, '
                                   'may be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertEqual('-', result['op'])

    def test_missing_dot(self):
        result = self.parser.parse('Required if Image Type (0008,0008) Value 1 is ORIGINAL May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['ORIGINAL'], result['values'])


class CompositeConditionParserTest(ConditionParserTest):
    def test_and_condition(self):
        result = self.parser.parse('Required if Series Type (0054,1000), Value 1 is GATED and '
                                   'Beat Rejection Flag (0018,1080) is Y.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        result1 = result['and'][0]
        self.assertEqual('(0054,1000)', result1['tag'])
        self.assertEqual('=', result1['op'])
        self.assertEqual(['GATED'], result1['values'])
        result2 = result['and'][1]
        self.assertEqual('(0018,1080)', result2['tag'])
        self.assertEqual('=', result2['op'])
        self.assertEqual(['Y'], result2['values'])

    def test_ignore_unverifyable_and_condition(self):
        result = self.parser.parse('Required if Delivery Type (300A,00CE) is CONTINUATION and '
                                   'one or more channels of any Application Setup are omitted.')
        self.assertEqual('MN', result['type'])
        self.assertNotIn('and', result)
        self.assertEqual('=', result['op'])
        self.assertEqual(['CONTINUATION'], result['values'])

    def test_and_without_value(self):
        result = self.parser.parse('Required if Recorded Channel Sequence (3008,0130) is sent and '
                                   'Brachy Treatment Type (300A,0202) is not MANUAL or PDR.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        result1 = result['and'][0]
        self.assertEqual('(3008,0130)', result1['tag'])
        self.assertEqual('+', result1['op'])
        result2 = result['and'][1]
        self.assertEqual('(300A,0202)', result2['tag'])
        self.assertEqual('!=', result2['op'])
        self.assertEqual(['MANUAL', 'PDR'], result2['values'])

    def test_and_with_multiple_values(self):
        result = self.parser.parse('Required if Image Type (0008,0008) Value 1 is ORIGINAL or MIXED '
                                   'and Respiratory Motion Compensation Technique (0018,9170) equals other than NONE.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertEqual('=', result['and'][0]['op'])
        self.assertEqual(['ORIGINAL', 'MIXED'], result['and'][0]['values'])
        self.assertEqual('!=', result['and'][1]['op'])
        self.assertEqual(['NONE'], result['and'][1]['values'])

    def test_either_or_tag_presence(self):
        result = self.parser.parse("Required if either Patient's Birth Date in Alternative Calendar (0010,0033) "
                                   "or Patient's Alternative Death Date in Calendar (0010,0034) is present.")
        self.assertEqual('MN', result['type'])
        self.assertIn('or', result)
        result1 = result['or'][0]
        self.assertEqual('(0010,0033)', result1['tag'])
        self.assertEqual('+', result1['op'])
        result2 = result['or'][1]
        self.assertEqual('(0010,0034)', result2['tag'])
        self.assertEqual('+', result2['op'])

    def test_multiple_tag_absence(self):
        result = self.parser.parse('Required if DICOM Media Retrieval Sequence (0040,E022), '
                                   'WADO Retrieval Sequence (0040,E023), WADO-RS Retrieval Sequence (0040,E025)'
                                   ' and XDS Retrieval Sequence (0040,E024) are not present. May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertIn('and', result)
        self.assertEqual(4, len(result['and']))
        for result_part in result['and']:
            self.assertEqual('-', result_part['op'])

    def test_multiple_tag_absence_with_comma(self):
        result = self.parser.parse('Required if DICOM Retrieval Sequence (0040,E021), '
                                   'WADO Retrieval Sequence (0040,E023), '
                                   'and WADO-RS Retrieval Sequence (0040,E025) '
                                   'and XDS Retrieval Sequence (0040,E024) are not present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(4, len(result['and']))
        for result_part in result['and']:
            self.assertEqual('-', result_part['op'])

    def test_multiple_tag_presence(self):
        result = self.parser.parse('Required if Selector Attribute (0072,0026) and '
                                   'Filter-by Operator (0072,0406) are present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        for result_part in result['and']:
            self.assertEqual('+', result_part['op'])

    def test_mixed_and_or_tag_presence(self):
        result = self.parser.parse('Required if Selector Attribute (0072,0026) or Filter-by Category (0072,0402), '
                                   'and Filter-by Operator (0072,0406) are present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertIn('or', result['and'][0])
        self.assertEqual(2, len(result['and'][0]['or']))
        for result_part in result['and'][0]['or']:
            self.assertEqual('+', result_part['op'])
        self.assertEqual('+', result['and'][1]['op'])

    def test_multi_tag_in_second_condition(self):
        result = self.parser.parse('Required if Temporal Range Type (0040,A130) is present, '
                                   'and if Referenced Time Offsets (0040,A138) and '
                                   'Referenced DateTime (0040,A13A) are not present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertIn('and', result['and'][1])
        self.assertEqual(2, len(result['and'][1]['and']))
        for result_part in result['and'][1]['and']:
            self.assertEqual('-', result_part['op'])
        self.assertEqual('+', result['and'][0]['op'])

    def test_is_present_with_multiple_tags(self):
        result = self.parser.parse('Required if Bounding Box Top Left Hand Corner (0070,0010) '
                                   'or Bounding Box Bottom Right Hand Corner (0070,0011) is present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('or', result)
        self.assertEqual(2, len(result['or']))
        for result_part in result['or']:
            self.assertEqual('+', result_part['op'])

    def test_multiple_tags_with_value(self):
        result = self.parser.parse('Required if the value of Image Box Layout Type (0072,0304) is TILED, '
                                   'and the value of Image Box Tile Horizontal Dimension (0072,0306) or '
                                   'Image Box Tile Vertical Dimension (0072,0308) is greater than 1.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertIn('or', result['and'][1])
        self.assertEqual(2, len(result['and'][1]['or']))
        for result_part in result['and'][1]['or']:
            self.assertEqual('>', result_part['op'])
            self.assertIn('values', result_part)
            self.assertEqual('1', result_part['values'][0])

    def test_ispresent_with_value(self):
        result = self.parser.parse('Required if Patient Identity Removed (0012,0062) is present and '
                                   'has a value of YES and '
                                   'De-identification Method Code Sequence (0012,0064) is not present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertEqual('=', result['and'][0]['op'])
        self.assertEqual('YES', result['and'][0]['values'][0])
        self.assertEqual('-', result['and'][1]['op'])

    def test_or_condition_with_space(self):
        result = self.parser.parse('"Required if Photometric Interpretation (0028,0004) has a value of PALETTE COLOR '
                                   'or Pixel Presentation (0008,9205) equals COLOR or MIXED.')
        self.assertEqual('MN', result['type'])
        self.assertIn('or', result)
        self.assertEqual(2, len(result['or']))
        self.assertEqual('=', result['or'][0]['op'])
        self.assertEqual('PALETTE COLOR', result['or'][0]['values'][0])
        self.assertEqual('=', result['or'][1]['op'])
        self.assertEqual(['COLOR', 'MIXED'], result['or'][1]['values'])

    def test_or_condition_with_comma(self):
        result = self.parser.parse('"Required if Photometric Interpretation (0028,0004) has a value of PALETTE COLOR, '
                                   'or Pixel Presentation (0008,9205) equals COLOR or MIXED.')
        self.assertEqual('MN', result['type'])
        self.assertIn('or', result)
        self.assertEqual(2, len(result['or']))
        self.assertEqual('=', result['or'][0]['op'])
        self.assertEqual('PALETTE COLOR', result['or'][0]['values'][0])
        self.assertEqual('=', result['or'][1]['op'])
        self.assertEqual(['COLOR', 'MIXED'], result['or'][1]['values'])


class ComplicatedConditionParserTest(ConditionParserTest):
    def disabled_test_ispresent_with_value(self):
        result = self.parser.parse('Required if Graphic Data (0070,0022) is "closed", '
                                   'that is Graphic Type (0070,0023) is CIRCLE or ELLIPSE, '
                                   'or Graphic Type (0070,0023) is POLYLINE or INTERPOLATED '
                                   'and the first data point is the same as the last data point.')
        self.assertEqual('MN', result['type'])
        self.assertIn('or', result)
        self.assertEqual(3, len(result['or']))
        self.assertEqual('=', result['or'][0]['op'])
        self.assertEqual(['closed'], result['or'][0]['values'])
        self.assertEqual('=', result['or'][1]['op'])
        self.assertEqual(['CIRCLE', 'ELLIPSE'], result['or'][1]['values'])
        self.assertEqual('=', result['or'][2]['op'])
        self.assertEqual(['POLYLINE', 'INTERPOLATED'], result['or'][2]['values'])

    def test_other_condition(self):
        result = self.parser.parse('Required if 3D Point Coordinates (0068,6590) is not present and '
                                   'HPGL Document Sequence (0068,62C0) is present. '
                                   'May be present if 3D Point Coordinates (0068,6590) is present and '
                                   'HPGL Document Sequence (0068,62C0) is present.')
        self.assertEqual('MC', result['type'])
        self.assertIn('and', result)
        self.assertEqual(2, len(result['and']))
        self.assertEqual('-', result['and'][0]['op'])
        self.assertEqual('+', result['and'][1]['op'])
        self.assertIn('other_cond', result)
        other_cond = result['other_cond']
        self.assertIn('and', other_cond)
        self.assertEqual(2, len(other_cond['and']))
        self.assertEqual('+', other_cond['and'][0]['op'])
        self.assertEqual('(0068,6590)', other_cond['and'][0]['tag'])
        self.assertEqual('+', other_cond['and'][1]['op'])
        self.assertEqual('(0068,62C0)', other_cond['and'][1]['tag'])
