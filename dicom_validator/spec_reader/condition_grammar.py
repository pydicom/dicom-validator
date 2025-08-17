import string
from re import RegexFlag
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
    ConditionType,
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
        value_grammar = self._value_grammar(self._tag_expression_grammar(is_value=True))
        tag_expression_grammar = self._tag_expression_grammar(is_value=False)
        simple_condition_grammar = (
            self._simple_condition_grammar(tag_expression_grammar, value_grammar)
            + self._in_module_grammar()
        )
        condition_grammar = self._tag_condition_grammar(
            simple_condition_grammar, value_grammar
        )
        other_condition_prefix = Suppress(
            CaselessKeyword("may be present") + Opt("otherwise") + Opt("only") + "if"
        )

        return {
            "prefix": AtLineStart(self._condition_prefix_grammar()),
            "condition_expr": AtLineStart(condition_grammar),
            "other_condition": other_condition_prefix + condition_grammar,
        }

    @staticmethod
    def _condition_prefix_grammar() -> ParserElement:
        required_cond = Regex(
            r".*(required if|shall be present if|required for images where|required only if)",
            flags=RegexFlag.IGNORECASE,
        ).set_parse_action(lambda: ConditionMeaning.TagShallBePresent)
        absent_cond = Regex(
            ".*shall not be present if", flags=RegexFlag.IGNORECASE
        ).set_parse_action(lambda: ConditionMeaning.TagShallBeAbsent)
        return required_cond | absent_cond

    def _tag_condition_grammar(
        self, simple_condition: ParserElement, value_grammar: ParserElement
    ) -> ParserElement:
        and_op = Regex(r"(?!, )and( whose| if)?").set_parse_action(lambda: "and")
        comma_and_op = Regex(r", and( whose| if)?").set_parse_action(lambda: "and")
        or_op = Regex(r"(?!, )or( if)?").set_parse_action(lambda: "or")
        comma_or_op = Regex(r", or( if)?").set_parse_action(lambda: "or")
        # Compound conditions
        value_prefix = Opt(
            Suppress(Keyword("Value")) + (Keyword("1") | "2" | "3" | "4")
        )
        condition_without_tag = Group(
            value_prefix + self._condition_grammar(value_grammar)
        ).set_parse_action(lambda r: self._condition_from_condition_expression(r[0]))
        or_conditions = Group(
            simple_condition + OneOrMore((or_op | comma_or_op) + condition_without_tag)
        ).set_parse_action(lambda r: self._combined_condition(r[0]))
        and_conditions = Group(
            simple_condition
            + OneOrMore((and_op | comma_and_op) + condition_without_tag)
        ).set_parse_action(lambda r: self._combined_condition(r[0]))
        tag_condition = and_conditions | or_conditions | simple_condition
        combined_condition = (
            Group(
                tag_condition
                + (OneOrMore(and_op + tag_condition) | OneOrMore(or_op + tag_condition))
            ).set_parse_action(lambda r: self._combined_condition(r[0]))
            | tag_condition
        )
        and_condition = Group(
            combined_condition + OneOrMore(comma_and_op + combined_condition)
        ).set_parse_action(lambda r: self._combined_condition(r[0]))
        or_condition = Group(
            combined_condition + OneOrMore(comma_or_op + combined_condition)
        ).set_parse_action(lambda r: self._combined_condition(r[0]))

        # anything else after a comma and before a period or semicolon
        # is considered an explanation or clarification
        explanation = Regex(r"(, (?!and|or)[^.;:]*)?")
        condition_expr = (
            and_condition | or_condition | combined_condition
        ) + explanation
        return condition_expr

    @staticmethod
    def _combined_condition(result: ParserElement) -> Condition:
        combined_condition = Condition(ctype=ConditionType.MandatoryOrUserDefined)
        if result[1] == "or":
            conditions = combined_condition.or_conditions
        else:
            conditions = combined_condition.and_conditions

        for index, condition in enumerate(result):
            if index % 2 == 0:
                if (
                    not condition.tag
                    and not condition.or_conditions
                    and not condition.and_conditions
                ):
                    condition.tag = conditions[0].tag
                conditions.append(condition)

        # special case: transform (c1 or c2) and c3 to c1 or (c2 and c3)
        if (
            len(combined_condition.and_conditions) == 2
            and len(combined_condition.and_conditions[0].or_conditions) == 2
        ):
            combined_condition.or_conditions.append(
                combined_condition.and_conditions[0].or_conditions[0]
            )
            and_condition = Condition()
            and_condition.and_conditions = [
                combined_condition.and_conditions[0].or_conditions[1],
                combined_condition.and_conditions[1],
            ]
            combined_condition.or_conditions.append(and_condition)
            combined_condition.and_conditions = []

        return combined_condition

    @staticmethod
    def _validate_condition(condition: Condition) -> Condition:
        if condition.tag is None:
            raise ParseException("Condition tag is None")
        if condition.operator is None:
            raise ParseException("Missing condition operator")
        if is_binary_condition(condition.operator) and not condition.values:
            raise ParseException("Missing condition value")
        if condition.operator == ConditionOperator.NonZero:
            condition.operator = ConditionOperator.NotEqualsValue
            condition.values = ["0"]
        return condition

    def _simple_condition_grammar(
        self, tag_expr: ParserElement, values_expr: ParserElement
    ) -> ParserElement:
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
        condition_expression = self._condition_grammar(values_expr)
        return Group(tag_expressions + condition_expression).set_parse_action(
            lambda result: self._condition_from_tag_expression(result)
        )

    def _condition_grammar(self, values_grammar):
        operator_grammar = self._operator_grammar()
        condition_expression = (
            Suppress(Opt(Keyword("value") | "the value" | "the Value"))
            + operator_grammar
            + Opt(values_grammar)
        )
        return condition_expression

    def _condition_from_condition_expression(self, result: ParseResult) -> Condition:
        tag_index = 0
        index = 0
        if result[0] in ("1", "2", "3", "4"):
            tag_index = int(result[0]) - 1
            index += 1
        values: list = result[index + 1 :]  # type: ignore[assignment]
        return self._validate_condition(
            Condition(
                tag="",
                index=tag_index,
                operator=result[index],  # type: ignore[arg-type]
                values=values,
            )
        )

    def _condition_from_tag_expression(self, result: ParseResult) -> Condition:
        def condition_from_tag(tag, ctype=None) -> Condition:
            return self._validate_condition(
                Condition(
                    ctype=ctype,
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
            condition = Condition(ctype=ConditionType.MandatoryOrUserDefined)
            if result[0].and_tags:  # type: ignore[attr-defined]
                condition.and_conditions = conditions
            else:
                condition.or_conditions = conditions
            return condition

        # single tag expression
        return condition_from_tag(
            result[0][0], ctype=ConditionType.MandatoryOrUserDefined
        )

    @staticmethod
    def _operator_grammar() -> ParserElement:
        absent_op = (
            Keyword("is not sent")
            | CaselessKeyword("is not present in this Sequence Item")
            | Keyword("is not present")
            | Keyword("is absent")
            | Keyword("are not present")
        ).set_parse_action(lambda: ConditionOperator.Absent)
        not_empty_op1 = (
            CaselessKeyword("is non-null") | CaselessKeyword("is non-zero length")
        ).set_parse_action(lambda: ConditionOperator.NotEmpty)
        not_equals_op = (
            Keyword("equals other than")
            | CaselessKeyword("value is not")
            | Keyword("is not equal to")
            | Keyword("is not any of")
            | Keyword("is not:")
            | Keyword("is not")
            | Keyword("not")
            | Keyword("is other than")
            | CaselessKeyword("is present with a value other than")
        ).set_parse_action(lambda: ConditionOperator.NotEqualsValue)
        greater_op = (
            CaselessKeyword("has a value of more than")
            | Keyword("is greater than")
            | CaselessKeyword("has a value greater than")
            | CaselessKeyword("is present and has a value greater than")
        ).set_parse_action(lambda: ConditionOperator.GreaterValue)
        less_op = (Keyword("is less than")).set_parse_action(
            lambda: ConditionOperator.LessValue
        )
        non_zero_op = CaselessKeyword("is non-zero").set_parse_action(
            lambda: ConditionOperator.NonZero
        )
        equals_op = (
            CaselessKeyword("is present and the value is")
            | CaselessKeyword("is present and has a value of")
            | CaselessKeyword("is present and has the value")
            | Keyword("is present and is either")
            | CaselessKeyword("is present with value")
            | Keyword("is present and equals")
            | CaselessKeyword("is present with a value of")
            | Keyword("is set to")
            | CaselessKeyword("equals one of the following values:")
            | CaselessKeyword("has a value of")
            | CaselessKeyword("has value")
            | Keyword("=")
            | CaselessKeyword("at the image level equals")
            | Keyword("equals")
            | Keyword("is one of the following:")
            | CaselessKeyword("value is")
            | Keyword("is equal to")
            | Keyword("equals")
            | CaselessKeyword("has the value")
        ).set_parse_action(lambda: ConditionOperator.EqualsValue)
        not_empty_op2 = (
            CaselessKeyword("is present and has a value")
            | CaselessKeyword("is present with a value")
            | CaselessKeyword("has a value")
        ).set_parse_action(lambda: ConditionOperator.NotEmpty)
        present_op = (
            CaselessKeyword("is present in this Sequence Item")
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

    def _tag_expression_grammar(self, is_value: bool) -> ParserElement:
        tag_id = Regex(r"\([\da-fA-F]{4},[\da-fA-F]{4}\)")
        # some special handling for less common tag names,
        # may need to be adapted for new tags
        tag_name_capitalized = Regex(r"(2D|3D|[A-Z][A-Za-z'\-]+)")
        unit_name = Regex(r"ms|mAs|mA|mGy|uS|uA|ppm|yyy|zzz")
        tag_name_inner = ~(Regex("is|not|or|equals") | unit_name) + Word(
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
            Suppress(CaselessKeyword("the"))
            + (
                Keyword("first").set_parse_action(lambda: "1")
                | Keyword("second").set_parse_action(lambda: "2")
                | Keyword("third").set_parse_action(lambda: "3")
            )
            + Suppress(CaselessKeyword("value") + "of")
        )
        value_index2 = Regex(r"Value (?P<index>\d) of").set_parse_action(
            lambda r: r.index
        )
        value_index3 = Regex(r"(, )?Value (?P<index>\d)").set_parse_action(
            lambda r: r.index
        )
        prefix1_regex = "((the|a) )?[vV]alue( (of|for))?"
        prefix2_regex = "(the|either|Attribute)?"
        tag_expr_prefix = Suppress(
            Regex(f"({prefix1_regex}|{prefix2_regex})( the( [vV]alue))?")
        ) + Opt(tag_id)
        tag_name_expr = Opt(value_index1 | value_index2 | tag_expr_prefix) + tag_name
        action = (
            self._tag_value_from_expression if is_value else self._tag_from_expression
        )
        return Group(
            tag_name_expr
            + Opt(tag_id)
            + Opt(value_index3)
            + Suppress(Opt(Keyword("of this frame") | "of this Frame"))
            + self._in_module_grammar()
        ).set_parse_action(lambda result: action(result[0]))

    @staticmethod
    def _in_module_grammar() -> ParserElement:
        return Suppress(Regex(r"(in the [a-zA-Z ]+ Module)?"))

    @staticmethod
    def _value_grammar(tag_expression: ParserElement) -> ParserElement:
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
        uid_value = Regex(
            r'"(?P<uid>\d+(\.\d+)+)( \([a-zA-Z ]+\))?"( \([a-zA-Z ]+\))?'
        ).set_parse_action(lambda r: r.uid)
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
                + ZeroOrMore(Suppress(", or") + value_type)
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

    def _tag_value_from_expression(self, tag_expr: ParseResult) -> int:
        tag, _ = self._tag_from_expression(tag_expr)
        group, element = tag[1:-1].split(",")
        return (int(group, 16) << 16) + int(element, 16)

    def _tag_from_expression(self, tag_expr: ParseResult) -> tuple[str, int]:
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

    def _tag_id_from_id_and_name(self, tag_id: str | None, tag_name: str) -> str | None:
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
