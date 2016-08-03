"""
Cahpter4Reader collects SOP Class Information information for specific Storage SOP Classes.
The information is taken from PS3.4 in docbook format as provided by ACR NEMA.
"""
from spec_reader import SpecReader, SpecReaderLookupError, SpecReaderParseError


class Part4Reader(SpecReader):
    def __init__(self, spec_dir):
        super(Part4Reader, self).__init__(spec_dir)
        self._sop_class_uids = {}

    def iod_chapter(self, sop_class_uid):
        """ Returns the chapter in part 3 for the given SOP Class """
        if not self._sop_class_uids:
            self._read_sop_table('B.5')  # standard SOP Classes
        try:
            return self._sop_class_uids[sop_class_uid]
        except KeyError:
            raise SpecReaderLookupError('SOP Class {} not found'.format(sop_class_uid))

    def iod_chapters(self):
        """ Returns the chapter in part 3 for each SOP Class listed in table B.5 """
        if not self._sop_class_uids:
            self._read_sop_table('B.5')
        return self._sop_class_uids

    def _read_sop_table(self, chapter):
        table = self._find(self._get_doc_root(part_number=4),
                           ['chapter[@label="B"]', 'section[@label="{}"]'.format(chapter), 'table', 'tbody'])
        if table is None:
            raise SpecReaderParseError('SOP Class table in Part 4 not found')
        row_nodes = self._findall(table, ['tr'])
        for row_node in row_nodes:
            column_nodes = self._findall(row_node, ['td'])
            if len(column_nodes) == 3:
                uid = self._find(column_nodes[1], ['para']).text
                target_node = self._find(column_nodes[2], ['para', 'olink'])
                if target_node is not None:
                    chapter = target_node.attrib['targetptr'].split('_')[1]
                    self._sop_class_uids[uid] = chapter

    def _read_all_table(self, chapter):
        table = self._find(self._get_doc_root(part_number=4),
                           ['chapter[@label="B"]', 'section[@label="{}"]'.format(chapter), 'table', 'tbody'])
        if table is None:
            raise SpecReaderParseError('SOP Class table in Part 4 not found')
        row_nodes = self._findall(table, ['tr'])
        for row_node in row_nodes:
            column_nodes = self._findall(row_node, ['td'])
            if len(column_nodes) == 3:
                uid = self._find(column_nodes[1], ['para']).text
                target_node = self._find(column_nodes[2], ['para', 'olink'])
                if target_node is not None:
                    chapter = target_node.attrib['targetptr'].split('_')[1]
                    self._sop_class_uids[uid] = chapter
