"""
SpecReader reads information from DICOM standard files in docbook format as
provided by ACR-NEMA.
"""

from typing import Optional

try:
    import lxml.etree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree
from pathlib import Path

OptionalElement = Optional[ElementTree.Element]


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

    def __init__(self, spec_dir: str | Path) -> None:
        """Initialize a reader for DICOM standard DocBook files.

        Parameters
        ----------
        spec_dir : str | pathlib.Path
            Directory containing the DocBook XML files (e.g., `part03.xml`).

        Raises
        ------
        SpecReaderFileError
            If the provided directory is empty.
        """
        self.spec_dir = Path(spec_dir)
        self.part_nr: int = 0
        if not list(self.spec_dir.iterdir()):
            raise SpecReaderFileError(f"Missing docbook files in {self.spec_dir}")
        self._doc_trees: dict[int, ElementTree.ElementTree] = {}

    def _get_doc_tree(self) -> ElementTree.ElementTree:
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

    def get_doc_root(self) -> OptionalElement:
        """Return the XML root element of the current part, or `None` if unavailable."""
        doc_tree = self._get_doc_tree()
        if doc_tree:
            return doc_tree.getroot()
        return None

    def _find(self, node: ElementTree.Element, elements: list[str]) -> OptionalElement:
        search_string = "/".join([self.docbook_ns + element for element in elements])
        if node is not None:
            return node.find(search_string)
        return None

    def _findall(
        self, node: ElementTree.Element, elements: list[str]
    ) -> list[ElementTree.Element]:
        search_string = "/".join([self.docbook_ns + element for element in elements])
        return node.findall(search_string)

    def _find_text(self, node: ElementTree.Element) -> str:
        try:
            para_node = self._find(node, ["para"])
            if para_node is not None:
                text_parts = [
                    text.strip() for text in para_node.itertext() if text.strip()
                ]
                return " ".join(text_parts) if text_parts else ""
            return ""
        except AttributeError:
            return ""

    @staticmethod
    def cleaned_value(value: str) -> str:
        """Return `value` with zero-width space (U+200B) characters removed."""
        return value.replace("\u200b", "")

    @staticmethod
    def _find_all_text(node: ElementTree.Element) -> str:
        text_parts = [text.strip() for text in node.itertext() if text.strip()]
        return " ".join(text_parts) if text_parts else ""
