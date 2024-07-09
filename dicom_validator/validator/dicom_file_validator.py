from dataclasses import dataclass
import logging
import os
import sys
from typing import Any
import warnings

from pydicom import config, dcmread
from pydicom.valuerep import validate_value
from pydicom.errors import InvalidDicomError

from dicom_validator.validator.iod_validator import IODValidator


class DicomFileValidator:
    def __init__(
        self,
        dicom_info,
        log_level=logging.INFO,
        force_read=False,
        suppress_vr_warnings=False,
    ):
        self._dicom_info = dicom_info
        self.logger = logging.getLogger()
        self.logger.level = log_level
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self._force_read = force_read
        self._suppress_vr_warnings = suppress_vr_warnings

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
            # Suppress warnings about invalid values while reading the file.
            # The default behavior emits a warning, but unfortunately it does
            # not provide the tag and value that caused the warning. We will
            # handle it ourselves after reading the file.
            config.settings.reading_validation_mode = config.IGNORE
            data_set = dcmread(file_path, defer_size=1024, force=self._force_read)
            if not self._suppress_vr_warnings:
                self.validate_dicom_values(data_set)

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

    def validate_dicom_values(self, data_set) -> None:
        # Confirm that SOPClassUID is valid. Skip the check if SopClassUID
        # is present, since validator will result in a fatal error if it is missing.
        if "SOPClassUID" in data_set:
            validate_value("UI", data_set.SOPClassUID, config.WARN)

        @dataclass
        class TagValue:
            tag: str
            VR: str
            value: Any

        invalid_values = []

        for tt in data_set:
            if tt.value is None:
                continue
            values = [tt.value] if tt.VM == 1 else list(tt.value)
            for vv in values:
                # Convert the value to a string if it is a number to avoid
                # raising an exception when validating the value.
                # TODO: What is the right way to do this? Should we update the
                # validator in pydicom's valuerep.py instead of hacking it here?
                if tt.VR in ["IS", "DS"]:
                    vv = str(vv)
                try:
                    validate_value(tt.VR, vv, config.RAISE)
                except Exception as _:
                    invalid_values.append(
                        TagValue(tag=str(tt.tag).replace(' ', ''),
                                 VR=tt.VR,
                                 value=vv)
                                 )

        if invalid_values:
            self.logger.warning("\nWarnings for values not matching value representation (VR).\n"
                                "========")
            for iv in invalid_values:
                self.logger.warning("Tag %s: invalid value (%s) for VR %s", iv.tag, iv.value, iv.VR)
            self.logger.warning("See https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html#table_6.2-1\n")
                    