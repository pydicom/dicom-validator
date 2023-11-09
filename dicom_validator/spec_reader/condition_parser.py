import re
from collections import OrderedDict
from typing import Dict, Tuple, Optional, List

from dicom_validator.spec_reader.condition import (
    Condition,
    ConditionType,
    ConditionOperator,
    ValuesType,
)


class ConditionParser:
    """Parses the description of type C modules and type 1C and 2C attributes.
    Creates a Condition object representing the condition(s) in the
    description provided that:
    - the condition is related to the value, absence or presence of one
        or more tags in the data set
    - the condition is related only to the data set itself
    All other conditions (including parsable conditions which reference
    other data sets) are ignored.
    """

    tagname_expression = (
        r"(?P<name>[a-zA-Z1-9 \'\-]+)(?P<id>\([\dA-Fa-f]{4},[\dA-Fa-f]{4}\))?"
    )
    tag_expression1 = re.compile(
        rf"(the (?P<index>first|second|third) value of ){tagname_expression}"
    )
    tag_expression2 = re.compile(rf"Value (?P<index>\d) of {tagname_expression}")
    tag_expression3 = re.compile(
        r"((((the|a) )?value ((of|for) )?)|(the )|(either )|Attribute )?"
        rf"{tagname_expression}(,? Value (?P<index>\d))?$"
    )

    operators = OrderedDict(
        [
            (" is present and the value is ", ConditionOperator.EqualsValue),
            (" is present and has a value of ", ConditionOperator.EqualsValue),
            (" is greater than ", ConditionOperator.GreaterValue),
            (" is present and equals ", ConditionOperator.EqualsValue),
            (" is present with a value of ", ConditionOperator.EqualsValue),
            (" is set to ", ConditionOperator.EqualsValue),
            (" equals one of the following values: ", ConditionOperator.EqualsValue),
            (" has a value of more than ", ConditionOperator.GreaterValue),
            (" has a value greater than ", ConditionOperator.GreaterValue),
            (" has a value of ", ConditionOperator.EqualsValue),
            (" = ", ConditionOperator.EqualsValue),
            (" at the image level equals ", ConditionOperator.EqualsValue),
            (" equals other than ", ConditionOperator.NotEqualsValue),
            (" equals ", ConditionOperator.EqualsValue),
            (" is other than ", ConditionOperator.NotEqualsValue),
            (" is one of the following: ", ConditionOperator.EqualsValue),
            (" is present and has a value", ConditionOperator.NotEmpty),
            (" is present", ConditionOperator.Present),
            (" value is not ", ConditionOperator.NotEqualsValue),
            (" value is ", ConditionOperator.EqualsValue),
            (" is sent", ConditionOperator.Present),
            (" is not sent", ConditionOperator.Absent),
            (" is not present", ConditionOperator.Absent),
            (" is absent", ConditionOperator.Absent),
            (" is not equal to ", ConditionOperator.NotEqualsValue),
            (" is equal to ", ConditionOperator.EqualsValue),
            (" is not ", ConditionOperator.NotEqualsValue),
            (" is ", ConditionOperator.EqualsValue),
            (" is: ", ConditionOperator.EqualsValue),
            (" are not present", ConditionOperator.Absent),
            (" are present", ConditionOperator.Present),
            (" points to ", ConditionOperator.EqualsTag),
        ]
    )

    logical_ops = OrderedDict(
        [
            ("and if", "and"),
            ("and whose", "and"),
            ("and", "and"),
            ("or if", "or"),
            ("or", "or"),
        ]
    )

    def __init__(self, dict_info: Dict) -> None:
        self._dict_info = dict_info
        self._uid_dict_info = {}
        for tag, info in dict_info.items():
            if info["name"].endswith(" UID"):
                uid_info = info.copy()
                uid_info["name"] = uid_info["name"][:-4]
                self._uid_dict_info[tag] = uid_info

    def parse(self, condition_str: str) -> Condition:
        """Parse the given condition string and return a Condition object
        with the required attributes.
        """
        condition_prefixes = (
            "required if ",
            "shall be present if ",
            "required for images where ",
            "required only if",
        )
        condition_lower = condition_str.lower()
        for prefix in condition_prefixes:
            index = condition_lower.find(prefix)
            if index >= 0:
                condition_str = condition_str[len(prefix) + index :]
                condition_str = self._fix_condition(condition_str)
                condition = self._parse_tag_expressions(condition_str)
                return condition
        # special handling for functional group restrictions
        if " not be used as a shared functional group" in condition_lower:
            ctype = ConditionType.per_frame_type(condition_str[0] == "M")
            return Condition(ctype=ctype)
        elif (
            " not be used as a per-frame functional group" in condition_lower
            or "shall be used as a shared functional group" in condition_lower
        ):
            ctype = ConditionType.shared_type(condition_str[0] == "M")
            return Condition(ctype=ctype)
        return Condition(ctype=ConditionType.UserDefined)

    def _parse_tag_expression(self, condition: str) -> Tuple[Condition, Optional[str]]:
        operator_text = None
        op_offset = None
        for operator in self.operators:
            offset = condition.find(operator)
            if offset > 0 and (op_offset is None or offset < op_offset):
                op_offset = offset
                operator_text = operator
        if operator_text is None or op_offset is None:
            return Condition(ctype=ConditionType.UserDefined), None
        operator = self.operators[operator_text]
        rest = condition[op_offset + len(operator_text) :]
        if operator in (
            ConditionOperator.EqualsValue,
            ConditionOperator.NotEqualsValue,
            ConditionOperator.GreaterValue,
            ConditionOperator.LessValue,
        ):
            values, rest = self._parse_tag_values(rest)
            # fixup special values
            if values:
                if isinstance(values[0], str):
                    if values[0].startswith("non-zero"):
                        operator = ConditionOperator.NotEqualsValue
                        values = ["0"] if values[0] == "non-zero" else [""]
                    elif values[0].startswith("non-null"):  # type:ignore[union-attr]
                        operator = ConditionOperator.NotEmpty
                        values = []
                    elif values[0].startswith("zero-length"):  # type:ignore[union-attr]
                        values = [""]
            else:
                # failed to parse mandatory values - ignore the condition
                return Condition(ctype=ConditionType.UserDefined), None
        elif operator == ConditionOperator.EqualsTag:
            value_string, rest = self._split_value_part(rest)
            tag, _ = self._parse_tag(value_string)
            if tag is None:
                return Condition(ctype=ConditionType.UserDefined), None
            values, rest = [str(self._tag_id(tag))], rest
        else:
            values, rest = [], rest.strip()
        result = self._parse_tags(condition[:op_offset], operator, values)
        if not result:
            return Condition(ctype=ConditionType.UserDefined), None

        result.type = (
            ConditionType.MandatoryOrNotAllowed
            if "not be present otherwise" in condition[op_offset:].lower()
            else ConditionType.MandatoryOrUserDefined
        )
        # special handling for AT tags - values are saved as numbers
        if (
            result.tag
            and result.values
            and operator == ConditionOperator.EqualsValue
            and result.tag in self._dict_info
            and self._dict_info[result.tag]["vr"] == "AT"
        ):
            result.values = [self._tag_id(str(v)) for v in result.values]
        return result, rest

    def _get_other_condition(self, condition_string: str) -> Optional[Condition]:
        match = re.match(
            ".*(may be present( otherwise)?( only)? if ).*", condition_string.lower()
        )
        if match is not None:
            marker = match.group(1)
            index = condition_string.lower().find(marker)
            return self._parse_tag_expressions(condition_string[index + len(marker) :])
        return None

    @staticmethod
    def _tag_id(tag_id_string: str) -> int:
        group, element = tag_id_string[1:-1].split(",")
        return (int(group, 16) << 16) + int(element, 16)

    def _tag_id_from_id_and_name(self, tag_id, tag_name):
        if not tag_name:
            return tag_id

        if not tag_id:
            # tag name only - look it up
            for tag_id, entry in self._dict_info.items():
                if entry["name"] == tag_name:
                    return tag_id
            for tag_id, entry in self._uid_dict_info.items():
                if entry["name"] == tag_name:
                    return tag_id
            return None

        # we have both tag name and ID
        id_entry = self._dict_info.get(tag_id)
        if not id_entry:
            return None
        name_from_id = id_entry["name"]
        if name_from_id == tag_name:
            # tag name matched tag ID
            return tag_id

        # tag name does not match tag ID
        # this may be either because the used tag name is not the
        # correct one, or there is additional text that we cannot parse

        # space may be used instead of hyphen
        real_name_parts = name_from_id.replace("-", " ").split()
        name_parts = tag_name.replace("-", " ").split()

        # first part of name may be omitted
        len_diff = len(real_name_parts) - len(name_parts)
        if len_diff < 0:
            return None

        # special case: missing second name part
        if " ".join([real_name_parts[0]] + real_name_parts[2:]) == tag_name:
            return tag_id

        # special case: name parts moved around
        if len_diff == 0 and sorted(real_name_parts) == sorted(name_parts):
            return tag_id

        # simple heuristic: just compare the first letters of each name part
        if any(a[0] != b[0] for a, b in zip(real_name_parts[len_diff:], name_parts)):
            # print(f"## Unreadable: {tag_name}, id: {tag_id}")
            return None
        return tag_id

    def _parse_tag(self, tag_string: str) -> Tuple[Optional[str], Optional[int]]:
        tag_string = tag_string.strip()
        match = (
            self.tag_expression1.match(tag_string)
            or self.tag_expression2.match(tag_string)
            or self.tag_expression3.match(tag_string)
        )
        if match:
            index_match = match.group("index")
            value_index = 0
            if index_match is not None:
                if index_match in ("first", "second", "third"):
                    value_index = ("first", "second", "third").index(index_match)
                else:
                    value_index = int(index_match) - 1
            tag_name = match.group("name").strip()
            tag_id = match.group("id")
            return self._tag_id_from_id_and_name(tag_id, tag_name), value_index

        return None, None

    def _parse_tag_values(self, value_string: str) -> Tuple[ValuesType, str]:
        value_part, rest = self._split_value_part(value_string)
        values: ValuesType = []
        value_index = 0
        last_or = None
        while value_index >= 0:
            value_index = -1
            current_or = ""
            for or_phrase in self._valid_or_expressions_after_or_expression(last_or):
                index = value_part.find(or_phrase)
                if index >= 0 and (value_index < 0 or index < value_index):
                    value_index = index
                    next_index = index + len(or_phrase)
                    current_or = or_phrase
            if value_index > 0:
                value, value_rest = self._get_const_value(value_part[:value_index])
                if value is None:
                    return values, current_or + value_part + rest
                values.append(value)
                if value_rest:
                    return values, current_or + value_rest + rest
                value_part = value_part[next_index:]
                last_or = current_or
        value, value_rest = self._get_const_value(value_part)
        if value is None:
            return values, value_part + rest
        values.append(value)
        return values, value_rest + rest

    def _split_value_part(self, value_string: str) -> Tuple[str, str]:
        value_string = value_string.strip()
        end_index = self._end_index_for_stop_chars(
            value_string, [";", ".", ", and ", " and ", ":"]
        )
        return value_string[:end_index], value_string[end_index:]

    @staticmethod
    def _valid_or_expressions_after_or_expression(
        previous_expr: Optional[str],
    ) -> List[str]:
        if previous_expr is None:
            return [", ", " or "]
        if previous_expr == " or ":
            return [" or "]
        if previous_expr == ", ":
            return [", or ", ", ", " or "]
        return []

    @staticmethod
    def _index_is_inside_string(value: str, index: int) -> bool:
        in_string = False
        apo_index = 0
        while apo_index >= 0:
            apo_index = value.find('"', apo_index, index)
            if apo_index >= 0:
                apo_index += 1
                in_string = not in_string
        return in_string

    def _get_const_value(self, value: str) -> Tuple[Optional[str], str]:
        value = value.strip()
        if value[0] == value[-1] == '"':
            return value[1:-1], ""
        if re.match("^[A-Z0-9][A-Za-z0-9_ ]*$", value) is not None:
            return value, ""
        # sometimes a value explanation is present in scopes
        match = re.match(r"^([A-Z0-9_ ]+)\([A-Za-z ]+\)+$", value)
        if match is not None:
            return match.group(1).strip(), ""
        if value == "zero length":
            return "", ""
        if value == "zero":
            return "0", ""
        if value in ("non-zero", "non-zero length", "non-null", "zero-length"):
            return value, ""
        match = re.match(r"^.* \(\"([\d.]+)\"\)(.*)$", value)
        if match is not None:
            return match.group(1), match.group(2)
        tag, index = self._parse_tag(value)
        if tag is not None:
            return tag, ""
        return None, ""

    def _end_index_for_stop_chars(self, value: str, stop_chars: List[str]) -> int:
        end_index = len(value)
        for stop_char in stop_chars:
            start_index = 0
            stop_index = 0
            while stop_index >= 0:
                stop_index = value.find(stop_char, start_index, end_index)
                if stop_index < 0:
                    break
                if self._index_is_inside_string(value, stop_index):
                    start_index = stop_index + 1
                else:
                    end_index = stop_index
                    break
        return end_index

    def _parse_tag_expressions(self, condition: str, nested: bool = False) -> Condition:
        result, rest = self._parse_tag_expression(condition)
        if rest is not None:
            rest = rest.strip()
            if rest.startswith(", "):
                rest = rest[2:]
            logical_op = None
            for operator in self.logical_ops:
                if rest.startswith(operator + " "):
                    logical_op = self.logical_ops[operator]
                    condition = rest[len(operator) + 1 :]
                    break
            if logical_op is not None:
                next_result = self._parse_tag_expressions(condition, nested=True)
                if next_result.type != ConditionType.UserDefined:
                    next_result.type = None
                    new_result = Condition(ctype=result.type)
                    cond_list = self._condition_list(logical_op, new_result)
                    cond_list.append(result)
                    cond_list.append(next_result)
                    result.type = None
                    result = new_result
                elif logical_op == "and":
                    # the second part of the condition could not be parsed
                    # this invalidates the whole condition
                    result = next_result
        if not nested and rest is not None:
            other_cond = self._get_other_condition(rest)
            if other_cond is not None:
                if other_cond.type == ConditionType.UserDefined:
                    if result.type != ConditionType.UserDefined:
                        result.type = ConditionType.MandatoryOrUserDefined
                else:
                    result.type = ConditionType.MandatoryOrConditional
                    result.other_condition = other_cond
        return result

    def _parse_tags(
        self, condition: str, operator: ConditionOperator, values: ValuesType
    ) -> Optional[Condition]:
        # this handles only a few cases that are actually found
        if ", and " in condition:
            return self._parse_tag_composition(condition, operator, values, "and")
        if ", or " in condition:
            return self._parse_tag_composition(condition, operator, values, "or")
        if " and " in condition:
            return self._parse_multiple_tags(condition, operator, values, "and")
        if " or " in condition:
            return self._parse_multiple_tags(condition, operator, values, "or")
        return self._result_from_tag_string(condition, operator, values)

    def _parse_tag_composition(
        self,
        condition_str: str,
        operator: ConditionOperator,
        values: ValuesType,
        logical_op: str,
    ) -> Optional[Condition]:
        split_string = f", {logical_op} "
        conditions = condition_str.split(split_string)
        result0 = self._parse_tags(conditions[0], operator, values)
        if result0 is None:
            result = self._parse_tags(
                condition_str.replace(split_string, split_string.replace(",", "")),
                operator,
                values,
            )
        else:
            result = Condition()
            cond_list = self._condition_list(logical_op, result)
            cond_list.append(result0)
            condition = self._parse_tags(conditions[1], operator, values)
            if condition is not None:
                cond_list.append(condition)
        return result

    def _parse_multiple_tags(
        self,
        condition: str,
        operator: ConditionOperator,
        values: ValuesType,
        logical_op: str,
    ) -> Optional[Condition]:
        condition = condition.replace(f" {logical_op} ", ", ")
        result = Condition()
        cond_list = self._condition_list(logical_op, result)
        for tag_string in condition.split(", "):
            tag_result = self._result_from_tag_string(tag_string, operator, values)
            if tag_result:
                cond_list.append(tag_result)
        if len(cond_list) > 1:
            return result
        return None

    @staticmethod
    def _condition_list(logical_op: str, result: Condition) -> List[Condition]:
        cond_list = (
            result.and_conditions if logical_op == "and" else result.or_conditions
        )
        return cond_list

    def _result_from_tag_string(
        self,
        tag_string: str,
        operator: ConditionOperator,
        values: ValuesType,
    ) -> Optional[Condition]:
        tag, index = self._parse_tag(tag_string)
        if tag is not None and index is not None:
            result = Condition(tag=tag, index=index, operator=operator)
            if values:
                result.values = values
            return result
        return None

    @staticmethod
    def _fix_condition(condition: str) -> str:
        condition = condition.replace("(Legacy Converted)", "")
        index = condition.lower().find(" may be present otherwise")
        if index > 0:
            if condition[index - 1] == ",":
                condition = condition[: index - 1] + "." + condition[index:]
            elif condition[index - 1] != ".":
                condition = condition[:index] + "." + condition[index:]
        return condition
