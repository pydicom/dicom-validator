from typing import Dict

from pyparsing import ParseException

from dicom_validator.spec_reader.condition import (
    Condition,
    ConditionType,
    ConditionOperator,
    ConditionMeaning,
)
from dicom_validator.spec_reader.condition_grammar import ConditionGrammar


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

    def __init__(self, dict_info: Dict) -> None:
        self._dict_info = dict_info
        self._uid_dict_info = {}
        for tag, info in dict_info.items():
            if info["name"].endswith(" UID"):
                uid_info = info.copy()
                uid_info["name"] = uid_info["name"][:-4]
                self._uid_dict_info[tag] = uid_info
        self._grammar: dict = ConditionGrammar(
            self._dict_info, self._uid_dict_info
        ).grammar()
        self._condition_cache: dict[str, Condition] = {}

    def parse(self, condition_str: str, debug: bool = False) -> Condition:
        """Parse the given condition string and return a Condition object
        with the required attributes.
        """
        cache_key = condition_str
        if not debug and cache_key in self._condition_cache:
            return Condition.read_condition(self._condition_cache[cache_key].dict())

        condition = self._parse_with_grammar(condition_str, self._grammar, debug)
        if not debug:
            self._condition_cache[cache_key] = condition
        return condition

    def _fix_condition_result(self, condition: Condition) -> Condition:
        """Some fix-ups to the condition returned as parse result."""
        # TODO: move to grammar?
        if (
            condition.values
            and isinstance(condition.values[0], tuple)
            and len(condition.values[0]) == 2
        ):
            # value is a tag expression
            condition.values = [self._tag_id(v[0]) for v in condition.values]

        if condition.operator == ConditionOperator.NonZero:
            condition.operator = ConditionOperator.NotEqualsValue
            condition.values = ["0"]
        condition.type = ConditionType.MandatoryOrUserDefined
        return condition

    def _parse_with_grammar(
        self, condition_str: str, grammar: dict, debug: bool = False
    ) -> Condition:
        # Handle special cases first
        condition_lower = condition_str.lower()

        # Special handling for functional group restrictions
        if " not be used as a shared functional group" in condition_lower:
            ctype = ConditionType.per_frame_type(condition_str[0] == "M")
            return Condition(ctype=ctype)
        elif (
            " not be used as a per-frame functional group" in condition_lower
            or "shall be used as a shared functional group" in condition_lower
        ):
            ctype = ConditionType.shared_type(condition_str[0] == "M")
            return Condition(ctype=ctype)

        try:
            prefix, _, end = next(grammar["prefix"].scan_string(condition_str))
        except (ParseException, StopIteration):
            return Condition(ctype=ConditionType.UserDefined)
        condition_str = self._fix_condition(condition_str[end:]).strip()

        try:
            if debug:
                print(f"\nParsing condition: {condition_str}")
            tokens, _, end = next(grammar["condition_expr"].scan_string(condition_str))
            if debug:
                print(f"Grammar parse result: {tokens}")

            condition = self._fix_condition_result(tokens[0])
            if debug:
                print(f"Created condition: {condition}")

            condition_str = condition_str[end:].strip()
            if condition_str and not condition_str.startswith(
                (".", ";", ":", "or ", ", or ", "and ", ", and ")
            ):
                raise ParseException(f"Invalid condition rest: {condition_str}")

            # Set the condition type
            if prefix[0] == ConditionMeaning.TagShallBeAbsent:
                if condition.type == ConditionType.MandatoryOrUserDefined:
                    condition.type = ConditionType.NotAllowedOrUserDefined
            else:
                condition.type = (
                    ConditionType.MandatoryOrNotAllowed
                    if "not be present otherwise" in condition_str.lower()
                    else ConditionType.MandatoryOrUserDefined
                )
        except (ParseException, StopIteration) as e:
            # If parsing fails, return a user-defined condition
            if debug:
                print(f"Error parsing condition {condition_str}: {e}")
            return Condition(ctype=ConditionType.UserDefined)

        try:
            tokens, _, _ = next(grammar["other_condition"].scan_string(condition_str))
            other_condition = self._fix_condition_result(tokens[0])
            if other_condition.type == ConditionType.UserDefined:
                if condition.type != ConditionType.UserDefined:
                    condition.type = ConditionType.MandatoryOrUserDefined
            else:
                other_condition.type = ConditionType.MandatoryOrUserDefined
                condition.type = ConditionType.MandatoryOrConditional
                condition.other_condition = other_condition
            if debug:
                print("\nother condition result:", condition.other_condition)
        except (ParseException, StopIteration):
            pass

        condition_str = condition_str.strip()
        # new sentences and unparsable or-conditions can be ignored
        if condition_str:
            if condition_str.startswith(("and ", ", and ")):
                if condition.other_condition:
                    condition.other_condition = None
                elif condition.or_conditions:
                    # remove the last or condition (related to the unparsable and)
                    if len(condition.or_conditions) > 2:
                        condition.or_conditions.pop()
                    else:
                        ctype = condition.type
                        condition = condition.or_conditions[0]
                        condition.type = ctype
                        condition.or_conditions = []
                else:
                    if debug:
                        print(f"Unparsable and condition: {condition_str}")
                    return Condition(ctype=ConditionType.UserDefined)
            elif not condition_str.startswith((".", ":", "or ", ", or ")):
                if debug:
                    print(f"Unparsable rest of condition: {condition_str}")
                return Condition(ctype=ConditionType.UserDefined)

        return condition

    @staticmethod
    def _tag_id(tag_id_string: str) -> int:
        if tag_id_string is None:
            return 0
        group, element = tag_id_string[1:-1].split(",")
        return (int(group, 16) << 16) + int(element, 16)

    @staticmethod
    def _fix_condition(condition: str) -> str:
        condition = condition.replace("(Legacy Converted)", "")
        index = condition.lower().find(" may be present otherwise")
        if index > 0:
            if condition[index - 1] in (",", ";"):
                condition = condition[: index - 1] + "." + condition[index:]
            elif condition[index - 1] != ".":
                condition = condition[:index] + "." + condition[index:]
        index = condition.lower().find(", that is ")
        if index > 0:
            condition = condition[index + 10 :]
        return condition
