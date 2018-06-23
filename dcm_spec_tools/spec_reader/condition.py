import json


class Condition(object):
    """ Represents a condition for the presence of a specific tag.

    Attributes:
        type: the type of the related object (tag or module) regarding its
            existence; possible values:
            'U': user defined, e.g. both existence or non-existence
                of the related object is considered legal
            'MN': the object is mandatory if the condition is fulfilled,
                otherwise not
            'MU': the object is mandatory if the condition is fulfilled,
                otherwise is user defined
        tag: the ID of the required tag in the form '(####,####)' or None
        index: the index of the tag for multi-valued tags or 0
        values: a list of values the tag shall have if the condition
            is fulfilled, or None
        operator: the comparison operation used ('=', '<', '>') for the
            value(s), or None

    """

    def __init__(self, ctype=None, operator=None, tag=None, index=0,
                 values=None):

        self.type = ctype
        self.operator = operator
        self.tag = tag
        self.index = index
        self.values = values
        self.and_conditions = []
        self.or_conditions = []
        self.other_condition = None

    def read(self, json_string):
        condition_dict = json.loads(json_string)
        self.read_condition(condition_dict, self)

    @classmethod
    def read_condition(cls, condition_dict, condition=None):
        condition = condition or Condition()
        condition.type = condition_dict.get('type')
        condition.operator = condition_dict.get('op')
        condition.tag = condition_dict.get('tag')
        condition.index = int(condition_dict.get('index', '0'))
        condition.values = condition_dict.get('values')
        and_list = condition_dict.get('and', [])
        condition.and_conditions = [
            cls.read_condition(cond) for cond in and_list]
        or_list = condition_dict.get('or', [])
        condition.or_conditions = [
            cls.read_condition(cond) for cond in or_list
        ]
        if 'other_cond' in condition_dict:
            condition.other_condition = cls.read_condition(
                condition_dict['other_cond'])
            condition.other_condition.type = condition_dict['other_cond'].get(
                'type')
        return condition

    def dict(self):
        result = {'type': self.type}
        result.update(self.write_condition(self))
        return result

    @classmethod
    def write_condition(cls, condition):
        result = {}
        if condition.operator is not None:
            result['op'] = condition.operator
        if condition.tag is not None:
            result['tag'] = condition.tag
            result['index'] = condition.index
        if condition.values:
            result['values'] = condition.values
        if condition.and_conditions:
            result['and'] = []
            for and_condition in condition.and_conditions:
                result['and'].append(cls.write_condition(and_condition))
        if condition.or_conditions:
            result['or'] = []
            for or_condition in condition.or_conditions:
                result['or'].append(cls.write_condition(or_condition))
        if condition.other_condition:
            result['other_cond'] = condition.other_condition.dict()
        return result

    def to_string(self, dict_info):
        """Return a condition readable as part of a sentence."""
        result = ''
        if self.and_conditions:
            return ' and '.join(
                cond.to_string(dict_info) for cond in self.and_conditions)
        if self.or_conditions:
            return ' or '.join(
                cond.to_string(dict_info) for cond in self.or_conditions)
        if self.tag is not None:
            if dict_info and self.tag in dict_info:
                result = dict_info[self.tag]['name']
            else:
                result = self.tag
            if self.index:
                result += '[{}]'.format(self.index)
        if self.operator == '+':
            result += ' exists'
        elif self.operator == '++':
            result += ' exists and has a value'
        elif self.operator == '=>':
            tag_value = int(self.values[0])
            tag_string = '({:04x},{:04x})'.format(
                tag_value // 0x10000, tag_value % 0x10000)
            result += ' points to ' + dict_info[tag_string]['name']
        elif self.operator == '-':
            result += ' is not present'
        elif self.operator == '=':
            result += ' is equal to '
            values = ['"' + value + '"' for value in self.values]
            if len(values) > 1:
                result += ', '.join(values[:-1]) + ' or '
            result += values[-1]
        elif self.operator == '!=':
            result += ' is not equal to '
            values = ['"' + value + '"' for value in self.values]
            if len(values) > 1:
                result += ', '.join(values[:-1]) + ' and '
            result += values[-1]
        elif self.operator == '<':
            result += ' is less than ' + self.values[0]
        elif self.operator == '>':
            result += ' is greater than ' + self.values[0]
        return result

