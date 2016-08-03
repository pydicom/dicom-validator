"""
Chapter6Reader collects DICOM Data Element information.
The information is taken from DICOM dictionary (PS3.6) in docbook format as provided by ACR NEMA.
"""
from tools.spec_reader.spec_reader import SpecReader, SpecReaderParseError


class Part6Reader(SpecReader):
    def __init__(self, spec_dir):
        super(Part6Reader, self).__init__(spec_dir)
        self._data_elements = {}

    def data_elements(self):
        if not self._data_elements:
            self._read_element_table()
        return self._data_elements

    def data_element(self, group, element):
        tag_id = (group, element)
        return self.data_elements().get(tag_id)

    def _read_element_table(self):
        table = self._find(self._get_doc_root(part_number=6),
                           ['chapter[@label="6"]', 'table', 'tbody'])
        if table is None:
            raise SpecReaderParseError('Data Element Registry table in Part 6 not found')
        row_nodes = self._findall(table, ['tr'])
        attrib_indexes = [1, 3, 4, 5]
        for row_node in row_nodes:
            column_nodes = self._findall(row_node, ['td'])
            if len(column_nodes) == 6:
                tag_attributes = None
                tag_ids = self._find_text(column_nodes[0])[1:-1].split(',')
                if len(tag_ids) == 2:
                    tag_attributes = [self._find_text(column_nodes[i]) for i in attrib_indexes]
                if tag_attributes is not None:
                    try:
                        tag_id = (int(tag_ids[0], base=16), int(tag_ids[1], base=16))
                        self._data_elements[tag_id] = {
                            'name': tag_attributes[0],
                            'vr': tag_attributes[1],
                            'vm': tag_attributes[2],
                            'prop': tag_attributes[3]
                        }
                    except ValueError:
                        # special handling for tags like 60xx needed
                        pass

    def _find_text(self, node):
        try:
            text = self._find(node, ['para']).text
            if text and text.strip():
                return text.strip()
        except AttributeError:
            pass
        try:
            text = self._find(node, ['para', 'emphasis']).text
            if text and text.strip():
                return text.strip()
        except AttributeError:
            return ''
