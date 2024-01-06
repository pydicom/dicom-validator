"""
SpecReader reads information from DICOM standard files in docbook format as
provided by ACR-NEMA.
"""

try:
    import lxml.etree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree
from pathlib import Path


class SpecReaderError(Exception):
    pass


class SpecReaderFileError(SpecReaderError):
    pass


class SpecReaderParseError(SpecReaderError):
    pass


class SpecReaderLookupError(SpecReaderError):
    pass


class SpecReader:
    docbook_ns = "{http://docbook.org/ns/docbook}"

    def __init__(self, spec_dir):
        self.spec_dir = Path(spec_dir)
        self.part_nr = 0
        if not list(self.spec_dir.iterdir()):
            raise SpecReaderFileError(f"Missing docbook files in {self.spec_dir}")
        self._doc_trees = {}

    def _get_doc_tree(self):
        if self.part_nr not in self._doc_trees:
            doc_name = self.spec_dir / f"part{self.part_nr:02}.xml"
            if doc_name not in self.spec_dir.iterdir():
                raise SpecReaderFileError(f"Missing docbook file {doc_name}")
            try:
                self._doc_trees[self.part_nr] = ElementTree.parse(doc_name)
            except ElementTree.ParseError as e:
                raise SpecReaderFileError(
                    f"Parse error in docbook file {doc_name}: {e}"
                )
        return self._doc_trees.get(self.part_nr)

    def get_doc_root(self):
        doc_tree = self._get_doc_tree()
        if doc_tree:
            return doc_tree.getroot()

    def _find(self, node, elements):
        search_string = "/".join([self.docbook_ns + element for element in elements])
        if node is not None:
            return node.find(search_string)

    def _findall(self, node, elements):
        search_string = "/".join([self.docbook_ns + element for element in elements])
        return node.findall(search_string)

    def _find_text(self, node):
        try:
            para_node = self._find(node, ["para"])
            text_parts = [text.strip() for text in para_node.itertext() if text.strip()]
            return " ".join(text_parts) if text_parts else ""
        except AttributeError:
            return ""

    @staticmethod
    def cleaned_value(value):
        return value.replace("\u200B", "")

    @staticmethod
    def _find_all_text(node):
        text_parts = [text.strip() for text in node.itertext() if text.strip()]
        return " ".join(text_parts) if text_parts else ""
