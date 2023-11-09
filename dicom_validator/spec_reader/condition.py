import enum
from typing import Optional, List, Dict, Any, Union

from dicom_validator.tag_tools import tag_name_from_id


ValuesType = List[Union[str, int]]


class ConditionType(str, enum.Enum):  # replace later with StrEnum from Python 3.11
    """The type of the condition, which defines the consequences of the condition
    being met or not met for the existence of the related tag."""

    # user defined, e.g. both existence or non-existence
    # of the related object is considered legal
    UserDefined = "U"
    # mandatory if the condition is fulfilled, otherwise not allowed
    MandatoryOrNotAllowed = "MN"
    # mandatory if the condition is fulfilled, otherwise user defined
    MandatoryOrUserDefined = "MU"
    # mandatory if the condition is fulfilled,
    # otherwise another condition will be checked
    MandatoryOrConditional = "MC"
    # mandatory in the per-frame functional groups,
    # not allowed in the shared functional groups
    MandatoryPerFrame = "MF"
    # may be present in the per-frame functional groups,
    # not allowed in the shared functional groups
    UserDefinedPerFrame = "UF"
    # mandatory in the per-frame functional groups,
    # not allowed in the shared functional groups
    MandatoryShared = "MS"
    # may be present in the per-frame functional groups,
    # not allowed in the shared functional groups
    UserDefinedShared = "US"

    @property
    def user_defined(self):
        return self in (
            self.UserDefined,
            self.UserDefinedPerFrame,
            self.UserDefinedShared,
        )

    @classmethod
    def per_frame_type(cls, is_mandatory):
        return cls.MandatoryPerFrame if is_mandatory else cls.UserDefinedPerFrame

    @classmethod
    def shared_type(cls, is_mandatory):
        return cls.MandatoryShared if is_mandatory else cls.UserDefinedShared


class ConditionOperator(str, enum.Enum):
    """The operator used in the condition in that defines if the related tag
    is required."""

    # tag exists
    Present = "+"
    # tag exists and has a value
    NotEmpty = "++"
    # tag does not exist
    Absent = "-"
    # tag has one of the given values
    EqualsValue = "="
    # tag does not have one of the given values
    NotEqualsValue = "!="
    # tag value is greater than the given value
    GreaterValue = ">"
    # tag value is less than the given value
    LessValue = "<"
    # tag points to one of the given tag IDs
    EqualsTag = "=>"


class Condition:
    """Represents a condition for the presence of a specific tag.

    Attributes:
        type: ConditionType
            the type of the related object (tag or module) regarding its existence
        tag: str | None
            the ID of the required tag in the form '(####,####)' or None
        index: int
            the index of the tag for multivalued tags or 0
        values: list[str] | None
            a list of values the tag shall have if the condition
            is fulfilled, or None
        operator: ConditionOperator | None
            the comparison operation used for the value(s), or None

    """

    def __init__(
        self,
        ctype: Optional[ConditionType] = None,
        operator: Optional[ConditionOperator] = None,
        tag: Optional[str] = None,
        index: int = 0,
        values: Optional[ValuesType] = None,
    ) -> None:
        self.type = ctype
        self.operator = operator
        self.tag = tag
        self.index = index
        self.values: ValuesType = values or []
        self.and_conditions: List[Condition] = []
        self.or_conditions: List[Condition] = []
        self.other_condition: Optional[Condition] = None

    def __repr__(self):
        return (
            f"Condition type={self.type} op='{self.operator}'"
            f" tag={self.tag} values={self.values}"
        )

    @classmethod
    def read_condition(
        cls, condition_dict: Dict, condition: Optional["Condition"] = None
    ) -> "Condition":
        """Create or update a Condition object from a condition dict.
        Parameters
        ----------
        condition_dict : dict
            Contains condition or sub-condition attributes

        condition : Condition | None
            If not None, the condition that shall be updated from the dict,
            otherwise a new Condition object is created.

        Returns
        -------
        Condition
            A condition object containing the given attributes.
        """
        condition = condition or Condition()
        condition.type = condition_dict.get("type")
        condition.operator = condition_dict.get("op")
        condition.tag = condition_dict.get("tag")
        condition.index = int(condition_dict.get("index", "0"))
        condition.values = condition_dict.get("values", [])
        and_list = condition_dict.get("and", [])
        condition.and_conditions = [cls.read_condition(cond) for cond in and_list]
        or_list = condition_dict.get("or", [])
        condition.or_conditions = [cls.read_condition(cond) for cond in or_list]
        if "other_cond" in condition_dict:
            condition.other_condition = cls.read_condition(condition_dict["other_cond"])
            condition.other_condition.type = condition_dict["other_cond"].get("type")
        return condition

    def dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        result.update(self.write_condition(self))
        return result

    @classmethod
    def write_condition(cls, condition: "Condition") -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if condition.operator is not None:
            result["op"] = condition.operator
        if condition.tag is not None:
            result["tag"] = condition.tag
            result["index"] = condition.index
        if condition.values:
            result["values"] = condition.values
        if condition.and_conditions:
            result["and"] = []
            for and_condition in condition.and_conditions:
                result["and"].append(cls.write_condition(and_condition))
        if condition.or_conditions:
            result["or"] = []
            for or_condition in condition.or_conditions:
                result["or"].append(cls.write_condition(or_condition))
        if condition.other_condition is not None:
            result["other_cond"] = condition.other_condition.dict()
        return result

    def to_string(self, dict_info: Dict) -> str:
        """Return a condition readable as part of a sentence."""
        result = ""
        if self.and_conditions:
            return " and ".join(
                cond.to_string(dict_info) for cond in self.and_conditions
            )
        if self.or_conditions:
            return " or ".join(cond.to_string(dict_info) for cond in self.or_conditions)
        if self.tag is not None:
            if dict_info and self.tag in dict_info:
                result = dict_info[self.tag]["name"]
            else:
                result = self.tag
            if self.index:
                result += f"[{self.index}]"
        if self.operator is None:
            return result
        if self.operator == ConditionOperator.Present:
            result += " exists"
        elif self.operator == ConditionOperator.NotEmpty:
            result += " exists and has a value"
        elif self.operator == ConditionOperator.Absent:
            result += " is not present"
        elif self.operator == ConditionOperator.EqualsTag:
            tag_value = int(self.values[0])
            result += " points to " + tag_name_from_id(tag_value, dict_info)
        elif not self.values:
            # if no values are found here, we have some unhandled condition
            # and ignore it for the time being
            return result
        elif self.operator == ConditionOperator.EqualsValue:
            values = ['"' + str(value) + '"' for value in self.values]
            result += " is equal to "
            if len(values) > 1:
                result += ", ".join(values[:-1]) + " or "
            result += values[-1]
        elif self.operator == ConditionOperator.NotEqualsValue:
            values = ['"' + str(value) + '"' for value in self.values]
            result += " is not equal to "
            if len(values) > 1:
                result += ", ".join(values[:-1]) + " and "
            result += values[-1]
        elif self.operator == ConditionOperator.LessValue:
            result += " is less than " + str(self.values[0])
        elif self.operator == ConditionOperator.GreaterValue:
            result += " is greater than " + str(self.values[0])
        return result
