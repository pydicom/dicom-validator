import logging
import os
import sys

from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from dicom_validator.validator.iod_validator import IODValidator


class DicomFileValidator:
    def __init__(
        self,
        dicom_info,
        log_level=logging.INFO,
        force_read=False,
    ):
        self._dicom_info = dicom_info
        self.logger = logging.getLogger()
        self.logger.level = log_level
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self._force_read = force_read

    def validate(self, path):
        errors = {}
        if not os.path.exists(path):
            errors.update({path: {"fatal": "File missing"}})
            self.logger.warning('\n"%s" does not exist - skipping', path)
        else:
            if os.path.isdir(path):
                errors.update(self.validate_dir(path))
            else:
                errors.update(self.validate_file(path))
        return errors

    def validate_dir(self, dir_path):
        errors = {}
        for root, _, names in os.walk(dir_path):
            for name in names:
                errors.update(self.validate(os.path.join(root, name)))
        return errors

    def validate_file(self, file_path):
        self.logger.info('\nProcessing DICOM file "%s"', file_path)
        try:
            data_set = dcmread(file_path, defer_size=1024, force=self._force_read)
        except InvalidDicomError:
            self.logger.error(f"Invalid DICOM file: {file_path}")
            return {file_path: {"fatal": "Invalid DICOM file"}}
        return {
            file_path: IODValidator(
                data_set,
                self._dicom_info,
                self.logger.level,
            ).validate()
        }
