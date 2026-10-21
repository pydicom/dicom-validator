import os
from pathlib import Path

import pydicom
import pytest
from pydicom import DataElement, config, dcmread, dcmwrite
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset

from dicom_validator.validator.dicom_file_validator import DicomFileValidator
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.error_handler import NullValidationResultHandler
from dicom_validator.validator.iod_validator import IODValidator
from dicom_validator.validator.validation_result import DicomTag, ErrorCode, Status

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
    def assert_fatal_error(validator, filename, error_code, is_error=True):
        result_dict = validator.validate(filename)
        assert len(result_dict) == 1
        assert filename in result_dict
        result = result_dict[filename]
        assert result.status == error_code
        assert result.errors == (1 if is_error else 0)

    def test_non_existing_file(self, validator):
        self.assert_fatal_error(validator, "non_existing", Status.MissingFile)

    def test_invalid_file(self, fs, validator):
        fs.create_file("test", contents="invalid")
        self.assert_fatal_error(validator, "test", Status.InvalidFile, is_error=False)

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
    assert "RT Series" in result.module_errors
    oper_name_error = result.module_errors["RT Series"].get(DicomTag(0x0008_1070))
    assert oper_name_error is not None
    assert oper_name_error.code == ErrorCode.TagMissing
    # if PixelData is not read, RT Dose will show errors
    assert "RT Dose" not in result.module_errors


@pytest.fixture(params=[config.IGNORE, config.WARN, config.RAISE])
def reading_mode(request, monkeypatch):
    monkeypatch.setattr(config.settings, "reading_validation_mode", request.param)
    return request.param


@pytest.fixture
def mode_validator():
    return DicomFileValidator(
        DicomInfo({}, {}, {}), error_handler=NullValidationResultHandler()
    )


@pytest.fixture
def deferred_dicom_file(tmp_path):
    filename = str(tmp_path / "deferred.dcm")
    dataset = FileDataset(
        filename, Dataset(), file_meta=TestFakeDicomFileValidator.create_metadata()
    )
    dataset.SOPClassUID = dataset.file_meta.MediaStorageSOPClassUID
    dataset.add(
        DataElement("PatientID", "LO", "A" * 2048, validation_mode=config.IGNORE)
    )
    dcmwrite(filename, dataset, **TestFakeDicomFileValidator.enforce_file_format())
    # The oversized LO value is deferred by the same threshold used in validate_file.
    assert dcmread(filename, defer_size=1024)._dict[0x0010_0020].value is None
    return filename


def test_reading_mode_restored_after_validation(
    mode_validator, deferred_dicom_file, reading_mode
):
    writing_mode = config.settings.writing_validation_mode
    result = mode_validator.validate_file(deferred_dicom_file)[deferred_dicom_file]
    assert result.status == Status.UnknownSOPClassUID
    assert config.settings.reading_validation_mode == reading_mode
    assert config.settings.writing_validation_mode == writing_mode


def test_reading_mode_restored_after_invalid_file(
    mode_validator, tmp_path, reading_mode
):
    filename = str(tmp_path / "invalid.dcm")
    Path(filename).write_bytes(b"not a DICOM file")
    result = mode_validator.validate_file(filename)[filename]
    assert result.status == Status.InvalidFile
    assert config.settings.reading_validation_mode == reading_mode


def test_reading_mode_restored_after_read_error(mode_validator, tmp_path, reading_mode):
    with pytest.raises(FileNotFoundError):
        mode_validator.validate_file(str(tmp_path / "missing.dcm"))
    assert config.settings.reading_validation_mode == reading_mode


@pytest.mark.parametrize("method", ["__init__", "validate"])
def test_reading_mode_restored_after_validation_error(
    mode_validator, deferred_dicom_file, reading_mode, method, monkeypatch
):
    def fail_validation(self, *args, **kwargs):
        assert config.settings.reading_validation_mode == config.IGNORE
        raise RuntimeError("validation failed")

    monkeypatch.setattr(IODValidator, method, fail_validation)
    with pytest.raises(RuntimeError, match="validation failed"):
        mode_validator.validate_file(deferred_dicom_file)
    assert config.settings.reading_validation_mode == reading_mode


@pytest.mark.parametrize("invalid_file", [False, True])
def test_reading_mode_restored_after_handler_error(
    mode_validator, deferred_dicom_file, reading_mode, invalid_file, monkeypatch
):
    def fail_handler(result):
        assert config.settings.reading_validation_mode == config.IGNORE
        raise RuntimeError("handler failed")

    if invalid_file:
        Path(deferred_dicom_file).write_bytes(b"not a DICOM file")
    monkeypatch.setattr(
        mode_validator._error_handler, "handle_validation_result", fail_handler
    )
    with pytest.raises(RuntimeError, match="handler failed"):
        mode_validator.validate_file(deferred_dicom_file)
    assert config.settings.reading_validation_mode == reading_mode
