import re

from collections.abc import Callable
from typing import Optional

from pydicom.valuerep import VR, INT_VR, STR_VR

from dicom_validator.spec_reader.condition_parser import ConditionParser

try:
    import lxml.etree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

from dicom_validator.spec_reader.condition import ValuesType, ConditionType, Condition

OptionalElement = Optional[ElementTree.Element]


class EnumParser:
    """Parses enumerated values for a tag."""

    docbook_ns = "{http://docbook.org/ns/docbook}"
    enum_with_value_regex = re.compile(r"Enumerated Values for Value (\d):")
    enum_values_regex = re.compile(
        r"[Ee]numerated [Vv]alues( (for|of) [A-Za-z0-9 ]+"
        r"\([0-9A-Fa-f]{4},[0-9A-Fa-f]{4}\))?( (if|when) ([^:]*))?:?$"
    )

    def __init__(
        self,
        find_section: Callable[[str], OptionalElement],
        condition_parser: ConditionParser,
    ) -> None:
        self._find_section = find_section
        self._condition_parser = condition_parser
        self._enum_cache: dict[str, dict] = {}

    def parse(self, node: ElementTree.Element, vr: VR) -> list[dict]:
        """Searches for enumerated values in the tag description and in linked sections.
        Returns a list of the allowed values, or an empty list if none found.
        """
        var_lists = node.findall(self.docbook_ns + "variablelist")
        enum_lists = [self.parse_variable_list(e) for e in var_lists]
        enum_lists = [e for e in enum_lists if e]
        if not enum_lists:
            enums = self.parse_linked_variablelist(node)
            if enums:
                enum_lists.append(enums)

        if enum_lists:
            if vr == VR.AT:
                return []  # this is included in INT_VRs, but won't work
            if vr in INT_VR:
                for enums in enum_lists:
                    int_enums: ValuesType = []
                    for e in enums["val"]:
                        if isinstance(e, str):
                            if e.endswith("H"):
                                int_enums.append(int(e[:-1], 16))
                            else:
                                int_enums.append(int(e))
                        else:
                            int_enums.append(e)
                    enums["val"] = int_enums
                return enum_lists
            if vr in STR_VR:
                return enum_lists
            # any other VR does not make sense here
        return []

    def parse_variable_list(self, var_list) -> dict:
        """Parse a DocBook `variablelist` for enumerated values.

        Parameters
        ----------
        var_list : Element
            A DocBook `variablelist` element.

        Returns
        -------
        dict
            A dictionary with keys `val` (list of values) and optional `index`
            when the list applies to a specific value position; otherwise empty.
        """
        # we assume that a variablelist contains enumerated values or defined terms
        # we ignore defined terms, as they do not limit the possible values
        title = var_list.find(self.docbook_ns + "title")
        if title is None:
            return {}
        index = 0
        match = self.enum_values_regex.match(title.text)
        if not match:
            value_match = self.enum_with_value_regex.match(title.text)
            if value_match:
                index = int(value_match.group(1))
            else:
                return {}
        condition = None
        if match and (cond := match.group(5)) is not None:
            condition = self._condition_parser.parse("Required if " + cond)
            if condition.type == ConditionType.UserDefined:
                condition = None
        terms = []
        for item in var_list.findall(self.docbook_ns + "varlistentry"):
            term = item.find(self.docbook_ns + "term")
            if term is not None:
                terms.append(term.text)
        result: dict[str, list[str] | int | Condition] = {}
        if terms:
            result["val"] = terms
            if index > 0:
                result["index"] = index
            if condition is not None:
                result["cond"] = condition

        return result

    def parse_linked_variablelist(self, node) -> dict:
        """Follow `xref` links to a section containing enumerated values.

        Parameters
        ----------
        node : Element
            DocBook element whose paragraph may contain `xref` pointers to
            a section with a `variablelist` of enumerated values.

        Returns
        -------
        dict
            Parsed enumerated values dictionary as returned by
            `parse_variable_list`, or empty dict if none found.
        """
        for xref in node.findall(f"{self.docbook_ns}para/{self.docbook_ns}xref"):
            link = xref.attrib.get("linkend")
            if link and link.startswith("sect_"):
                if link in self._enum_cache:
                    return self._enum_cache[link]
                section = self._find_section(link[5:])
                if section is not None:
                    var_list = section.find(f"{self.docbook_ns}variablelist")
                    if var_list is not None:
                        self._enum_cache[link] = self.parse_variable_list(var_list)
                        return self._enum_cache[link]
        return {}
