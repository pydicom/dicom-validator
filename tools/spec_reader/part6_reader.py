"""
Cahpter6Reader collects DICOM Data Element information.
The information is taken from DICOM dictionary (PS3.6) in docbook format as provided by ACR NEMA.
"""
from spec_reader.spec_reader import SpecReader, SpecReaderParseError


class Part6Reader(SpecReader):
    def __init__(self, spec_dir):
        super(Part6Reader, self).__init__(spec_dir)
        self._data_elements = {}

    def data_elements(self):
        if not self._data_elements:
            self._read_element_table()
        return self._data_elements

    def data_element(self, group, id):
        tag_id = (group, id)
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
                tag_attribs = None
                tag_ids = self._find(column_nodes[0], ['para']).text[1:-1].split(',')
                if len(tag_ids) == 2:
                    tag_attribs = [self._find(column_nodes[i], ['para']).text for i in attrib_indexes]
                else:
                    tag_ids = self._find(column_nodes[0], ['para', 'emphasis']).text[1:-1].split(',')
                    if len(tag_ids) == 2:
                        tag_attribs = [self._find(column_nodes[i], ['para', 'emphasis']).text for i in attrib_indexes]
                if tag_attribs is not None:
                    tag_id = (int(tag_ids[0]), int(tag_ids[1]))
                    self._data_elements[tag_id] = {
                        'name': tag_attribs[0],
                        'vr': tag_attribs[1],
                        'vm': tag_attribs[2],
                        'prop': tag_attribs[3]
                    }
