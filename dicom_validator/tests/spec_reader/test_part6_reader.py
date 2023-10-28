import pytest


@pytest.mark.usefixtures("fs")
class TestPart6Reader:
    def test_undefined_id(self, dict_reader):
        assert dict_reader.data_element("(0011,0011)") is None

    def test_data_element(self, dict_reader):
        element = dict_reader.data_element("(0008,0005)")
        assert element is not None
        assert element["name"] == "Specific Character Set"
        assert element["vr"] == "CS"
        assert element["vm"] == "1-n"

    def test_data_elements(self, dict_reader):
        elements = dict_reader.data_elements()
        assert len(elements) == 5063

    def test_sop_class_uids(self, dict_reader):
        sop_class_uids = dict_reader.sop_class_uids()
        assert len(sop_class_uids) == 301
        assert "1.2.840.10008.1.1" in sop_class_uids
        assert sop_class_uids["1.2.840.10008.1.1"] == "Verification SOP Class"

    def test_uid_type(self, dict_reader):
        xfer_syntax_uids = dict_reader.uids("Transfer Syntax")
        assert len(xfer_syntax_uids) == 54
        assert "1.2.840.10008.1.2.4.80" in xfer_syntax_uids
        assert (
            xfer_syntax_uids["1.2.840.10008.1.2.4.80"]
            == "JPEG-LS Lossless Image Compression"
        )

    def test_all_uids(self, dict_reader):
        uids = dict_reader.all_uids()
        assert len(uids) == 12
        assert "Transfer Syntax" in uids
        assert "SOP Class" in uids
        uid_nr = sum([len(uid_dict) for uid_dict in uids.values()])
        assert uid_nr == 446

    def test_sop_class_name(self, dict_reader):
        assert (
            dict_reader.sop_class_name("1.2.840.10008.5.1.4.1.1.6.2")
            == "Enhanced US Volume Storage"
        )

    def test_sop_class_uid(self, dict_reader):
        assert (
            dict_reader.sop_class_uid("CT Image Storage") == "1.2.840.10008.5.1.4.1.1.2"
        )
