from xml.etree import ElementTree
from pathlib import Path
from unittest.mock import patch

import pytest

from dicom_validator.spec_reader.part4_reader import Part4Reader
from dicom_validator.spec_reader.spec_reader import (
    SpecReaderLookupError,
    SpecReaderParseError,
)


@pytest.fixture(scope="module")
def doc_contents(spec_fixture_path):
    with open(spec_fixture_path / "part04.xml", "rb") as spec_file:
        contents = spec_file.read()
    yield contents


@pytest.fixture
def reader(fs, doc_contents):
    spec_path = Path("dicom", "specs")
    part3_path = spec_path / "part04.xml"
    fs.create_file(part3_path, contents=doc_contents)
    yield Part4Reader(spec_path)


@pytest.mark.usefixtures("fs")
@patch("dicom_validator.spec_reader.spec_reader.ElementTree", ElementTree)
class TestPart4Reader:
    def test_read_incomplete_doc_file(self, fs):
        spec_path = Path("/var/dicom/specs")
        spec_path.mkdir(parents=True)
        fs.create_file(
            spec_path / "part04.xml",
            contents='<book xmlns="http://docbook.org/ns/docbook">\n</book>',
        )
        reader = Part4Reader(spec_path)
        with pytest.raises(SpecReaderParseError):
            reader.iod_chapter("1.2.840.10008.5.1.4.1.1.2")

    def test_sop_class_lookup(self, reader):
        with pytest.raises(SpecReaderLookupError):
            reader.iod_chapter("1.1.1.1")
        iod_chapter = reader.iod_chapter(sop_class_uid="1.2.840.10008.5.1.4.1.1.2")
        assert iod_chapter == "A.3"

    def test_uids_for_chapter(self, reader):
        iod_chapters = reader.iod_chapters()
        assert "A.3" in iod_chapters
        assert len(iod_chapters["A.3"]) == 1
        assert "A.26" in iod_chapters
        assert "1.2.840.10008.5.1.4.1.1.2" in iod_chapters["A.3"]
        assert "A.26" in iod_chapters
        assert len(iod_chapters["A.26"]) == 2
        assert "1.2.840.10008.5.1.4.1.1.1.1" in iod_chapters["A.26"]
        assert "1.2.840.10008.5.1.4.1.1.1.1.1" in iod_chapters["A.26"]

    def test_secondary_capture_fix(self, reader):
        iod_chapter = reader.iod_chapter(sop_class_uid="1.2.840.10008.5.1.4.1.1.7")
        assert iod_chapter == "A.8.1"
