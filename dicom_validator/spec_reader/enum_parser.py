from typing import Callable, Optional, Dict

from pydicom.valuerep import VR, INT_VR, STR_VR

try:
    import lxml.etree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

from dicom_validator.spec_reader.condition import ValuesType


class EnumParser:
    """Parses enumerated values for a tag."""

    docbook_ns = "{http://docbook.org/ns/docbook}"
    nr_direct_enums = 0
    nr_linked_enums = 0

    def __init__(
        self, find_section: Callable[[str], Optional[ElementTree.Element]]
    ) -> None:
        self._find_section = find_section
        self._enum_cache: Dict[str, ValuesType] = {}

    def parse(self, node: ElementTree.Element, vr: VR) -> ValuesType:
        """Searches for enumerated values in the tag description and in linked sections.
        Returns a list of the allowed values, or an empty list if none found.
        """
        var_list = node.find(self.docbook_ns + "variablelist")
        if var_list is not None:
            enums = self.parse_variable_list(var_list)
        else:
            enums = self.parse_linked_variablelist(node)
        if enums:
            if vr == VR.AT:
                # print(
                #     f"Ignoring enum values: "
                #     f"{', '.join([str(e) for e in enums])} with VR {vr}"
                # )
                return []  # this is included in INT_VRs, but won't work
            if vr in INT_VR:
                int_enums: ValuesType = []
                for e in enums:
                    assert isinstance(e, str)
                    if e.endswith("H"):
                        int_enums.append(int(e[:-1], 16))
                    else:
                        int_enums.append(int(e))
                self.__class__.nr_direct_enums += 1
                return int_enums
            if vr in STR_VR:
                self.__class__.nr_direct_enums += 1
                return enums
            # any other VR does not make sense here
            # print(
            #     f"Ignoring enum values: "
            #     f"{', '.join([str(e) for e in enums])} with VR {vr}"
            # )
        return []

    def parse_variable_list(self, var_list) -> ValuesType:
        # we assume that a variablelist contains enumerated values or defined terms
        # we ignore defined terms, as they do not limit the possible values
        title = var_list.find(self.docbook_ns + "title")
        # TODO: handle cases with conditions
        if title is None or title.text.lower() not in ("enumerated values:",):
            return []
        terms = []
        for item in var_list.findall(self.docbook_ns + "varlistentry"):
            term = item.find(self.docbook_ns + "term")
            if term is not None:
                terms.append(term.text)
        return terms

    def parse_linked_variablelist(self, node) -> ValuesType:
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
                        if self._enum_cache[link]:
                            self.__class__.nr_linked_enums += 1
                            # print("LINK:", link, self._enum_cache[link])
                        return self._enum_cache[link]
        return []
