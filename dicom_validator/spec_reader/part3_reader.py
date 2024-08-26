"""
Chapter3Reader collects DICOM Information Object Definition information
for specific Storage SOP Classes.
The information is taken from PS3.3 in docbook format as provided by ACR NEMA.
"""

import logging
from itertools import groupby

import sys
from typing import Dict

from dicom_validator.spec_reader.condition import (
    Condition,
    ConditionType,
    ConditionOperator,
)
from dicom_validator.spec_reader.condition_parser import ConditionParser
from dicom_validator.spec_reader.enum_parser import EnumParser
from dicom_validator.spec_reader.spec_reader import (
    SpecReader,
    SpecReaderParseError,
    SpecReaderLookupError,
)


# Some conditions from the spec are hard to parse with a few general rules.
# Instead of implementing a full parser for these cases, we may define them here.
# CAUTION: The same tag may appear with different conditions in different contexts
# (different sequences), which will not be handled automatically by SPECIAL_CASES
SPECIAL_CASES: Dict[str, Condition] = {}


class Part3Reader(SpecReader):
    """Reads information from PS3.3 in docbook format."""

    def __init__(self, spec_dir, dict_info):
        super(Part3Reader, self).__init__(spec_dir)
        self.part_nr = 3
        self._dict_info = dict_info
        self._iod_descriptions = {}
        self._iod_nodes = {}
        self._module_descriptions = {}
        self._current_refs = []
        self.logger = logging.getLogger()
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self._condition_parser = ConditionParser(self._dict_info)
        self._enum_parser = EnumParser(self.find_section)

    def find_section(self, name):
        return self.get_doc_root().find(f".//{self.docbook_ns}section[@label='{name}']")

    def iod_description(self, chapter):
        """Return the IOD information for the given chapter.

        The return value is a dict with the entries:
            'title': The display name of the IOD
            'modules': A dictionary of the contained IOD modules with the
                module name as key.
                A module dict value has the following entries:
                'ref': The section in PS3.3 describing the module
                    (e.g. 'C.7.4.2')
                'use': Usage information (e.g. 'M' for mandatory)
        Raises SpecReaderLookupError if the chapter is not found.
        """
        if chapter not in self._iod_descriptions:
            iod_node = self._get_iod_nodes().get(chapter)
            if iod_node is not None and len(iod_node) > 0:
                description = self._parse_iod_node(iod_node)
                self._iod_descriptions[chapter] = description
        try:
            return self._iod_descriptions[chapter]
        except KeyError:
            raise SpecReaderLookupError(f"No definition found for chapter {chapter}")

    def iod_descriptions(self):
        """Return the IOD information dict per chapter.

        The dict has the chapter (e.g. 'A.3') as key and the IOD descriptions
         as value.
        See iod_description() for the format of the IOD descriptions.
        Retired IODs (which have no module list) are omitted.
        """
        return {
            chapter: self.iod_description(chapter)
            for chapter in self._get_iod_nodes()
            if self.iod_description(chapter)["modules"]
        }

    def module_description(self, section):
        """Return the module information in the given section.

        The return value is a dict with the entries:
            'title': The name of the module
            'attributes': A dictionary of the contained module attributes
                with the tag as key.
                An attribute dict value has the following entries:
                    'name': the tag name
                    'type': the type (1, 1C, 2, 2C, 3)
                    'items': only for sequence tags - contains a dictionary
                        of the module attributes contained in the sequence
        Raises SpecReaderLookupError if the section is not found.
        """
        if section not in self._module_descriptions:
            section_node = self._get_section_node(section)
            if section_node is not None:
                description = self._parse_module_description(section_node)
                self._module_descriptions[section] = description
        try:
            return self._module_descriptions[section]
        except KeyError:
            raise SpecReaderLookupError(f"No definition found for section {section}")

    def module_descriptions(self):
        """Return the module attribute information for all IODs.

        The return value is a dict with the section name as key and
        a description dict as value.
        See module_description() for the content of the value dict.
        """
        # ensure that all module attributes are read
        self.iod_descriptions()
        return self._module_descriptions

    def _get_iod_nodes(self):
        if not self._iod_nodes:
            chapter_a = self._find(self.get_doc_root(), ['chapter[@label="A"]'])
            if chapter_a is None:
                raise SpecReaderParseError("Chapter A in Part 3 not found")
            # ignore A.1
            all_iod_nodes = self._findall(chapter_a, ["section"])[1:]
            iod_def_endings = (
                " IOD",
                " Information Object Definition",
                " Information Objection Definition",  # account for known typo
            )

            iod_sub_nodes = []
            nodes_with_subnodes = []
            for iod_node in all_iod_nodes:
                sub_nodes = self._find_sections_with_title_endings(
                    iod_node, iod_def_endings
                )
                if sub_nodes:
                    nodes_with_subnodes.append(iod_node)
                    iod_sub_nodes.extend(sub_nodes)
            all_iod_nodes = [
                node for node in all_iod_nodes if node not in nodes_with_subnodes
            ]
            all_iod_nodes.extend(iod_sub_nodes)
            self._iod_nodes = {node.attrib["label"]: node for node in all_iod_nodes}
        return self._iod_nodes

    def _get_section_node(self, section):
        section_parts = section.split(".")
        section_name = section_parts[0]
        search_path = [f'chapter[@label="{section_name}"]']
        for section_part in section_parts[1:]:
            section_name = section_name + "." + section_part
            search_path.append(f'section[@label="{section_name}"]')
        section_node = self._find(self.get_doc_root(), search_path)
        # handle incorrect nesting in specific section
        if (
            section_node is None
            and section_parts[:-1] == ["C", "8", "31"]
            and int(section_parts[-1]) > 6
        ):
            search_path.insert(-1, 'section[@label="C.8.31.6"]')
            section_node = self._find(self.get_doc_root(), search_path)
        return section_node

    def _parse_iod_node(self, iod_node):
        return {
            "title": self._find(iod_node, ["title"]).text,
            "modules": self._get_iod_modules(iod_node),
            "group_macros": self._get_functional_group_macros(iod_node),
        }

    def _parse_module_description(self, parent_node):
        table_node = self._find(parent_node, ["table"])
        # handle the case that the parent node is the table itself
        if table_node is None:
            table_node = parent_node
        table_body_node = self._find(table_node, ["tbody"])
        if table_body_node is None:
            return
        rows = self._findall(table_body_node, ["tr"])
        current_level = 0
        current_descriptions = [{}]
        last_tag_id = None
        for row in rows:
            columns = self._findall(row, ["td"])
            if not columns:
                continue
            tag_name, current_level = self._get_tag_name_and_level(
                columns[0], current_descriptions, current_level, last_tag_id
            )
            if len(columns) == 4:
                last_tag_id = self._handle_regular_attribute(
                    columns, current_descriptions, last_tag_id, tag_name
                )
            elif tag_name.startswith("Include"):
                self._handle_included_attributes(
                    tag_name, columns, current_descriptions
                )
            else:
                # not a valid entry, no need to handle
                pass
        return current_descriptions[0]

    def _handle_included_attributes(self, text, columns, current_descriptions):
        include_node = self._find(columns[0], ["para", "emphasis", "xref"])
        if include_node is None:
            description = self._find_text(columns[0])
            is_func_group = (
                description
                and "Include one or more Functional Group Macros" in description
            )
            if is_func_group:
                # add a placeholder - has to be evaluated at validation time
                current_descriptions[-1].setdefault("include", []).append(
                    {"ref": "FuncGroup"}
                )
            return
        include_ref = include_node.attrib["linkend"]
        if self._current_refs and include_ref == self._current_refs[-1]:
            self.logger.debug("Self reference in %s  - ignoring.", include_ref)
            return
        self._current_refs.append(include_ref)
        element, label = self._get_ref_element_and_label(include_ref)
        if label not in self._module_descriptions:
            ref_node = self._get_ref_node(element, label)
            if ref_node is None:
                raise SpecReaderLookupError(
                    "Failed to lookup include reference " + include_ref
                )
            # it is allowed to have no attributes (example: Raw Data)
            ref_description = self._parse_module_description(ref_node) or {}
            self._module_descriptions[label] = ref_description
        include_attr = {"ref": label}
        # this is currently the only occurring condition for includes
        cond_prefix = "if and only if "
        cond_index = text.find(cond_prefix)
        if cond_index > 0:
            # we replace the prefix to avoid special handling in the parser
            cond_text = text[cond_index:].replace(cond_prefix, "required if ")
            condition = self._condition_parser.parse(cond_text)
            # the parser will put ConditionType.MandatoryOrUserDefined,
            # which makes no sense for includes
            condition.type = ConditionType.MandatoryOrNotAllowed
            include_attr["cond"] = condition
        current_descriptions[-1].setdefault("include", []).append(include_attr)
        self._current_refs.pop()

    def _handle_regular_attribute(
        self, columns, current_descriptions, last_tag_id, tag_name
    ):
        tag_id = self._find_text(columns[1])
        tag_type = self._find_text(columns[2])
        if tag_id:
            current_descriptions[-1][tag_id] = {
                "name": tag_name,
                "type": tag_type,
            }
            if tag_id in SPECIAL_CASES:
                current_descriptions[-1][tag_id]["cond"] = SPECIAL_CASES[tag_id]
            # include type 3 as there may be conditions for not allowed tags
            elif tag_type in ("1C", "2C", "3"):
                cond = self._condition_parser.parse(self._find_all_text(columns[3]))
                if cond.type != ConditionType.UserDefined:
                    # no need to save user defined - it means no condition
                    current_descriptions[-1][tag_id]["cond"] = cond
            info = self._dict_info.get(tag_id)
            if info:
                enum_values = self._enum_parser.parse(columns[3], info["vr"])
                if enum_values:
                    current_descriptions[-1][tag_id]["enums"] = enum_values

            last_tag_id = tag_id
        return last_tag_id

    def _get_ref_node(self, element, label):
        return self._get_doc_tree().find(
            f'.//{self.docbook_ns}{element}[@label="{label}"]'
        )

    @staticmethod
    def _get_ref_element_and_label(ref):
        element, label = ref.split("_")
        if element == "sect":
            element = "section"
        return element, label

    def _get_tag_name_and_level(
        self, column, current_descriptions, current_level, last_tag_id
    ):
        tag_name = self._find_text(column)
        if not tag_name:
            return "", 0
        start_chars = next(groupby(tag_name))
        level = (
            len(list(start_chars[1]))
            if start_chars[0] == ConditionOperator.GreaterValue
            else 0
        )
        tag_name = tag_name[level:]
        if level > current_level:
            sequence_description = {}
            try:
                current_descriptions[-1][last_tag_id]["items"] = sequence_description
                current_descriptions.append(sequence_description)
            except KeyError:
                # silently ignore error in older specs
                pass
        elif level < current_level:
            # Pop off (delete) the last level_delta items.
            level_delta = current_level - level
            del current_descriptions[-level_delta:]
            if not current_descriptions:
                current_descriptions.append({})
        return tag_name, level

    def _collect_modules(self, table_section, check_rowspan):
        modules = {}
        module_rows = self._findall(table_section, ["table", "tbody", "tr"])
        row_span = 0
        for row in module_rows:
            columns = self._findall(row, ["td"])
            if check_rowspan:
                name_index = 0 if row_span > 0 else 1
                if row_span == 0:
                    if "rowspan" in columns[0].attrib:
                        row_span = int(columns[0].attrib["rowspan"])
                    else:
                        row_span = 1
            else:
                name_index = 0
            name = self._find_text(columns[name_index])
            modules[name] = {}
            try:
                ref_section = (
                    self._find(columns[name_index + 1], ["para", "xref"])
                    .attrib["linkend"]
                    .split("_")[1]
                )
            except AttributeError:
                try:
                    ref_section = (
                        self._find(columns[name_index + 1], ["xref"])
                        .attrib["linkend"]
                        .split("_")[1]
                    )
                except AttributeError:
                    self.logger.warning("Failed to read module table for %s", name)
                    continue
            modules[name]["ref"] = ref_section
            # make sure the referenced description is loaded
            self.module_description(ref_section)
            modules[name]["use"] = self._find_text(columns[name_index + 2])
            if len(modules[name]["use"]) > 1:
                modules[name]["cond"] = self._condition_parser.parse(
                    modules[name]["use"]
                )
            row_span -= 1
        return modules

    def _get_iod_modules(self, iod_node):
        module_table_sections = self._find_sections_with_title_endings(
            iod_node, (" Module Table", " IOD Modules")
        )
        if not module_table_sections:
            module_table_sections = self._find_sections_with_title_endings(
                iod_node, ("IOD Entity-Relationship Model",)
            )
        modules = {}
        if len(module_table_sections) == 1:
            modules = self._collect_modules(
                module_table_sections[0], check_rowspan=True
            )
        return modules

    def _get_functional_group_macros(self, iod_node):
        macros = {}
        group_macro_sections = self._find_sections_with_title_endings(
            iod_node, (" Functional Group Macros",)
        )
        if len(group_macro_sections) == 1:
            macros = self._collect_modules(group_macro_sections[0], check_rowspan=False)
        return macros

    def _find_sections_with_title_endings(self, node, title_endings):
        section_nodes = self._findall(node, ["section"])
        found_nodes = []
        for sections_node in section_nodes:
            title_node = self._find(sections_node, ["title"])
            if title_node is not None:
                title = title_node.text
                if any(
                    [title.endswith(title_ending) for title_ending in title_endings]
                ):
                    found_nodes.append(sections_node)
        return found_nodes
