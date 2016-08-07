"""
Chapter3Reader collects DICOM Information Object Definition information for specific Storage SOP Classes.
The information is taken from PS3.3 in docbook format as provided by ACR NEMA.
"""
from tools.spec_reader.spec_reader import SpecReader, SpecReaderParseError, SpecReaderLookupError


class Part3Reader(SpecReader):
    """Reads information from PS3.3 in docbook format."""

    def __init__(self, spec_dir):
        super(Part3Reader, self).__init__(spec_dir)
        self._iod_descriptions = {}
        self._iod_nodes = {}

    def iod_description(self, chapter):
        """Return the IOD information for the given chapter.

        The return value is a dict with the entries:
          'title': The display name of the IOD
          'modules': A dictionary of the contained IOD modules with the module name as key.
                     A module dict value has the following entries:
                     'ref': The section in PS3.3 describing the module (e.g. 'C.7.4.2')
                     'use': Usage information (e.g. 'M' for mandatory)
        Raises SpecReaderLookupError if the chapter is not found.
        """
        if chapter not in self._iod_descriptions:
            iod_node = self._get_iod_nodes().get(chapter)
            if iod_node:
                description = self._parse_iod_node(iod_node)
                self._iod_descriptions[chapter] = description
        try:
            return self._iod_descriptions[chapter]
        except KeyError:
            raise SpecReaderLookupError('No definition found for chapter {}'.format(chapter))

    def iod_descriptions(self):
        """Return the IOD information dict per chapter.

        The dict has the chapter (e.g. 'A.3') as key and the IOD descriptions as value.
        See iod_description() for the format of the IOD descriptions.
        Retired IODs (which have no module list) are omitted.
        """
        return {chapter: self.iod_description(chapter) for chapter in self._get_iod_nodes()
                if self.iod_description(chapter)['modules']}

    def _get_iod_nodes(self):
        if not self._iod_nodes:
            chapter_a = self._find(self._get_doc_root(part_number=3), ['chapter[@label="A"]'])
            if chapter_a is None:
                raise SpecReaderParseError('Chapter A in Part 3 not found')
            # ignore A.1
            all_iod_nodes = self._findall(chapter_a, ['section'])[1:]
            iod_def_endings = (
                ' IOD',
                ' Information Object Definition',
                ' Information Objection Definition'  # account for known typo
            )
            for iod_node in all_iod_nodes:
                iod_sub_notes = self._find_sections_with_title_endings(iod_node, iod_def_endings)
                if iod_sub_notes:
                    all_iod_nodes.remove(iod_node)
                    all_iod_nodes.extend(iod_sub_notes)
            self._iod_nodes = {node.attrib['label']: node for node in all_iod_nodes}
        return self._iod_nodes

    def _parse_iod_node(self, iod_node):
        return {'title': self._find(iod_node, ['title']).text,
                'modules': self._get_iod_modules(iod_node)}

    def _get_iod_modules(self, iod_node):
        module_table_sections = self._find_sections_with_title_endings(iod_node, (' Module Table',))
        modules = {}
        if len(module_table_sections) == 1:
            module_rows = self._findall(module_table_sections[0], ['table', 'tbody', 'tr'])
            row_span = 0
            for row in module_rows:
                columns = self._findall(row, ['td'])
                name_index = 0 if row_span > 0 else 1
                if row_span == 0:
                    row_span = int(columns[0].attrib['rowspan'])
                name = self._find(columns[name_index], ['para']).text
                modules[name] = {}
                modules[name]['ref'] = self._find(columns[name_index + 1],
                                                  ['para', 'xref']).attrib['linkend'].split('_')[1]
                modules[name]['use'] = self._find(columns[name_index + 2], ['para']).text
                row_span -= 1
        return modules

    def _find_sections_with_title_endings(self, node, title_endings):
        section_nodes = self._findall(node, ['section'])
        found_nodes = []
        for sections_node in section_nodes:
            title_node = self._find(sections_node, ['title'])
            if title_node is not None:
                title = title_node.text
                if any([title.endswith(title_ending) for title_ending in title_endings]):
                    found_nodes.append(sections_node)
        return found_nodes
