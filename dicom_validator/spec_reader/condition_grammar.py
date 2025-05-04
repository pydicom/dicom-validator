import string
from typing import Tuple, Optional
from urllib.parse import ParseResult

from pyparsing import (
    ParserElement,
    Group,
    OneOrMore,
    Suppress,
    Combine,
    Opt,
    Word,
    nums,
    alphanums,
    DelimitedList,
    ZeroOrMore,
    ParseException,
    alphas,
    CaselessKeyword,
    Keyword,
    Regex,
    AtLineStart,
)

from dicom_validator.spec_reader.condition import (
    ConditionOperator,
    ConditionMeaning,
    Condition,
    is_binary_condition,
)


class ConditionGrammar:
    def __init__(self, dict_info: dict, uid_dict_info: dict) -> None:
        self.dict_info = dict_info
        self.uid_dict_info = uid_dict_info

    def grammar(self) -> dict[str, ParserElement]:
        """Initialize the grammar (PEG) used to parse DICOM conditions.

        Returns
        -------
        dict
            A dictionary containing the grammar with the following keys:
            - prefix: the grammar for the mandatory condition prefix used to check
                the presence of condition expression
            - condition_expr: the grammar for the main condition expression
            - other_condition: the grammar for an optional condition related to the case
                that the condition expression is not met.
        """
        # pyparsing is quite slow, so for some performance improvement
        # we use packrat parsing for caching, and Regex where possible
        # to reduce the number of function calls
        ParserElement.enablePackrat()

        tag_expr = self._tag_expression()
        values_expr = self._value_expression(tag_expr)
        simple_condition = (
            self._simple_condition(tag_expr, values_expr) + self._in_module_expression()
        )
        condition_expr = self._condition_expression(simple_condition)
        other_condition_prefix = Suppress(
            CaselessKeyword("may be present") + Opt("otherwise") + Opt("only") + "if"
        )

        return {
            "prefix": self._condition_prefix(),
            "condition_expr": AtLineStart(condition_expr),
            "other_condition": other_condition_prefix + condition_expr,
        }

    @staticmethod
    def _condition_prefix() -> ParserElement:
        required_cond = (
            CaselessKeyword("required if")
            | CaselessKeyword("shall be present if")
            | CaselessKeyword("required for images where")
            | CaselessKeyword("required only if")
        ).set_parse_action(lambda: ConditionMeaning.TagShallBePresent)
        absent_cond = CaselessKeyword("shall not be present if").set_parse_action(
            lambda: ConditionMeaning.TagShallBeAbsent
        )
        condition_prefix = required_cond | absent_cond
        return condition_prefix

    def _condition_expression(self, simple_condition: ParserElement) -> ParserElement:
        and_op = Regex(r"(?!, )and( whose| if)?").set_parse_action(lambda: "and")
        comma_and_op = Regex(r", and( whose| if)?").set_parse_action(lambda: "and")
        or_op = Regex(r"(?!, )or( if)?").set_parse_action(lambda: "or")
        comma_or_op = Regex(r", or( if)?").set_parse_action(lambda: "or")
        # Compound conditions
        combined_condition = (
            Group(
                simple_condition
                + (
                    OneOrMore(and_op + simple_condition)
                    | OneOrMore(or_op + simple_condition)
                )
            ).set_parse_action(lambda r: self._combined_conditions(r))
            | simple_condition
        )
        and_condition = Group(
            combined_condition + OneOrMore(comma_and_op + combined_condition)
        ).set_parse_action(lambda r: self._combined_conditions(r))
        or_condition = Group(
            combined_condition + OneOrMore(comma_or_op + combined_condition)
        ).set_parse_action(lambda r: self._combined_conditions(r))

        # anything else after a comma and before a period or semicolon
        # is considered an explanation or clarification
        explanation = Regex(r"(, (?!and|or)[^.;:]*)?")
        condition_expr = (
            and_condition | or_condition | combined_condition
        ) + explanation
        return condition_expr

    @staticmethod
    def _combined_conditions(result: ParserElement) -> Condition:
        # print(f"_combined_conditions: {result}")
        combined_condition = Condition()
        if result[0][1] == "or":
            conditions = combined_condition.or_conditions
        else:
            conditions = combined_condition.and_conditions

        for index, condition in enumerate(result[0]):
            if index % 2 == 0:
                conditions.append(condition)
        return combined_condition

    @staticmethod
    def _validate_condition(condition: Condition) -> Condition:
        if condition.tag is None:
            raise ParseException("Condition tag is None")
        if condition.operator is None:
            raise ParseException("Missing condition operator")
        if is_binary_condition(condition.operator) and not condition.values:
            raise ParseException("Missing condition value")
        return condition

    def _simple_condition(
        self, tag_expr: ParserElement, values_expr: ParserElement
    ) -> ParserElement:

        condition_operators = self._operators()
        or_expressions = Group(
            tag_expr
            + ZeroOrMore(Suppress(",") + tag_expr)
            + OneOrMore(Suppress(Keyword("or") | ", or") + tag_expr)
        ).set_results_name("or_tags")
        and_expressions = Group(
            (or_expressions | tag_expr)
            + ZeroOrMore(Suppress(",") + tag_expr)
            + OneOrMore(Suppress(Keyword("and") | ", and") + tag_expr)
        ).set_results_name("and_tags")
        tag_expressions = and_expressions | or_expressions | tag_expr
        condition_expression = (
            Suppress(Opt(Keyword("value") | "the value"))
            + condition_operators
            + Opt(values_expr)
        )
        return Group(tag_expressions + condition_expression).set_parse_action(
            lambda result: self.condition_from_tag_expression(result)
        )

    def condition_from_tag_expression(self, result: ParseResult) -> Condition:
        def condition_from_tag(tag) -> Condition:
            return self._validate_condition(
                Condition(
                    None,
                    operator=result[0][1],  # type: ignore[arg-type]
                    tag=tag[0],
                    index=tag[1],
                    values=values,
                )
            )

        values: list = result[0][2:]  # type: ignore[assignment]
        if result[0].and_tags or result[0].or_tags:  # type: ignore[attr-defined]
            if result[0].and_tags and result[0][0].or_tags:  # type: ignore[attr-defined]
                # combined OR and AND conditions
                or_conditions = [condition_from_tag(tag) for tag in result[0][0][0]]
                or_condition = Condition()
                or_condition.or_conditions = or_conditions
                conditions = [or_condition, condition_from_tag(result[0][0][1])]
            else:
                # OR / AND condition
                conditions = [condition_from_tag(tag) for tag in result[0][0]]
            condition = Condition()
            if result[0].and_tags:  # type: ignore[attr-defined]
                condition.and_conditions = conditions
            else:
                condition.or_conditions = conditions
            return condition

        # single tag expression
        return condition_from_tag(result[0][0])

    @staticmethod
    def _operators() -> ParserElement:
        absent_op = (
            Keyword("is not sent")
            | Keyword("is not present in this Sequence Item")
            | Keyword("is not present")
            | Keyword("is absent")
            | Keyword("are not present")
        ).set_parse_action(lambda: ConditionOperator.Absent)
        not_empty_op1 = (
            Keyword("is non-null") | Keyword("is non-zero length")
        ).set_parse_action(lambda: ConditionOperator.NotEmpty)
        not_equals_op = (
            Keyword("equals other than")
            | Keyword("value is not")
            | Keyword("is not equal to")
            | Keyword("is not")
            | Keyword("is other than")
            | Keyword("is present with a value other than")
        ).set_parse_action(lambda: ConditionOperator.NotEqualsValue)
        greater_op = (
            Keyword("has a value of more than")
            | Keyword("is greater than")
            | Keyword("has a value greater than")
            | Keyword("is present and has a value greater than")
        ).set_parse_action(lambda: ConditionOperator.GreaterValue)
        less_op = (Keyword("is less than")).set_parse_action(
            lambda: ConditionOperator.LessValue
        )
        non_zero_op = Keyword("is non-zero").set_parse_action(
            lambda: ConditionOperator.NonZero
        )
        equals_op = (
            Keyword("is present and the value is")
            | Keyword("is present and has a value of")
            | Keyword("is present with value")
            | Keyword("is present and equals")
            | Keyword("is present with a value of")
            | Keyword("is set to")
            | Keyword("equals one of the following values:")
            | Keyword("has a value of")
            | Keyword("=")
            | Keyword("at the image level equals")
            | Keyword("equals")
            | Keyword("is one of the following:")
            | Keyword("value is")
            | Keyword("is equal to")
            | Keyword("equals")
            | Keyword("has the value")
        ).set_parse_action(lambda: ConditionOperator.EqualsValue)
        not_empty_op2 = (
            Keyword("is present and has a value")
            | Keyword("is present with a value")
            | Keyword("has a value")
        ).set_parse_action(lambda: ConditionOperator.NotEmpty)
        present_op = (
            Keyword("is present in this Sequence Item")
            | Keyword("is present")
            | Keyword("exists")
            | Keyword("is sent")
            | Keyword("are present")
        ).set_parse_action(lambda: ConditionOperator.Present)
        is_op = (Keyword("is:") | Keyword("is")).set_parse_action(
            lambda: ConditionOperator.EqualsValue
        )
        tag_op = Keyword("points to").set_parse_action(
            lambda: ConditionOperator.EqualsTag
        )
        return (
            absent_op
            | not_empty_op1
            | not_equals_op
            | greater_op
            | less_op
            | non_zero_op
            | equals_op
            | not_empty_op2
            | present_op
            | is_op
            | tag_op
        )

    def _tag_expression(self) -> ParserElement:
        tag_id = Regex(r"\([\da-fA-F]{4},[\da-fA-F]{4}\)")
        # some special handling for less common tag names,
        # may need to be adapted for new tags
        tag_name_capitalized = Regex(r"(2D|3D|[A-Z][A-Za-z'\-]+)")
        unit_name = Regex(r"ms|mAs|mA|mGy|uS|uA|ppm|yyy|zzz")
        tag_name_inner = ~(Regex("is|not|or") | unit_name) + Word(
            string.ascii_lowercase + nums, alphanums + "'-", as_keyword=True
        )
        tag_name = (
            (
                OneOrMore(tag_name_capitalized)
                + ZeroOrMore(tag_name_inner)
                + OneOrMore(tag_name_capitalized | unit_name)
            )
            | OneOrMore(tag_name_capitalized)
        ).set_parse_action(" ".join)
        # Tag value number
        value_index1 = (
            Suppress("the")
            + (
                Keyword("first").set_parse_action(lambda: "1")
                | Keyword("second").set_parse_action(lambda: "2")
                | Keyword("third").set_parse_action(lambda: "3")
            )
            + Suppress("value of")
        )
        value_index2 = Regex(r"Value (?P<index>\d) of").set_parse_action(
            lambda r: r.index
        )
        value_index3 = Regex(r"(, )?Value (?P<index>\d)").set_parse_action(
            lambda r: r.index
        )
        tag_expr_prefix1 = Regex("((the|a) )?value( (of|for))?")
        tag_expr_prefix2 = Regex("(the|either|Attribute)?")
        tag_expr_prefix = Suppress(tag_expr_prefix1 | tag_expr_prefix2)
        tag_expr_prefix = (
            tag_expr_prefix + Opt(Keyword("value") | "the value") + Opt(tag_id)
        )
        tag_name_expr = Opt(value_index1 | value_index2 | tag_expr_prefix) + tag_name
        tag_expr = Group(
            tag_name_expr
            + Opt(tag_id)
            + Opt(value_index3)
            + Suppress(Opt("of this frame"))
            + self._in_module_expression()
        ).set_parse_action(lambda result: self._tag_from_expression(result[0]))
        return tag_expr

    @staticmethod
    def _in_module_expression() -> ParserElement:
        return Suppress(Regex(r"(in the [a-zA-Z ]+ Module)?"))

    @staticmethod
    def _value_expression(tag_expression: ParserElement) -> ParserElement:
        # handle some special values
        zero_length_value = Regex("zero[- ]length").set_parse_action(lambda: "")
        zero_value = Keyword("zero").set_parse_action(lambda: "0")
        description = Suppress(Regex(r"(\([A-Za-z0-9 ]+\))?"))

        # the majority of values are all-caps like "COMPOSITE" or "PALETTE COLOR"
        all_caps_value = (
            DelimitedList(
                Word(string.ascii_uppercase + nums + "_", as_keyword=True),
                delim=" ",
                combine=True,
            )
            + description
        )

        # matches "Bits aligned" and similar that rarely occur
        mixed_caps_value = (
            Combine(
                Word(
                    string.ascii_uppercase + nums + "_",
                    string.ascii_lowercase + nums + "_",
                    as_keyword=True,
                )
                + ZeroOrMore(" " + Word(alphanums + "_")),
            )
            + description
        )

        # UIDs are always quoted and may be followed by an explanation
        uid_value = Regex(r'"(?P<uid>\d+(\.\d+)+)"( \([a-zA-Z ]+\))?').set_parse_action(
            lambda r: r.uid
        )
        # SOP Class UIDs may be written by the name followed by the UID in parentheses
        sop_class_value = (
            Suppress(
                ~(Keyword("or") | "and")
                + OneOrMore(
                    Word(string.ascii_uppercase, alphas + "-", as_keyword=True),
                )
            )
            + Suppress("(")
            + uid_value
            + Suppress(")")
            + Suppress(
                Opt(Opt(Keyword("Storage") + "SOP" + (Keyword("Classes") | "Class")))
            )
        )
        quoted_value = (
            Suppress('"') + (all_caps_value | mixed_caps_value) + Suppress('"')
        )

        # ensure that only values of the same type can be combined
        def make_value_list(value_type):
            return (
                value_type
                + ZeroOrMore(Suppress(",") + value_type)
                + ZeroOrMore(Suppress("or") + value_type)
                + Opt(Suppress(", or") + value_type)
            )

        values_expr = (
            make_value_list(sop_class_value)
            | make_value_list(uid_value)
            | make_value_list(quoted_value)
            | make_value_list(tag_expression)
            | make_value_list(all_caps_value)
            | make_value_list(mixed_caps_value)
            | zero_length_value
            | zero_value
        )

        return values_expr

    def _tag_from_expression(self, tag_expr: ParseResult) -> Tuple[str, int]:
        def is_index(item):
            return len(item) == 1 and item.isnumeric()

        expr_index = 0
        tag_index = 0
        if len(tag_expr) > 1 and is_index(tag_expr[expr_index]):
            tag_index = int(tag_expr[expr_index]) - 1
            expr_index += 1
        tag_name = tag_expr[expr_index]
        expr_index += 1
        if len(tag_expr) > expr_index:
            if is_index(tag_expr[expr_index]):
                tag_index = int(tag_expr[expr_index]) - 1
                expr_index += 1
        tag_id = tag_expr[expr_index] if len(tag_expr) > expr_index else None
        expr_index += 1
        if len(tag_expr) > expr_index and is_index(tag_expr[expr_index]):
            tag_index = int(tag_expr[expr_index]) - 1
        tag = self._tag_id_from_id_and_name(tag_id, tag_name)
        if tag is None:
            raise ParseException(f"Not a valid tag expression: {tag_expr}")
        return tag, tag_index

    def _tag_id_from_id_and_name(
        self, tag_id: Optional[str], tag_name: str
    ) -> Optional[str]:
        # print(f"_tag_id_from_id_and_name({tag_id}, {tag_name})")
        if not tag_name:
            return tag_id

        if not tag_id:
            # tag name only - look it up
            for tag_id, entry in self.dict_info.items():
                if entry["name"] == tag_name:
                    return tag_id
            for tag_id, entry in self.uid_dict_info.items():
                if entry["name"] == tag_name:
                    return tag_id
            return None

        # we have both tag name and ID
        id_entry = self.dict_info.get(tag_id)
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
