"""
Chapter6Reader collects DICOM Data Element information.
The information is taken from DICOM dictionary (PS3.6) in docbook format
as provided by ACR NEMA.
"""

from dicom_validator.spec_reader.spec_reader import SpecReader, SpecReaderParseError


class Part6Reader(SpecReader):
    """Reads information from PS3.4 in docbook format."""

    def __init__(self, spec_dir):
        super(Part6Reader, self).__init__(spec_dir)
        self.part_nr = 6
        self._uids = None
        self._data_elements = None

    def data_elements(self):
        """Return the information about registered DICOM data elements.

        The return value is a dict with the tag ID (group/element tuple)
        as key.
        See data_element() for the contained value.
        """
        if self._data_elements is None:
            self._read_element_table()
        return self._data_elements

    def data_element(self, tag_id):
        """Return the information about the specified tag.

        Arguments:
            tag_id: The tag ID as string in format (####,####)
        The return value is a dict with the tag ID (group/element tuple)
        as key.
        The values of the returned dict are dicts with the following entries:
            'name': The human-readable tag name
            'vr': The tag value representation (e.g. 'ON')
            'vm': The tag multiplicity (e.g. '1-N')
            'prop': Additional properties, like 'RET' for retired
        """
        return self.data_elements().get(tag_id)

    def _read_element_table(self):
        self._data_elements = {}
        table = self._find(
            self.get_doc_root(), ['chapter[@label="6"]', "table", "tbody"]
        )
        if table is None:
            raise SpecReaderParseError(
                "Registry of DICOM Data Elements not found in PS3.6"
            )
        row_nodes = self._findall(table, ["tr"])
        attrib_indexes = [1, 3, 4, 5]
        for row_node in row_nodes:
            column_nodes = self._findall(row_node, ["td"])
            if len(column_nodes) == 6:
                tag_id = self._find_text(column_nodes[0])
                if tag_id:
                    tag_attributes = [
                        self._find_text(column_nodes[i]) for i in attrib_indexes
                    ]
                    if tag_attributes is not None:
                        self._data_elements[tag_id] = {
                            "name": tag_attributes[0],
                            "vr": tag_attributes[1],
                            "vm": tag_attributes[2],
                            "prop": tag_attributes[3],
                        }

    def uids(self, uid_type):
        """Return a dict of UID values (keys) and names for the given UID type."""
        return self._get_uids().get(uid_type, {})

    def all_uids(self):
        """Return a dict of UID types with UID value/name dicts for the
        given UID type as value.
        """
        return self._get_uids()

    def sop_class_uids(self):
        """Return a dict of SOP Class UID values (keys) and names."""
        return self.uids("SOP Class")

    def sop_class_name(self, uid):
        """Return the name of SOP Class corresponding to the given UID."""
        return self.uids("SOP Class").get(uid)

    def sop_class_uid(self, sop_class_name):
        """Return the name of SOP Class corresponding to the given UID."""
        for uid, name in self.sop_class_uids().items():
            if name == sop_class_name:
                return uid

    def _get_uids(self):
        if self._uids is None:
            self._uids = {}
            table = self._find(
                self.get_doc_root(), ['chapter[@label="A"]', "table", "tbody"]
            )
            if table is None:
                raise SpecReaderParseError(
                    "Registry of DICOM Unique Identifiers not found in PS3.6"
                )

            row_nodes = self._findall(table, ["tr"])
            for row_node in row_nodes:
                column_nodes = self._findall(row_node, ["td"])
                nr_columns = len(column_nodes)
                if nr_columns in (4, 5):
                    # columns are UID Value, UID Name, UID Keyword (only
                    # since 2020d), UID Type and Part
                    uid_attributes = [
                        self._find_text(column_nodes[i]) for i in range(nr_columns - 1)
                    ]
                    if uid_attributes is not None:
                        uid_type = uid_attributes[nr_columns - 2]
                        # in PS3.6 xml there are multiple zero width (U+200B)
                        # spaces inside the UIDs
                        # we remove them hoping this is the only such problem
                        uid_value = self.cleaned_value(uid_attributes[0])
                        self._uids.setdefault(uid_type, {})[uid_value] = (
                            self.cleaned_value(uid_attributes[1])
                        )
        return self._uids
