import logging
import os
from os import PathLike

from pydicom import config, dcmread
from pydicom.errors import InvalidDicomError

from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.error_handler import ValidationResultHandler
from dicom_validator.validator.iod_validator import IODValidator
from dicom_validator.validator.validation_result import ValidationResult, Status


class DicomFileValidator:
    """Validates a single DICOM file or all DICOM files in a directory."""

    def __init__(
        self,
        dicom_info: DicomInfo,
        log_level: int = logging.INFO,
        force_read: bool = False,
        suppress_vr_warnings: bool = False,
        error_handler: ValidationResultHandler | None = None,
    ) -> None:
        """Initializes a DicomFileValidator object.

        Parameters
        ----------
        dicom_info : DicomInfo
            DICOM information as read from the JSON files created from the standard
        log_level : int
            The log level to use with the default error handler
        force_read: bool
            If `True`, the DICOM file is tried to read even if it may not be valid
        suppress_vr_warnings: bool
            By default, values not valid for the given VR are reported, using the
            `pydicom` validation. If set to `True`, this validation is not performed.
        error_handler: ValidationResultHandler or None
            If set, this handler will be used to handle the validation result,
            otherwise the default handler is used that logs errors to the console.
        """
        self._dicom_info = dicom_info
        self.log_level = log_level
        self._force_read = force_read
        self._suppress_vr_warnings = suppress_vr_warnings
        self._error_handler = error_handler

    def validate(self, path: str | PathLike) -> dict[str, ValidationResult]:
        """Validate a single DICOM file or all files under a directory.

        Parameters
        ----------
        path : str | os.PathLike
            Path to a DICOM file or a directory containing DICOM files.

        Returns
        -------
        dict[str, ValidationResult]
            A mapping from file path to its validation result.
        """
        results: dict[str, ValidationResult] = {}
        path = os.fspath(path)
        if not os.path.exists(path):
            results[path] = ValidationResult(
                file_path=path, status=Status.MissingFile, errors=1
            )
        else:
            if os.path.isdir(path):
                results.update(self.validate_dir(path))
            else:
                results.update(self.validate_file(path))
        return results

    def validate_dir(self, dir_path: str) -> dict[str, ValidationResult]:
        """Validate all DICOM files contained in a directory tree.

        Parameters
        ----------
        dir_path : str
            Path to a directory that will be traversed recursively.

        Returns
        -------
        dict[str, ValidationResult]
            A mapping from file path to its validation result for all files found.
        """
        results: dict[str, ValidationResult] = {}
        for root, _, names in os.walk(dir_path):
            for name in names:
                results.update(self.validate(os.path.join(root, name)))
        return results

    def validate_file(self, file_path: str) -> dict[str, ValidationResult]:
        """Validate a single DICOM file.

        Parameters
        ----------
        file_path : str
            Path to a DICOM file.

        Returns
        -------
        dict[str, ValidationResult]
            A mapping containing exactly one entry for the given file.
        """
        try:
            # dcmread calls validate_value by default. If values don't match
            # required VR (value representation), it emits a warning but
            # does not provide the tag and value that caused the warning.
            # We will handle it later (optionally) by calling validate_value
            # directly.
            config.settings.reading_validation_mode = config.IGNORE
            data_set = dcmread(file_path, defer_size=1024, force=self._force_read)

        except InvalidDicomError:
            return {
                file_path: ValidationResult(
                    file_path=file_path, status=Status.InvalidFile, errors=1
                )
            }
        return {
            file_path: IODValidator(
                data_set,
                self._dicom_info,
                log_level=self.log_level,
                suppress_vr_warnings=self._suppress_vr_warnings,
                error_handler=self._error_handler,
                file_path=file_path,
            ).validate()
        }
