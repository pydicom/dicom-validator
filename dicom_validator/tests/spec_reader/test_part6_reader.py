from pathlib import Path

import pytest

from dicom_validator.spec_reader.part6_reader import Part6Reader


@pytest.fixture(scope="module")
def doc_contents(spec_fixture_path):
    with open(spec_fixture_path / "part06.xml", "rb") as spec_file:
        contents = spec_file.read()
    yield contents


@pytest.fixture
def reader(fs, doc_contents):
    spec_path = Path("dicom", "docbook")
    part6_path = spec_path / "part06.xml"
    fs.create_file(part6_path, contents=doc_contents)
    yield Part6Reader(spec_path)


@pytest.mark.usefixtures("fs")
class TestPart6Reader:
    def test_undefined_id(self, reader):
        assert reader.data_element("(0011,0011)") is None

    def test_data_element(self, reader):
        element = reader.data_element("(0008,0005)")
        assert element is not None
        assert element["name"] == "Specific Character Set"
        assert element["vr"] == "CS"
        assert element["vm"] == "1-n"

    def test_data_elements(self, reader):
        elements = reader.data_elements()
        assert len(elements) == 8

    def test_sop_class_uids(self, reader):
        sop_class_uids = reader.sop_class_uids()
        assert len(sop_class_uids) == 3
        assert "1.2.840.10008.1.1" in sop_class_uids
        assert sop_class_uids["1.2.840.10008.1.1"] == "Verification SOP Class"

    def test_uid_type(self, reader):
        xfer_syntax_uids = reader.uids("Transfer Syntax")
        assert len(xfer_syntax_uids) == 2
        assert "1.2.840.10008.1.2.4.80" in xfer_syntax_uids
        assert (
            xfer_syntax_uids["1.2.840.10008.1.2.4.80"]
            == "JPEG-LS Lossless Image Compression"
        )

    def test_all_uids(self, reader):
        uids = reader.all_uids()
        assert len(uids) == 2
        assert "Transfer Syntax" in uids
        assert "SOP Class" in uids
        uid_nr = sum([len(uid_dict) for uid_dict in uids.values()])
        assert uid_nr == 5

    def test_sop_class_name(self, reader):
        assert (
            reader.sop_class_name("1.2.840.10008.5.1.4.1.1.6.2")
            == "Enhanced US Volume Storage"
        )

    def test_sop_class_uid(self, reader):
        assert reader.sop_class_uid("CT Image Storage") == "1.2.840.10008.5.1.4.1.1.2"
