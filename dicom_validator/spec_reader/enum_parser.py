import re
from typing import Callable, Optional, Dict, List, Any

from pydicom.valuerep import VR, INT_VR, STR_VR

try:
    import lxml.etree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

from dicom_validator.spec_reader.condition import ValuesType


class EnumParser:
    """Parses enumerated values for a tag."""

    docbook_ns = "{http://docbook.org/ns/docbook}"
    enum_with_value_regex = re.compile(r"Enumerated Values for Value (\d):")

    def __init__(
        self, find_section: Callable[[str], Optional[ElementTree.Element]]
    ) -> None:
        self._find_section = find_section
        self._enum_cache: Dict[str, Dict] = {}

    def parse(self, node: ElementTree.Element, vr: VR) -> List[Dict]:
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

    def parse_variable_list(self, var_list) -> Dict:
        # we assume that a variablelist contains enumerated values or defined terms
        # we ignore defined terms, as they do not limit the possible values
        title = var_list.find(self.docbook_ns + "title")
        if title is None:
            return {}
        value_match = self.enum_with_value_regex.match(title.text)
        if value_match:
            index = int(value_match.group(1))
        else:
            index = 0
        if index == 0 and title.text.lower() != "enumerated values:":
            return {}
        # TODO: handle cases with conditions
        terms = []
        for item in var_list.findall(self.docbook_ns + "varlistentry"):
            term = item.find(self.docbook_ns + "term")
            if term is not None:
                terms.append(term.text)
        result: Dict[str, Any] = {}
        if terms:
            result["val"] = terms
            if index > 0:
                result["index"] = index

        return result

    def parse_linked_variablelist(self, node) -> Dict:
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
