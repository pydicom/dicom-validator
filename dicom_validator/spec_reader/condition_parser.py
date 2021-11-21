import re
from collections import OrderedDict

from dicom_validator.spec_reader.condition import Condition


class ConditionParser(object):
    """Parses the description of type C modules and type 1C and 2C attributes.
    Creates a Condition object representing the condition(s) in the
    description provided that:
    - the condition is related to the value, absence or presence of one
        or more tags in the data set
    - the condition is related only to the data set itself
    All other conditions (including parsable conditions which reference
    other data sets) are ignored.
    The following operators are used for conditions:
    '+' - required if the given tag is present
    '++' - required if the given tag is present and has a value
    '-' - required if the given tag is absent
    '=' - required if the given tag has one of the given values
    '!=' - required if the given tag does not have one of the given values
    '>' - required if the given tag value is greater than the given value
    '<' - required if the given tag value is less than the given value
    '=>' - required if the given tag points to one of the given tags
    """

    tag_expression = re.compile(
        r'(the value of )?(?P<name>[a-zA-Z1-9 \'\-]+)'
        r'(?P<id>\([\dA-Fa-f]{4},[\dA-Fa-f]{4}\))?(,? Value (?P<index>\d))?$')

    operators = OrderedDict([
        (' is greater than ', '>'),
        (' is present and equals ', '='),
        (' is present with a value of ', '='),
        (' value is ', '='),
        (' has a value of more than ', '>'),
        (' has a value greater than ', '>'),
        (' has a value of ', '='),
        (' = ', '='),
        (' at the image level equals ', '='),
        (' equals other than ', '!='),
        (' equals ', '='),
        (' is other than ', '!='),
        (' is present and the value is ', '='),
        (' is present and has a value of ', '='),
        (' is present and has a value', '++'),
        (' is present', '+'),
        (' is sent', '+'),
        (' is not sent', '-'),
        (' is not present', '-'),
        (' is absent', '-'),
        (' is not equal to ', '!='),
        (' is not ', '!='),
        (' is ', '='),
        (' is: ', '='),
        (' are not present', '-'),
        (' are present', '+'),
        (' points to ', '=>')
    ])

    logical_ops = OrderedDict([
        ('and if', 'and'),
        ('and', 'and'),
        ('or if', 'or'),
        ('or', 'or')
    ])

    def __init__(self, dict_info):
        self._dict_info = dict_info

    def parse(self, condition):
        """Parse the given condition string and return a Condition object
         with the required attributes.
        """
        condition_prefixes = ('required if ', 'shall be present if ')
        for prefix in condition_prefixes:
            index = condition.lower().find(prefix)
            if index >= 0:
                condition = condition[len(prefix) + index:]
                condition = self._fix_condition(condition)
                return self._parse_tag_expressions(condition)
        return Condition(ctype='U')

    def _parse_tag_expression(self, condition):
        operator_text = None
        op_offset = None
        for operator in self.operators:
            offset = condition.find(operator)
            if offset > 0 and (op_offset is None or offset < op_offset):
                op_offset = offset
                operator_text = operator
        if operator_text is None:
            return Condition(ctype='U'), None
        operator = self.operators[operator_text]
        rest = condition[op_offset + len(operator_text):]
        if self.operators[operator_text] in ('=', '!=', '>', '<'):
            values, rest = self._parse_tag_values(rest)
        elif self.operators[operator_text] == '=>':
            value_string, rest = self.extract_value_string(rest)
            tag, _ = self._parse_tag(value_string)
            if tag is None:
                return Condition(ctype='U'), None
            values, rest = [str(self._tag_id(tag))], rest
        else:
            values, rest = None, rest.strip()
        result = self._parse_tags(condition[:op_offset], operator, values)
        if not result:
            return Condition(ctype='U'), None

        result.type = ('MU' if 'may be present otherwise'
                               in condition[op_offset:].lower() else 'MN')
        return result, rest

    def _get_other_condition(self, condition_string):
        other_cond_texts = [
            'may be present otherwise if ', 'may be present if '
        ]
        for condition_marker in other_cond_texts:
            index = condition_string.lower().find(condition_marker)
            if index >= 0:
                return self._parse_tag_expressions(
                    condition_string[index + len(condition_marker):])

    @staticmethod
    def _tag_id(tag_id_string):
        group, element = tag_id_string[1:-1].split(',')
        return (int(group, 16) << 16) + int(element, 16)

    def _parse_tag(self, tag_string):
        match = self.tag_expression.match(tag_string.strip())
        if match:
            value_index = (0 if match.group('index') is None
                           else int(match.group('index')) - 1)
            if match.group('id') is not None:
                return match.group('id'), value_index
            tag_name = match.group('name').strip()
            for tag_id, entry in self._dict_info.items():
                if entry['name'] == tag_name:
                    return tag_id, value_index
        return None, None

    def _parse_tag_values(self, value_string):
        value_string, rest = self.extract_value_string(value_string)
        values = value_string.split(', ')
        tag_values = []
        for value in values:
            if ' or ' in value:
                tag_values.extend(value.split(' or '))
            elif value.startswith('or '):
                tag_values.append(value[3:])
            else:
                tag_values.append(value)
        values = []
        for value in tag_values:
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].strip()
            values.append(value)
        return values, rest

    def extract_value_string(self, value_string):
        # remove stuff that breaks parser
        value_string = value_string.replace('(Legacy Converted)', '')
        start_index = 0
        rest = None
        while True:
            end_index = -1
            # todo: handle or
            for end_char in (';', '.', 'and ', ', or ', ' or '):
                char_index = value_string.find(end_char, start_index)
                if end_index < 0 or 0 <= char_index < end_index:
                    end_index = char_index
            apo_index = value_string.find('"', start_index)
            if end_index < 0:
                break
            if 0 <= apo_index < end_index:
                start_index = value_string.find('"', apo_index + 1) + 1
                continue
            if end_index > 0:
                if value_string.find(' or ') in [end_index, end_index + 1]:
                    # differentiate between several values and several
                    # conditions - check if the rest is a condition
                    or_cond = self._parse_tag_expressions(
                        value_string[end_index + 3:])
                    if or_cond.type == 'U':
                        start_index = end_index + 4
                        continue
                rest = value_string[end_index:].strip()
                value_string = value_string[:end_index]
                break
        return value_string, rest

    def _parse_tag_expressions(self, condition, nested=False):
        result, rest = self._parse_tag_expression(condition)
        if rest is not None:
            if rest.startswith(', '):
                rest = rest[2:]
            logical_op = None
            for operator in self.logical_ops:
                if rest.startswith(operator + ' '):
                    logical_op = self.logical_ops[operator]
                    condition = rest[len(operator) + 1:]
                    break
            if logical_op is not None:
                next_result = self._parse_tag_expressions(
                    condition, nested=True)
                if next_result.type != 'U':
                    next_result.type = None
                    new_result = Condition(ctype=result.type)
                    cond_list = self._condition_list(logical_op, new_result)
                    cond_list.append(result)
                    cond_list.append(next_result)
                    result.type = None
                    result = new_result
        if not nested and rest is not None:
            other_cond = self._get_other_condition(rest)
            if other_cond is not None and other_cond.type != 'U':
                result.type = 'MC'
                result.other_condition = other_cond
        return result

    def _parse_tags(self, condition, operator, values):
        # this handles only a few cases that are actually found
        if ', and ' in condition:
            return self._parse_tag_composition(
                condition, operator, values, 'and')
        if ', or ' in condition:
            return self._parse_tag_composition(
                condition, operator, values, 'or')
        if ' and ' in condition:
            return self._parse_multiple_tags(
                condition, operator, values, 'and')
        if ' or ' in condition:
            return self._parse_multiple_tags(
                condition, operator, values, 'or')
        return self._result_from_tag_string(condition, operator, values)

    def _parse_tag_composition(self, condition, operator, values, logical_op):
        split_string = ', {} '.format(logical_op)
        conditions = condition.split(split_string)
        result0 = self._parse_tags(conditions[0], operator, values)
        if not result0:
            result = self._parse_tags(condition.replace(
                split_string, split_string.replace(',', '')), operator, values)
        else:
            result = Condition()
            cond_list = self._condition_list(logical_op, result)
            cond_list.append(result0)
            cond_list.append(self._parse_tags(conditions[1], operator, values))
        return result

    def _parse_multiple_tags(self, condition, operator, values, logical_op):
        condition = condition.replace(' {} '.format(logical_op), ', ')
        result = Condition()
        cond_list = self._condition_list(logical_op, result)
        for tag_string in condition.split(', '):
            tag_result = self._result_from_tag_string(
                tag_string, operator, values)
            if tag_result:
                cond_list.append(tag_result)
        if len(cond_list) > 1:
            return result

    @staticmethod
    def _condition_list(logical_op, result):
        cond_list = (result.and_conditions if logical_op == 'and'
                     else result.or_conditions)
        return cond_list

    def _result_from_tag_string(self, tag_string, operator, values):
        tag, index = self._parse_tag(tag_string)
        if tag is not None:
            result = Condition(tag=tag, index=index, operator=operator)
            if values:
                result.values = values
            return result

    @staticmethod
    def _fix_condition(condition):
        index = condition.lower().find(' may be present otherwise')
        if index > 0:
            if condition[index - 1] == ',':
                condition = condition[:index - 1] + '.' + condition[index:]
            elif condition[index - 1] != '.':
                condition = condition[:index] + '.' + condition[index:]
        return condition
