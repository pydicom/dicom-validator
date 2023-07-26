from pathlib import Path

import pytest

from dicom_validator.spec_reader.spec_reader import SpecReader, SpecReaderFileError

pytestmark = pytest.mark.usefixtures("fs")


def test_missing_path():
    spec_path = "/var/dicom/specs"
    with pytest.raises(OSError):
        SpecReader(spec_path)


def test_missing_doc_files(fs):
    spec_path = Path("/var/dicom/specs")
    spec_path.mkdir(parents=True)
    fs.create_file("notadoc.xml")
    with pytest.raises(SpecReaderFileError):
        SpecReader(spec_path)


def test_existing_doc_files(fs):
    spec_path = Path("/var/dicom/specs")
    spec_path.mkdir(parents=True)
    fs.create_file(spec_path / "part03.xml")
    assert SpecReader(spec_path)


def test_cleaned_uid():
    orig_value = "1.2.840.10008.5." "\u200b1.\u200b4.\u200b1.\u200b1.\u200b88.\u200b72"
    assert SpecReader.cleaned_value(orig_value) == "1.2.840.10008.5.1.4.1.1.88.72"
