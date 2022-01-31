import json
import unittest

import os

from dicom_validator.spec_reader.condition import Condition
from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.tests.test_utils import json_fixture_path


class ConditionReadTest(unittest.TestCase):
    dict_info = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(json_fixture_path(),
                               EditionReader.dict_info_json)) as info_file:
            cls.dict_info = json.load(info_file)

    def check_condition(self, cond_dict, cond_type, index=0, op=None,
                        tag=None, values=None, nr_and_cond=0, nr_or_cond=0):
        condition = Condition.read_condition(cond_dict)
        self.assertEqual(cond_type, condition.type)
        self.check_sub_condition(condition, index, op, tag, values,
                                 nr_and_cond, nr_or_cond)
        return condition

    def check_sub_condition(self, condition, index=0, op=None,
                            tag=None, values=None, nr_and_cond=0,
                            nr_or_cond=0):
        self.assertEqual(index, condition.index)
        self.assertEqual(op, condition.operator)
        self.assertEqual(tag, condition.tag)
        self.assertEqual(values or [], condition.values)
        self.assertEqual(nr_and_cond, len(condition.and_conditions))
        self.assertEqual(nr_or_cond, len(condition.or_conditions))

    def test_read_type_only(self):
        self.check_condition({"type": "U"}, 'U')

    def test_eq(self):
        cond_dict = {
            "index": 0,
            "op": "=",
            "tag": "(3004,000A)",
            "type": "MN",
            "values": [
                "BEAM",
                "BEAM_SESSION",
                "CONTROL_POINT"
            ]
        }

        def test_condition():
            return self.check_condition(cond_dict, cond_type='MN', op='=',
                                        tag='(3004,000A)',
                                        values=['BEAM', 'BEAM_SESSION',
                                                'CONTROL_POINT'])

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('Dose Summation Type is equal to "BEAM", '
                         '"BEAM_SESSION" or "CONTROL_POINT"',
                         condition.to_string(self.dict_info))

    def test_greater(self):
        cond_dict = {
            "index": 0,
            "op": ">",
            "tag": "(0028,0008)",
            "type": "MN",
            "values": ["1"]
        }

        def test_condition():
            return self.check_condition(cond_dict, cond_type='MN', op='>',
                                        tag='(0028,0008)',
                                        values=['1'])

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('Number of Frames is greater than 1',
                         condition.to_string(self.dict_info))

    def test_less(self):
        cond_dict = {
            "index": 0,
            "op": "<",
            "tag": "(0028,0008)",
            "type": "MN",
            "values": ["20"]
        }

        def test_condition():
            return self.check_condition(cond_dict, cond_type='MN', op='<',
                                        tag='(0028,0008)',
                                        values=['20'])

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('Number of Frames is less than 20',
                         condition.to_string(self.dict_info))

    def test_points_to(self):
        cond_dict = {
            "index": 0,
            "op": "=>",
            "tag": "(0028,0009)",
            "type": "MN",
            "values": [
                "1577061"
            ]
        }

        def test_condition():
            return self.check_condition(cond_dict, cond_type='MN', op='=>',
                                        tag='(0028,0009)',
                                        values=['1577061'])

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('Frame Increment Pointer points to '
                         '(0018,1065) (Frame Time Vector)',
                         condition.to_string(self.dict_info))

    def test_exists(self):
        cond_dict = {
            "index": 0,
            "op": "+",
            "tag": "(7FE0,0010)",
            "type": "MN"
        }

        def test_condition():
            return self.check_condition(cond_dict, cond_type='MN', op='+',
                                        tag='(7FE0,0010)')

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('Pixel Data exists',
                         condition.to_string(self.dict_info))

    def test_and_condition(self):
        cond_dict = {
            "and": [
                {
                    "index": 0,
                    "op": "-",
                    "tag": "(0040,E022)"
                },
                {
                    "index": 1,
                    "op": "+",
                    "tag": "(0040,E023)"
                },
                {
                    "index": 0,
                    "op": "!=",
                    "tag": "(0040,E025)",
                    "values": ["TEST"]
                }
            ],
            "type": "MU"
        }

        def test_condition():
            cond = self.check_condition(
                cond_dict, cond_type='MU', nr_and_cond=3)
            self.check_sub_condition(
                cond.and_conditions[0], op='-', tag='(0040,E022)')
            self.check_sub_condition(
                cond.and_conditions[1], op='+', tag='(0040,E023)',
                index=1)
            self.check_sub_condition(
                cond.and_conditions[2], op='!=', tag='(0040,E025)',
                values=['TEST'])
            return cond

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('DICOM Media Retrieval Sequence is not present and '
                         'WADO Retrieval Sequence[1] exists and WADO-RS '
                         'Retrieval Sequence is not equal to "TEST"',
                         condition.to_string(self.dict_info))

    def test_or_condition(self):
        cond_dict = {
            "or": [
                {
                    "index": 0,
                    "op": "-",
                    "tag": "(0040,4072)"
                },
                {
                    "index": 0,
                    "op": "-",
                    "tag": "(0040,4074)"
                }
            ],
            "type": "MU"
        }

        def test_condition():
            cond = self.check_condition(
                cond_dict, cond_type='MU', nr_or_cond=2)
            self.check_sub_condition(
                cond.or_conditions[0], op='-', tag='(0040,4072)')
            self.check_sub_condition(
                cond.or_conditions[1], op='-', tag='(0040,4074)')
            return cond

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
        self.assertEqual('STOW-RS Storage Sequence is not present or '
                         'XDS Storage Sequence is not present',
                         condition.to_string(self.dict_info))

    def test_other_condition(self):
        cond_dict = {
            "index": 0,
            "op": "=",
            "other_cond": {
                "index": 0,
                "op": "+",
                "tag": "(0072,0704)",
                "type": "MN"
            },
            "tag": "(0072,0704)",
            "type": "MC",
            "values": [
                "PALETTE"
            ]
        }

        def test_condition():
            cond = self.check_condition(
                cond_dict, cond_type='MC', op='=',
                tag='(0072,0704)', values=['PALETTE'])
            self.check_sub_condition(
                cond.other_condition, op='+', tag='(0072,0704)')
            self.assertEqual('MN', cond.other_condition.type)
            return cond

        condition = test_condition()
        cond_dict = condition.dict()
        test_condition()
