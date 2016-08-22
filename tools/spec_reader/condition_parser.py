import re
from collections import OrderedDict


class ConditionParser(object):
    """Parses a condition string defining if a module or tag shall be present in the data set."""

    tag_expression = re.compile(r'([a-zA-Z \-]+)(\([\dA-Fa-f]{4},[\dA-Fa-f]{4}\))?( Value \d)?')

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
                return self._parse_tag_expression(condition)
        return {'type': 'U'}

    def _parse_tag_expression(self, condition):
        result = {'type': 'U'}
        if not condition or condition[0].islower():
            return result
        operators = OrderedDict([
            ('is greater than', '>'),
            ('is present and equals', '='),
            ('value is', '='),
            ('has a value of', '='),
            ('=', '='),
            ('equals other than', '!='),
            ('equals', '='),
            ('is present', '+'),
            ('is sent', '+'),
            ('is not present', '-'),
            ('is absent', '-'),
            ('is', '=')]
        )
        operator_text = None
        op_offset = None
        for op in operators:
            offset = condition.find(op)
            if offset > 0 and (op_offset is None or offset < op_offset):
                op_offset = offset
                operator_text = op
        if operator_text is None:
            return result
        tag, value_index = self._parse_tag(condition[:op_offset])
        if tag is not None:
            result['op'] = operators[operator_text]
            result['tag'] = tag
            result['index'] = value_index
            if operators[operator_text] in ('=', '!=', '>', '<'):
                result['values'] = self._parse_tag_values(condition[op_offset + len(operator_text):])
            result['type'] = 'MU' if 'may be present otherwise' in condition[op_offset:].lower() else 'MN'
        return result

    def _parse_tag(self, tag_string):
        match = self.tag_expression.match(tag_string.strip())
        if match:
            value_index = 0 if match.group(3) is None else int(match.group(3)[-1]) - 1
            if match.group(2) is not None:
                return match.group(2), value_index
            tag_name = match.group(1).strip()
            for tag_id, entry in self._dict_info.items():
                if entry['name'] == tag_name:
                    return tag_id, value_index
        return None, None

    @staticmethod
    def _parse_tag_values(value_string):
        end_index = value_string.find(';')
        if end_index > 0:
            value_string = value_string[:end_index]
        else:
            end_index = value_string.find('.')
            if end_index > 0:
                value_string = value_string[:end_index]
        values = value_string.split(', ')
        tag_values = []
        for value in values:
            value = value.strip()
            if ' or ' in value:
                tag_values.extend(value.split(' or '))
            elif value.startswith('or '):
                tag_values.append(value[3:])
            else:
                tag_values.append(value)
        return tag_values
