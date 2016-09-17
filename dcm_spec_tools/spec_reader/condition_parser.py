import re
from collections import OrderedDict


class ConditionParser(object):
    """Parses the description of type C modules and type 1C and 2C attributes.
       Creates a structured representation (dict) of the condition(s) in the description provided that:
       - the condition is related to the value, absence or presence of one or more tags in the data set
       - the condition is related only to the data set itself
       All other conditions (including parsable conditions which reference other data sets) are ignored.
    """

    tag_expression = re.compile(
        r'(the value of )?(?P<name>[a-zA-Z \-]+)(?P<id>\([\dA-Fa-f]{4},[\dA-Fa-f]{4}\))?(,? Value (?P<index>\d))?$')

    operators = OrderedDict([
        ('is greater than', '>'),
        ('is present and equals', '='),
        ('value is', '='),
        ('has a value of more than', '>'),
        ('has a value of', '='),
        ('=', '='),
        ('equals other than', '!='),
        ('equals', '='),
        ('is other than', '!='),
        ('is present and the value is', '='),
        ('is present', '+'),
        ('is sent', '+'),
        ('is not sent', '-'),
        ('is not present', '-'),
        ('is absent', '-'),
        ('is not', '!='),
        ('is', '='),
        ('are not present', '*-'),
        ('are present', '*+')
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
        """Parse the given condition string and return a dict with the required attributes.

        The return value is a dict with the entries:
        'type': the type of the related object (tag or module) regarding its existence; possible values:
            'U': user defined, e.g. both existence or non-existence of the related object is considered legal
            'MN': the object is mandatory if the condition is fulfilled, otherwise not
            'MU': the object is mandatory if the condition is fulfilled, otherwise is user defined
        'tag': (optional) the ID of the required tag in the form '(####,####)'
        'index': (optional) the index of the tag for multi-valued tags, if given
        'values': (optional) a list of values the tag shall have if the condition is fulfilled
        'op': (optional) the comparison operation used ('=', '<', '>') for the value(s)
        """
        condition_prefixes = ('required if ', 'shall be present if ')
        for prefix in condition_prefixes:
            index = condition.lower().find(prefix)
            if index >= 0:
                condition = condition[len(prefix) + index:]
                return self._parse_tag_expressions(condition)
        return {'type': 'U'}

    def _parse_tag_expression(self, condition):
        result = {'type': 'U'}
        rest = None
        if not condition:
            return result, rest
        operator_text = None
        op_offset = None
        for op in self.operators:
            offset = condition.find(op)
            if offset > 0 and (op_offset is None or offset < op_offset):
                op_offset = offset
                operator_text = op
        if operator_text is None:
            return result, rest
        operator = self.operators[operator_text]
        if operator.startswith('*'):
            result.update(self._parse_tags(condition[:op_offset], operator[1:]))
        else:
            tag, value_index = self._parse_tag(condition[:op_offset])
            if tag is None:
                return result, rest
            rest = condition[op_offset + len(operator_text):]
            result['op'] = operator
            result['tag'] = tag
            result['index'] = value_index
            if self.operators[operator_text] in ('=', '!=', '>', '<'):
                result['values'], rest = self._parse_tag_values(rest)
            else:
                rest = rest.strip()
        result['type'] = 'MU' if 'may be present otherwise' in condition[op_offset:].lower() else 'MN'
        return result, rest

    def _parse_tag(self, tag_string):
        match = self.tag_expression.match(tag_string.strip())
        if match:
            value_index = 0 if match.group('index') is None else int(match.group('index')) - 1
            if match.group('id') is not None:
                return match.group('id'), value_index
            tag_name = match.group('name').strip()
            for tag_id, entry in self._dict_info.items():
                if entry['name'] == tag_name:
                    return tag_id, value_index
        return None, None

    @staticmethod
    def _parse_tag_values(value_string):
        value_string, rest = ConditionParser.extract_value_string(value_string)
        values = value_string.split(', ')
        tag_values = []
        for value in values:
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].strip()
            if ' or ' in value:
                tag_values.extend(value.split(' or '))
            elif value.startswith('or '):
                tag_values.append(value[3:])
            else:
                tag_values.append(value)
        return tag_values, rest

    @staticmethod
    def extract_value_string(value_string):
        # remove stuff that breaks parser
        value_string = value_string.replace('(Legacy Converted)', '')
        start_index = 0
        rest = None
        while True:
            end_index = -1
            # todo: handle or
            for end_char in (';', '.', 'and '):
                char_index = value_string.find(end_char, start_index)
                if end_index < 0 or 0 <= char_index < end_index:
                    end_index = char_index
            apo_index = value_string.find('"', start_index)
            if end_index < 0:
                break
            if 0 < apo_index < end_index:
                start_index = value_string.find('"', apo_index + 1)
            else:
                if end_index > 0:
                    rest = value_string[end_index:].strip()
                    value_string = value_string[:end_index]
                break
        return value_string, rest

    def _parse_tag_expressions(self, condition):
        result, rest = self._parse_tag_expression(condition)
        if rest is not None:
            logical_op = None
            for op in self.logical_ops:
                if rest.startswith(op + ' '):
                    logical_op = self.logical_ops[op]
                    condition = rest[len(op) + 1:]
                    break
            if logical_op is not None:
                next_result = self._parse_tag_expressions(condition)
                if next_result['type'] != 'U':
                    del next_result['type']
                    new_result = {logical_op: [result, next_result], 'type': result['type']}
                    del result['type']
                    result = new_result
        return result

    def _parse_tags(self, condition, operator):
        # this handles only a few cases that are actually found
        result = {}
        if ', and ' in condition:
            and_conditions = condition.split(', and ')
            result['and'] = [
                self._parse_tags(and_conditions[0], operator),
                self._parse_tags(and_conditions[1], operator)
            ]
        elif ', or ' in condition:
            or_conditions = condition.split(', or ')
            result['or'] = [
                self._parse_tags(or_conditions[0], operator),
                self._parse_tags(or_conditions[1], operator)
            ]
        elif ' and ' in condition:
            condition = condition.replace(' and ', ', ')
            result['and'] = []
            for tag_string in condition.split(', '):
                tag, index = self._parse_tag(tag_string)
                if tag is not None:
                    result['and'].append({'tag': tag, 'index': index, 'op': operator})
        elif ' or ' in condition:
            condition = condition.replace(' or ', ', ')
            result['or'] = []
            for tag_string in condition.split(', '):
                tag, index = self._parse_tag(tag_string)
                if tag is not None:
                    result['or'].append({'tag': tag, 'index': index, 'op': operator})
        else:
            tag, index = self._parse_tag(condition)
            if tag is not None:
                result.update({'tag': tag, 'index': index, 'op': operator})
        return result
