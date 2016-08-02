"""
SpecReader raeds information from DICOM standard files in docbook format as provided by ACR NEMA.
"""
import os

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree


class SpecReaderError(Exception):
    pass


class SpecReaderFileError(SpecReaderError):
    pass


class SpecReaderParseError(SpecReaderError):
    pass


class SpecReaderLookupError(SpecReaderError):
    pass


class SpecReader(object):
    docbook_ns = '{http://docbook.org/ns/docbook}'

    def __init__(self, spec_dir):
        self.spec_dir = spec_dir
        document_files = os.listdir(self.spec_dir)
        if not document_files:
            raise SpecReaderFileError(u'Missing docbook files in {}'.format(self.spec_dir))
        self._doc_roots = {}

    def _get_doc_root(self, part_number):
        if part_number not in self._doc_roots:
            doc_name = 'part{:02}.xml'.format(part_number)
            document_files = os.listdir(self.spec_dir)
            if doc_name not in document_files:
                raise SpecReaderFileError(u'Missing docbook file {} in {}'.format(doc_name, self.spec_dir))
            try:
                self._doc_roots[part_number] = ElementTree.parse(os.path.join(self.spec_dir, doc_name)).getroot()
            except ElementTree.ParseError:
                raise SpecReaderFileError(u'Parse error in docbook file {} in {}'.format(doc_name, self.spec_dir))

        return self._doc_roots.get(part_number)

    def _find(self, node, elements):
        search_string = '/'.join([self.docbook_ns + element for element in elements])
        return node.find(search_string)

    def _findall(self, node, elements):
        search_string = '/'.join([self.docbook_ns + element for element in elements])
        return node.findall(search_string)
