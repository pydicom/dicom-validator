import os
from pathlib import Path

import pydicom
import pytest
from pydicom import dcmwrite
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset

from dicom_validator.validator.dicom_file_validator import DicomFileValidator
from dicom_validator.validator.validation_result import Status, DicomTag, ErrorCode

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

    @staticmethod
    def enforce_file_format():
        return (
            {"write_like_original": False}
            if int(pydicom.__version_info__[0]) < 3
            else {"enforce_file_format": True}
        )

    @staticmethod
    def assert_fatal_error(validator, filename, error_code):
        result_dict = validator.validate(filename)
        assert len(result_dict) == 1
        assert filename in result_dict
        result = result_dict[filename]
        assert result.status == error_code
        assert result.errors == 1

    def test_non_existing_file(self, validator):
        self.assert_fatal_error(validator, "non_existing", Status.MissingFile)

    def test_invalid_file(self, fs, validator):
        fs.create_file("test", contents="invalid")
        self.assert_fatal_error(validator, "test", Status.InvalidFile)

    def test_missing_sop_class(self, validator):
        filename = "test.dcm"
        file_dataset = FileDataset(
            filename, Dataset(), file_meta=self.create_metadata()
        )
        dcmwrite(filename, file_dataset, **self.enforce_file_format())
        self.assert_fatal_error(validator, filename, Status.MissingSOPClassUID)

    def test_unknown_sop_class(self, validator):
        dataset = Dataset()
        dataset.SOPClassUID = "Unknown"
        file_dataset = FileDataset("test", dataset, file_meta=self.create_metadata())
        dcmwrite("test", file_dataset, **self.enforce_file_format())
        self.assert_fatal_error(validator, "test", Status.UnknownSOPClassUID)

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
        dcmwrite("test", file_dataset, **self.enforce_file_format())
        error_dict = validator.validate("test")
        assert len(error_dict) == 1
        result = error_dict["test"]
        assert result.status == Status.Failed


def test_that_pixeldata_is_read(dicom_fixture_path, validator: DicomFileValidator):
    # regression test for #6
    rtdose_path = dicom_fixture_path / "rtdose.dcm"
    result_dict = validator.validate(rtdose_path)
    assert len(result_dict) == 1
    result = result_dict[str(rtdose_path)]
    assert result.module_errors is not None
    assert "RT Series" in result.module_errors
    oper_name_error = result.module_errors["RT Series"].get(DicomTag(0x0008_1070))
    assert oper_name_error is not None
    assert oper_name_error.code == ErrorCode.TagMissing
    # if PixelData is not read, RT Dose will show errors
    assert "RT Dose" not in result.module_errors
