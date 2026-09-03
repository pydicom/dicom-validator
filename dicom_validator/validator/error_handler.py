import logging
import sys
from abc import abstractmethod
from typing import Protocol

from pydicom.tag import BaseTag

from dicom_validator.spec_reader.condition import Condition, ConditionType
from dicom_validator.tag_tools import tag_name_from_id
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.validation_result import (
    DicomTag,
    ErrorCode,
    ErrorScope,
    Status,
    TagError,
    TagErrors,
    ValidationResult,
)


class ValidationResultHandler(Protocol):
    """Protocol to be implemented by any validation result handler
    passed to the IODValidator."""

    @abstractmethod
    def handle_validation_start(self, result: ValidationResult):
        """Called before the validation has started. Only the SOP Class UID
        is set at this point."""
        ...

    @abstractmethod
    def handle_validation_result(self, result: ValidationResult):
        """Called after the validation has finished. All found errors are
        recorded in the validation result."""
        ...


class NullValidationResultHandler(ValidationResultHandler):
    """A no-op handler.

    Useful when you only want to read the `ValidationResult` after `validate()`
    returns, without any additional reporting.
    """

    def handle_validation_start(self, result: ValidationResult) -> None:
        ...  # no-op: this handler intentionally does no reporting

    def handle_validation_result(self, result: ValidationResult) -> None:
        ...  # no-op: this handler intentionally does no reporting


class ValidationResultHandlerBase(ValidationResultHandler):
    """Provides a skeleton implementation for a result handler.
    An easy way to implement another handler is to derive from this class
    and implement the actual handling in some or all placeholder methods.
    """

    def handle_validation_start(self, result: ValidationResult) -> None:
        """Placeholder method.
        Called before the validation has started. Only the SOP Class UID
        is set at this point."""

    def handle_validation_result(self, result: ValidationResult) -> None:
        """Called after the validation has finished. All found errors are
        recorded in the validation result.
        Only calls other methods that may contain the actual handling."""
        if result.status not in (Status.Passed, Status.Failed):
            self.handle_failed_validation_start(result)
        else:
            if result.errors:
                self.handle_validation_result_start(result)
                if result.module_errors:
                    for module_name, tag_errors in result.module_errors.items():
                        self.handle_module_errors(module_name, tag_errors)
                self.handle_validation_result_end(result)

    def handle_failed_validation_start(self, result: ValidationResult) -> None:
        """Placeholder method.
        Called in case the validation could not be started. Only the error code
        is set in the result. The validation is aborted after this call."""

    def handle_validation_result_start(
        self, validation_result: ValidationResult
    ) -> None:
        """Placeholder method.
        Called after the validation result is available and before the result
        handling starts."""

    def handle_validation_result_end(self, validation_result: ValidationResult) -> None:
        """Placeholder method.
        Called after the validation result have been handled."""

    def handle_module_errors(self, module_name: str, tag_errors: TagErrors) -> None:
        """Called to handle the errors in a single module.
        Only calls other methods that may contain the actual handling.
        """
        self.handle_module_errors_start(module_name, tag_errors)
        error_items = sorted(tag_errors.items(), key=lambda x: x[0])
        parents: list[BaseTag] | None = []
        for tag_id, tag_error in error_items:
            if tag_id.parents and tag_id.parents != parents:
                if parents is not None:
                    self.handle_tag_parents_end(parents)
                parents = tag_id.parents
                if parents is not None:
                    self.handle_tag_parents_start(parents)
            self.handle_tag_error(tag_id, tag_error)
        self.handle_module_errors_end(module_name, tag_errors)

    def handle_module_errors_start(
        self, module_name: str, tag_errors: TagErrors
    ) -> None:
        """Placeholder method.
        Called before the errors for a single module are handled."""

    def handle_module_errors_end(self, module_name: str, tag_errors: TagErrors) -> None:
        """Placeholder method.
        Called after the errors for a single module are handled."""

    def handle_tag_error(self, tag_id: DicomTag, error: TagError) -> None:
        """Placeholder method.
        Called to handle a single tag error. The actual error handling
        (logging, recording) shall be implemented here."""

    def handle_tag_parents_start(self, parents: list[BaseTag]) -> None:
        """Placeholder method.
        Called to handle parent sequence tags. Is called once
        for one or more tag errors with the same parent sequences."""

    def handle_tag_parents_end(self, parents: list[BaseTag]) -> None:
        """Placeholder method.
        Called to handle parent sequence tags. Is called once
        after one or more tag errors with the same parent sequences appeared."""


