import logging
import os

import sys
from pydicom import filereader
from validator.iod_validator import IODValidator


class DicomFileValidator(object):
    def __init__(self, iod_info, module_info, dict_info, log_level=logging.INFO):
        self._module_info = module_info
        self._iod_info = iod_info
        self._dict_info = dict_info
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.level = log_level
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def validate(self, path):
        error_nr = 0
        if not os.path.exists(path):
            self.logger.warning('\n"%s" does not exist - skipping', path)
        else:
            if os.path.isdir(path):
                error_nr += self.validate_dir(path)
            else:
                error_nr += self.validate_file(path)
        return error_nr

    def validate_dir(self, dir_path):
        error_nr = 0
        for root, _, names in os.walk(dir_path):
            error_nr += sum(self.validate(os.path.join(root, name)) for name in names)
        return error_nr

    def validate_file(self, file_path):
        self.logger.info('\nProcessing DICOM file "%s"', file_path)
        data_set = filereader.read_file(file_path, stop_before_pixels=True, force=True)
        return len(IODValidator(data_set, self._iod_info, self._module_info, self._dict_info,
                                self.logger.level).validate())
