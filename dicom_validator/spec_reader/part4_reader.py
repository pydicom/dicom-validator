"""
Chapter4Reader collects SOP Class Information information for specific
Storage SOP Classes.
The information is taken from PS3.4 in docbook format as provided by ACR NEMA.
"""

from dicom_validator.spec_reader.spec_reader import (
    SpecReader,
    SpecReaderLookupError,
    SpecReaderParseError,
)


class Part4Reader(SpecReader):
    """Reads information from PS3.4 in docbook format."""

    def __init__(self, spec_dir):
        super(Part4Reader, self).__init__(spec_dir)
        self.part_nr = 4
        self._sop_class_uids = {}  # SOP Class UID --> chapter
        self._chapters = {}  # chapter --> SOP Class UID list

    def iod_chapter(self, sop_class_uid):
        """Return the chapter in part 3 for the given SOP Class."""
        if not self._sop_class_uids:
            self._read_sop_table("B.5")  # standard SOP Classes
        try:
            return self._sop_class_uids[sop_class_uid]
        except KeyError:
            raise SpecReaderLookupError(f"SOP Class {sop_class_uid} not found")

    def iod_chapters(self):
        """Return a dict of the chapter in part 3 for each SOP Class
        listed in table B.5.
        """
        if not self._chapters:
            self._read_sop_table("B.5")
        return self._chapters

    def _read_sop_table(self, chapter):
        table = self._find(
            self.get_doc_root(),
            ['chapter[@label="B"]', f'section[@label="{chapter}"]', "table", "tbody"],
        )
        if table is None:
            raise SpecReaderParseError("SOP Class table in Part 4 not found")
        row_nodes = self._findall(table, ["tr"])
        for row_node in row_nodes:
            column_nodes = self._findall(row_node, ["td"])
            if len(column_nodes) in (3, 4):
                # columns are SOP Class Name, SOP Class UID, IOD Specification
                # and Specialization (only since 2020c)
                uid = self.cleaned_value(self._find_text(column_nodes[1]))
                target_node = self._find(column_nodes[2], ["para", "olink"])
                if target_node is not None:
                    chapter = target_node.attrib["targetptr"].split("_")[1]
                    self._sop_class_uids[uid] = chapter
                    self._chapters.setdefault(chapter, []).append(uid)
        self._patch_incorrect_values()

    def _patch_incorrect_values(self):
        sc_sop_class_uid = "1.2.840.10008.5.1.4.1.1.7"
        if self._sop_class_uids.get(sc_sop_class_uid, "") == "A.8":
            self._sop_class_uids[sc_sop_class_uid] = "A.8.1"
            self._chapters["A.8.1"] = [sc_sop_class_uid]
            del self._chapters["A.8"]