class ValidationResultFormatter:
    """Renders `TagError` and `ValidationResult` objects as human-readable text."""

    def __init__(self, dictionary: dict | None = None) -> None:
        """Initialise the formatter.

        Parameters
        ----------
        dictionary : dict, optional
            The DICOM dictionary (`DicomInfo.dictionary`), used to look up
            condition text for `ErrorCode.TagNotAllowed` errors.
        """
        self.dictionary = dictionary

    def error_message(self, error: TagError, indent: int = 0) -> str:
        """Return a human-readable message fragment for a tag error.

        Parameters
        ----------
        error : TagError
            The error to be rendered.
        indent : int
            Current indentation level, in case the message itself needs to
            be indented further (e.g. for a condition on multiple lines).
            Defaults to 0.

        Returns
        -------
        str
            A message fragment starting with a space, to be appended after
            the tag name.
        """
        match error.scope:
            case ErrorScope.SharedFuncGroup:
                postfix = " in Shared Group"
            case ErrorScope.PerFrameFuncGroup:
                postfix = " in Per-Frame Group"
            case ErrorScope.BothFuncGroups:
                postfix = " in both Shared and Per-Frame Groups"
            case _:
                postfix = ""

        match error.code:
            case ErrorCode.TagMissing:
                return f" is missing{postfix}"
            case ErrorCode.TagEmpty:
                return " is empty"
            case ErrorCode.TagUnexpected:
                return f" is unexpected{postfix}"
            case ErrorCode.TagNotAllowed:
                msg = f" is not allowed{postfix}"
                if self.dictionary and error.context and "cond" in error.context:
                    indent += 1
                    condition = Condition.read_condition(error.context["cond"])
                    if condition.type != ConditionType.UserDefined:
                        msg += f" by condition:\n{'  ' * indent}{condition.to_string(self.dictionary)}"
                return msg
            case ErrorCode.EnumValueNotAllowed:
                error.context = error.context or {}
                return (
                    f" - enum value '{error.context.get('value', '')}' not allowed,\n"
                    f"  allowed values: {', '.join([str(v) for v in error.context.get('allowed', [])])}"
                )
            case ErrorCode.InvalidValue:
                error.context = error.context or {}
                return f" has invalid value '{error.context['value']}' for VR {error.context['VR'] if error.context else ''}"
            case ErrorCode.InvalidSequence:
                return " is not a valid sequence, ignoring it"
            case _:
                return ""

    def failed_validation_message(self, result: ValidationResult) -> str:
        """Return a human-readable message for a result that could not be validated.

        Parameters
        ----------
        result : ValidationResult
            The result of a validation that failed to start (`result.status`
            is not `Status.Passed` or `Status.Failed`).

        Returns
        -------
        str
            A message describing why the validation could not be started.
        """
        match result.status:
            case Status.MissingSOPClassUID:
                return "Missing SOP Class UID"
            case Status.UnknownSOPClassUID:
                return f"Unknown or retired SOP Class UID: {result.sop_class_uid}"
            case Status.MissingFile:
                return f"Missing DICOM File: {result.file_path}"
            case Status.InvalidFile:
                return f"Not a DICOM File: {result.file_path} - ignoring"
            case _:
                return "Unknown error"


class LoggingResultHandler(ValidationResultHandlerBase):
    """Handles the result of the validation of a single DICOM file
    by logging all errors.
    """

    def __init__(self, dicom_info: DicomInfo, logger: logging.Logger) -> None:
        self.dicom_info = dicom_info
        self.logger = logger
        self._formatter = ValidationResultFormatter(dicom_info.dictionary)

    def handle_validation_start(self, result: ValidationResult) -> None:
        iod_info = self.dicom_info.iods[result.sop_class_uid]
        if result.file_path:
            self.logger.info(f"Validating DICOM file {result.file_path}")
        self.logger.info(
            'SOP class is "%s" (%s)', result.sop_class_uid, iod_info["title"]
        )
        self.logger.debug("Checking modules for SOP Class")
        self.logger.debug("------------------------------")

    def handle_module_errors_start(
        self, module_name: str, tag_errors: TagErrors
    ) -> None:
        self.logger.warning(f'\nModule "{module_name}":')

    def handle_tag_parents_start(self, parents: list[BaseTag]) -> None:
        self.logger.warning(
            " / ".join(
                tag_name_from_id(tag, self.dicom_info.dictionary) for tag in parents
            )
            + ":"
        )

    def handle_tag_error(self, tag_id: DicomTag, error: TagError) -> None:
        indent = 1 if tag_id.parents else 0
        tag_name = tag_name_from_id(tag_id.tag, self.dicom_info.dictionary)
        msg = f"{'  ' * indent}Tag {tag_name}{self.error_message(error, indent)}"
        self.logger.warning(msg)

    def handle_validation_result_start(
        self, validation_result: ValidationResult
    ) -> None:
        if validation_result.errors:
            self.logger.info("\nErrors\n======")

    def handle_validation_result_end(self, validation_result: ValidationResult) -> None:
        if validation_result.errors:
            self.logger.info("\n======")
        else:
            self.logger.info("\n")

    def handle_failed_validation_start(self, result: ValidationResult) -> None:
        self.logger.error(self._formatter.failed_validation_message(result))

    def error_message(self, error: TagError, indent: int) -> str:
        """Return a human-readable message fragment for a tag error.

        Parameters
        ----------
        error : TagError
            The error to be rendered.
        indent : int
            Current indentation level, in case the message itself needs to
            be indented further (e.g. for a condition on multiple lines).

        Returns
        -------
        str
            A message fragment starting with a space, to be appended after
            the tag name.
        """
        return self._formatter.error_message(error, indent)


def default_error_handler(dicom_info: DicomInfo, log_level: int = logging.INFO):
    logger = logging.getLogger("validator")
    if not logger.hasHandlers():
        logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.level = log_level
    return LoggingResultHandler(dicom_info, logger)
