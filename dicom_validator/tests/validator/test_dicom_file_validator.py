import os
from pathlib import Path

import pytest
from pydicom import dcmwrite
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset

from dicom_validator.validator.dicom_file_validator import DicomFileValidator

pytestmark = pytest.mark.usefixtures("disable_logging")


@pytest.fixture
def validator(dicom_info):
    yield DicomFileValidator(dicom_info)


@pytest.fixture(scope="module")
def dicom_fixture_path():
    yield Path(__file__).parent.parent / "fixtures" / "dicom"


@pytest.mark.usefixtures("fs")
class TestFakeDicomFileValidator:
    @staticmethod
    def create_metadata():
        metadata = FileMetaDataset()
        metadata.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        metadata.MediaStorageSOPInstanceUID = "1.2.3"
        metadata.TransferSyntaxUID = "1.2.840.10008.1.2"
        metadata.ImplementationClassUID = "1.3.6.1.4.1.5962.2"
        return metadata

    def assert_fatal_error(self, validator, filename, error_string):
        error_dict = validator.validate(filename)
        assert len(error_dict) == 1
        name = list(error_dict.keys())[0]
        assert filename == name
        errors = error_dict[name]
        assert errors == {"fatal": error_string}

    def test_non_existing_file(self, validator):
        self.assert_fatal_error(validator, "non_existing", error_string="File missing")

    def test_invalid_file(self, fs, validator):
        fs.create_file("test", contents="invalid")
        self.assert_fatal_error(validator, "test", error_string="Invalid DICOM file")

    def test_missing_sop_class(self, validator):
        filename = "test.dcm"
        file_dataset = FileDataset(
            filename, Dataset(), file_meta=self.create_metadata()
        )
        dcmwrite(filename, file_dataset, write_like_original=False)
        self.assert_fatal_error(validator, filename, "Missing SOPClassUID")

    def test_unknown_sop_class(self, validator):
        dataset = Dataset()
        dataset.SOPClassUID = "Unknown"
        file_dataset = FileDataset("test", dataset, file_meta=self.create_metadata())
        dcmwrite("test", file_dataset, write_like_original=False)
        self.assert_fatal_error(
            validator, "test", "Unknown SOPClassUID (probably retired): Unknown"
        )

    def test_validate_dir(self, fs, validator):
        fs.create_dir(os.path.join("foo", "bar", "baz"))
        fs.create_dir(os.path.join("foo", "baz"))
        fs.create_file(os.path.join("foo", "1.dcm"))
        fs.create_file(os.path.join("foo", "bar", "2.dcm"))
        fs.create_file(os.path.join("foo", "bar", "3.dcm"))
        fs.create_file(os.path.join("foo", "bar", "baz", "4.dcm"))
        fs.create_file(os.path.join("foo", "baz", "5.dcm"))
        fs.create_file(os.path.join("foo1", "6.dcm"))

        assert len(validator.validate("foo")) == 5

    def test_non_fatal_errors(self, validator):
        dataset = Dataset()
        dataset.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
        file_dataset = FileDataset("test", dataset, file_meta=self.create_metadata())
        dcmwrite("test", file_dataset, write_like_original=False)
        error_dict = validator.validate("test")
        assert len(error_dict) == 1
        errors = error_dict["test"]
        assert "fatal" not in errors


def test_that_pixeldata_is_read(dicom_fixture_path, validator):
    # regression test for #6
    rtdose_path = dicom_fixture_path / "rtdose.dcm"
    error_dict = validator.validate(rtdose_path)
    assert len(error_dict) == 1
    results = error_dict[rtdose_path]
    assert "RT Series" in results
    assert "Tag (0008,1070) (Operators' Name) is missing" in results["RT Series"]
    # if PixelData is not read, RT Dose will show errors
    assert "RT Dose" not in results
