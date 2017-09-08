import unittest

from dcm_spec_tools.spec_reader.condition import Condition


class ConditionReadTest(unittest.TestCase):
    def check_condition(self, json_string, cond_type, index=0, op=None,
                        tag=None, values=None, nr_and_cond=0, nr_or_cond=0):
        condition = Condition()
        condition.read(json_string)
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
        self.assertEqual(values, condition.values)
        self.assertEqual(nr_and_cond, len(condition.and_conditions))
        self.assertEqual(nr_or_cond, len(condition.or_conditions))

    def test_read_type_only(self):
        self.check_condition('{ "type": "U" }', 'U')

    def test_eq(self):
        json_string = '''{
            "index": 0,
            "op": "=",
            "tag": "(3004,000A)",
            "type": "MN",
            "values": [
                "BEAM",
                "BEAM_SESSION",
                "CONTROL_POINT"
            ]
        }'''

        def test_condition():
            return self.check_condition(json_string, cond_type='MN', op='=',
                                        tag='(3004,000A)',
                                        values=['BEAM', 'BEAM_SESSION',
                                                'CONTROL_POINT'])

        condition = test_condition()
        json_string = condition.write()
        test_condition()

    def test_exists(self):
        json_string = '''{
            "index": 0,
            "op": "+",
            "tag": "(7FE0,0010)",
            "type": "MN"
        }'''

        def test_condition():
            return self.check_condition(json_string, cond_type='MN', op='+',
                                        tag='(7FE0,0010)')

        condition = test_condition()
        json_string = condition.write()
        test_condition()

    def test_and_condition(self):
        json_string = '''{
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
                    "values": [ "TEST" ]
                }
            ],
            "type": "MU"
        }'''

        def test_condition():
            condition = self.check_condition(
                json_string, cond_type='MU', nr_and_cond=3)
            self.check_sub_condition(
                condition.and_conditions[0], op='-', tag='(0040,E022)')
            self.check_sub_condition(
                condition.and_conditions[1], op='+', tag='(0040,E023)',
                index=1)
            self.check_sub_condition(
                condition.and_conditions[2], op='!=', tag='(0040,E025)',
                values=['TEST'])
            return condition

        condition = test_condition()
        json_string = condition.write()
        test_condition()

    def test_or_condition(self):
        json_string = '''{
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
        }'''

        def test_condition():
            condition = self.check_condition(
                json_string, cond_type='MU', nr_or_cond=2)
            self.check_sub_condition(
                condition.or_conditions[0], op='-', tag='(0040,4072)')
            self.check_sub_condition(
                condition.or_conditions[1], op='-', tag='(0040,4074)')
            return condition

        condition = test_condition()
        json_string = condition.write()
        test_condition()
