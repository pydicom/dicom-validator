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
