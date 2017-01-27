import logging
import os

import sys

try:
    from pydicom import filereader
    from pydicom.errors import InvalidDicomError
except ImportError:
    from dicom import filereader
    from dicom.errors import InvalidDicomError

from dcm_spec_tools.validator.iod_validator import IODValidator


class DicomFileValidator(object):
    def __init__(self, iod_info, module_info, dict_info=None, log_level=logging.INFO):
        self._module_info = module_info
        self._iod_info = iod_info
        self._dict_info = dict_info
        self.logger = logging.getLogger()
        self.logger.level = log_level
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def validate(self, path):
        errors = {}
        if not os.path.exists(path):
            errors.update({path: {'fatal': 'File missing'}})
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
            data_set = filereader.read_file(file_path, stop_before_pixels=True)
        except InvalidDicomError:
            return {file_path: {'fatal': 'Invalid DICOM file'}}
        return {
            file_path: IODValidator(data_set, self._iod_info, self._module_info, self._dict_info,
                                    self.logger.level).validate()
        }
