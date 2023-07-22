from typing import Optional, List, Dict, Any

from dicom_validator.tag_tools import tag_name_from_id


class Condition:
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
            'MC': the object is mandatory if the condition is fulfilled,
                otherwise another condition will be checked
        tag: the ID of the required tag in the form '(####,####)' or None
        index: the index of the tag for multi-valued tags or 0
        values: a list of values the tag shall have if the condition
            is fulfilled, or None
        operator: the comparison operation used ('=', '<', '>') for the
            value(s), or None

    """

    def __init__(self, ctype: Optional[str] = None,
                 operator: Optional[str] = None,
                 tag: Optional[str] = None,
                 index: int = 0,
                 values: Optional[List[str]] = None) -> None:
        self.type = ctype
        self.operator = operator
        self.tag = tag
        self.index = index
        self.values = values or []
        self.and_conditions: List[Condition] = []
        self.or_conditions: List[Condition] = []
        self.other_condition: Optional[Condition] = None

    def __repr__(self):
        return f"Condition type={self.type} op='{self.operator}' tag={self.tag} values={self.values}"

    @classmethod
    def read_condition(cls, condition_dict: Dict,
                       condition: Optional["Condition"] = None) -> "Condition":
        condition = condition or Condition()
        condition.type = condition_dict.get('type')
        condition.operator = condition_dict.get('op')
        condition.tag = condition_dict.get('tag')
        condition.index = int(condition_dict.get('index', '0'))
        condition.values = condition_dict.get('values', [])
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

    def dict(self) -> Dict[str, Any]:
        result = {'type': self.type}
        result.update(self.write_condition(self))
        return result

    @classmethod
    def write_condition(cls, condition: "Condition") -> Dict[str, Any]:
        result: Dict[str, Any] = {}
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
        if condition.other_condition is not None:
            result['other_cond'] = condition.other_condition.dict()
        return result

    def to_string(self, dict_info: Dict) -> str:
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
        if self.operator is None:
            return result
        if self.operator == '+':
            result += ' exists'
        elif self.operator == '++':
            result += ' exists and has a value'
        elif self.operator == '-':
            result += ' is not present'
        elif self.operator == '=>':
            tag_value = int(self.values[0])
            result += ' points to ' + tag_name_from_id(tag_value, dict_info)
        elif not self.values:
            # if no values are found here, we have some unhandled condition
            # and ignore it for the time being
            return result
        elif self.operator == '=':
            values = ['"' + value + '"' for value in self.values]
            result += ' is equal to '
            if len(values) > 1:
                result += ', '.join(values[:-1]) + ' or '
            result += values[-1]
        elif self.operator == '!=':
            values = ['"' + value + '"' for value in self.values]
            result += ' is not equal to '
            if len(values) > 1:
                result += ', '.join(values[:-1]) + ' and '
            result += values[-1]
        elif self.operator == '<':
            result += ' is less than ' + self.values[0]
        elif self.operator == '>':
            result += ' is greater than ' + self.values[0]
        return result
