"""
SpecReader reads information from DICOM standard files in docbook format as
provided by ACR-NEMA.
"""
import os

import xml.etree.ElementTree as ElementTree


class SpecReaderError(Exception):
    pass


class SpecReaderFileError(SpecReaderError):
    pass


class SpecReaderParseError(SpecReaderError):
    pass


class SpecReaderLookupError(SpecReaderError):
    pass


class SpecReader:
    docbook_ns = '{http://docbook.org/ns/docbook}'

    def __init__(self, spec_dir):
        self.spec_dir = spec_dir
        self.part_nr = 0
        document_files = os.listdir(self.spec_dir)
        if not document_files:
            raise SpecReaderFileError(
                'Missing docbook files in {}'.format(self.spec_dir))
        self._doc_trees = {}

    def _get_doc_tree(self):
        if self.part_nr not in self._doc_trees:
            doc_name = 'part{:02}.xml'.format(self.part_nr)
            document_files = os.listdir(self.spec_dir)
            if doc_name not in document_files:
                raise SpecReaderFileError(
                    'Missing docbook file {} in {}'.format(
                        doc_name, self.spec_dir))
            try:
                self._doc_trees[self.part_nr] = ElementTree.parse(
                    os.path.join(self.spec_dir, doc_name))
            except ElementTree.ParseError:
                raise SpecReaderFileError(
                    'Parse error in docbook file {} in {}'.format(
                        doc_name, self.spec_dir))
        return self._doc_trees.get(self.part_nr)

    def _get_doc_root(self):
        doc_tree = self._get_doc_tree()
        if doc_tree:
            return doc_tree.getroot()

    def _find(self, node, elements):
        search_string = '/'.join(
            [self.docbook_ns + element for element in elements])
        if node is not None:
            return node.find(search_string)

    def _findall(self, node, elements):
        search_string = '/'.join(
            [self.docbook_ns + element for element in elements])
        return node.findall(search_string)

    def _find_text(self, node):
        try:
            para_node = self._find(node, ['para'])
            text_parts = [text.strip() for text in para_node.itertext() if
                          text.strip()]
            return ' '.join(text_parts) if text_parts else ''
        except AttributeError:
            return ''

    @staticmethod
    def cleaned_value(value):
        return value.replace('\u200B', '')

    @staticmethod
    def _find_all_text(node):
        text_parts = [text.strip() for text in node.itertext() if text.strip()]
        return ' '.join(text_parts) if text_parts else ''
