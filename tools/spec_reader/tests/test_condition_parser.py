import json
import os
import unittest

from spec_reader.condition_parser import ConditionParser


class ConditionParserTest(unittest.TestCase):
    dict_info = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'dict_info.json')) as f:
            cls.dict_info = json.load(f)

    def setUp(self):
        super(ConditionParserTest, self).setUp()
        self.parser = ConditionParser(self.dict_info)

    def test_invalid_condition(self):
        result = self.parser.parse('')
        self.assertNotIn('tag', result)
        self.assertEqual('U', result['type'])

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

    def test_tag_ids_as_values(self):
        result = self.parser.parse('C - Required if Frame Increment Pointer (0028,0009) '
                                   'is Frame Time (0018,1063) or Frame Time Vector (0018,1065)')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,0009)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['Frame Time (0018,1063)', 'Frame Time Vector (0018,1065)'], result['values'])

    def test_shall_be_condition_with_absent_tag(self):
        result = self.parser.parse('Some Stuff. Shall be present if Clinical Trial Subject Reading ID '
                                   '(0012,0042) is absent. May be present otherwise.')
        self.assertEqual('MU', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0012,0042)', result['tag'])
        self.assertEqual(0, result['index'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_has_a_value_of(self):
        result = self.parser.parse('Required if Pixel Presentation (0008,9205) has a value of TRUE_COLOR.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,9205)', result['tag'])
        self.assertEqual('=', result['op'])
        self.assertEqual(['TRUE_COLOR'], result['values'])

    def test_not_present(self):
        result = self.parser.parse('Required if VOI LUT Sequence (0028,3010) is not present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0028,3010)', result['tag'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_is_present(self):
        result = self.parser.parse('Required if Bounding Box Top Left Hand Corner (0070,0010) is present.')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0070,0010)', result['tag'])
        self.assertEqual('+', result['op'])
        self.assertNotIn('values', result)

    def test_not_sent(self):
        result = self.parser.parse('Required if Anatomic Region Modifier Sequence (0008,2220) is not sent. ')
        self.assertEqual('MN', result['type'])
        self.assertIn('tag', result)
        self.assertEqual('(0008,2220)', result['tag'])
        self.assertEqual('-', result['op'])
        self.assertNotIn('values', result)

    def test_remove_apostrophes(self):
        result = self.parser.parse('Required if Lossy Image Compression (0028,2110) is "01".')
        self.assertEqual('=', result['op'])
        self.assertEqual(['01'], result['values'])

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
